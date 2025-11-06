#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VinceBot (trwiki)
#9-[[VP:KA|Uygun olmayan kullanıcı adı]] → {{yk:ku-kaengel|imza=evet}}
#8-[[VP:TELİF|Telif hakkı ihlali]] → {{yk:ku-telifengel|imza=evet}}
"""

import json, os, re, time
from datetime import datetime, timezone, timedelta
import pywikibot
from pywikibot.exceptions import HiddenKeyError

# ============ AYARLAR ============
PROJECT = ("tr", "wikipedia")
DRY_RUN = False
VERBOSE = True
STATE_FILE = "vincebot_state.json"
EDIT_SUMMARY = "Bot: Engel bildirimi yapılıyor."
SLEEP_BETWEEN_EDITS = 2
SCAN_WINDOW_HOURS = 6
LOG_TOTAL = 50
# ================================

# --- Gerekçe desenleri ---
_RE_KA_9 = re.compile(
    r"#\s*9\s*-\s*\[\[\s*(?:VP|Vikipedi)\s*:\s*KA\s*\|\s*Uygun\s+olmayan\s+kullanıcı\s+adı\s*\]\]",
    flags=re.IGNORECASE
)
_RE_TELIF_8 = re.compile(
    r"#\s*8\s*-\s*\[\[\s*(?:VP|Vikipedi)\s*:\s*TELİF\s*\|\s*Telif\s+hakk[ıi]\s+ihlali\s*\]\]",
    flags=re.IGNORECASE
)

# --- Yardımcı fonksiyonlar ---
def load_state():
    if not os.path.exists(STATE_FILE):
        start = datetime.now(timezone.utc) - timedelta(hours=SCAN_WINDOW_HOURS)
        return {"last_ts": start.timestamp(), "markers": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    tmpfile = STATE_FILE + ".tmp"
    with open(tmpfile, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmpfile, STATE_FILE)

def already_notified(text, marker):
    return bool(text) and re.search(r"<!--\s*KAENGEL:" + re.escape(marker) + r"\s*-->", text)

def detect_reason_type(reason):
    """#9, #8 veya None döner"""
    if not reason:
        return None
    r = reason.strip()
    if _RE_KA_9.search(r) or ("#9" in r.lower() and "uygun olmayan kullanıcı adı" in r.lower()):
        return "ka9"
    if _RE_TELIF_8.search(r) or ("#8" in r.lower() and "telif" in r.lower()):
        return "telif8"
    return None

# --- Ana fonksiyon ---
def main():
    print("Login başlıyor...")
    site = pywikibot.Site(*PROJECT)
    site.login()
    print("Login tamam.")

    state = load_state()
    last_ts = float(state["last_ts"])
    seen = set(state.get("markers", []))
    new_last_ts = last_ts

    print(f"Durum: last_ts={last_ts} | LOG_TOTAL={LOG_TOTAL} | SCAN_WINDOW_HOURS={SCAN_WINDOW_HOURS}")
    print("Günlükler çekiliyor...")
    logs = site.logevents(logtype="block", total=LOG_TOTAL, reverse=False)

    count_seen, count_match = 0, 0
    for log in logs:
        ts = log.timestamp()
        ts_sec = getattr(ts, "toTimestamp", lambda: ts)().timestamp() if hasattr(ts, "toTimestamp") else ts.timestamp()
        if ts_sec <= last_ts:
            if VERBOSE: print(f"- Atlandı (eski): {ts}")
            continue

        if log.action() not in ("block", "reblock"):
            continue

        try:
            page = log.page()
        except HiddenKeyError:
            if VERBOSE: print("  · Atlandı (gizli başlık/actionhidden).")
            new_last_ts = max(new_last_ts, ts_sec)
            continue

        reason = (log.comment() or "").strip()
        target_name = page.title(with_ns=False)
        admin_name = log.user()
        marker = f"{int(ts_sec)}-{admin_name}-{log.action()}"
        count_seen += 1

        reason_type = detect_reason_type(reason)
        if marker in seen:
            if VERBOSE: print(f"[{count_seen}] {ts} {target_name} zaten işlenmiş.")
            continue
        if not reason_type:
            if VERBOSE: print(f"[{count_seen}] {ts} {target_name} #8/#9 değil.")
            continue

        # Eşleşme
        if reason_type == "ka9":
            template = "{{yk:ku-kaengel|imza=evet}}"
            section = "Kullanıcı adı engeli"
        elif reason_type == "telif8":
            template = "{{yk:ku-telifengel|imza=evet}}"
            section = "Telif hakkı engeli"

        talk = page.toggleTalkPage()
        old_text = talk.get() if talk.exists() else ""
        if already_notified(old_text, marker):
            seen.add(marker)
            continue

        count_match += 1
        message = f"{template}\n<!-- KAENGEL:{marker} -->"
        print(f"==> EŞLEŞTİ: {target_name} | Tür={reason_type} | DRY_RUN={DRY_RUN}")

        if not DRY_RUN:
            new_text = (old_text + ("\n\n" if old_text else "")) + f"== {section} ==\n{message}\n"
            talk.text = new_text
            talk.save(summary=EDIT_SUMMARY, minor=True, botflag=True)
            time.sleep(SLEEP_BETWEEN_EDITS)

        seen.add(marker)
        new_last_ts = max(new_last_ts, ts_sec)

    state["last_ts"] = new_last_ts
    state["markers"] = sorted(list(seen))
    save_state(state)
    print(f"Bitti. İncelenen: {count_seen}, Eşleşen: {count_match}, DRY_RUN={DRY_RUN}")

if __name__ == "__main__":
    main()
