#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VinceBot (trwiki) — #9 KA engeli bildirimi
- Gerekçesi "#9-[[VP:KA|Uygun olmayan kullanıcı adı]]" olan block/reblock olaylarını yakalar.
- Engellenenin mesaj sayfasına {{yk:ku-kaengel}} bırakır.
- DRY_RUN=True iken sadece ne yapacağını yazar (değişiklik yapmaz).
"""

import json, os, re, time
from datetime import datetime, timezone, timedelta
import pywikibot
from pywikibot.exceptions import HiddenKeyError

# ============ AYARLAR ============
PROJECT = ("tr", "wikipedia")
DRY_RUN = False                 # önce deneme
VERBOSE = True                 # ayrıntılı çıktı
STATE_FILE = "vincebot_state.json"
EDIT_SUMMARY = "Bot: kullanıcı adı (#9) engeli bildirimi"
SECTION_TITLE = "Kullanıcı adı engeli"
SLEEP_BETWEEN_EDITS = 2
SCAN_WINDOW_HOURS = 6          # test için geniş aralık 
LOG_TOTAL = 50                # incelenecek maksimum kayıt sayısı
# ================================

_USERNAME_9_RE = re.compile(
    r"#\s*9\s*-\s*\[\[\s*Vikipedi\s*:\s*KA\s*\|\s*Uygun\s+olmayan\s+kullanıcı\s+adı\s*\]\]",
    flags=re.IGNORECASE
)

def load_state():
    if not os.path.exists(STATE_FILE):
        start = datetime.now(timezone.utc) - timedelta(hours=SCAN_WINDOW_HOURS)
        return {"last_ts": start.timestamp(), "markers": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def already_notified(text, marker):
    return bool(text) and re.search(r"<!--\s*KAENGEL:" + re.escape(marker) + r"\s*-->", text)

def is_username_policy_9(reason):
    if not reason: return False
    r = reason.strip()
    if _USERNAME_9_RE.search(r):
        return True
    rlow = r.lower()
    return ("#9" in rlow) and ("uygun olmayan kullanıcı adı" in rlow) and ("vp:ka" in rlow)

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
    # en yeni -> eski
    logs = site.logevents(logtype="block", total=LOG_TOTAL, reverse=False)

    count_seen, count_match = 0, 0
    for log in logs:
        ts = log.timestamp()
        ts_sec = getattr(ts, "toTimestamp", lambda: ts)().timestamp() if hasattr(ts, "toTimestamp") else ts.timestamp()
        if ts_sec <= last_ts:
            if VERBOSE: print(f"- Atlandı (eski): {ts}")
            continue

        action = log.action()
        if action not in ("block", "reblock"):
            if VERBOSE: print(f"- Atlandı (action={action}): {ts}")
            continue

        # *** ÖNEMLİ: Gerekçe yorumdadır ***
        reason = (log.comment() or "").strip()

        # Bazı kayıtlar gizli (actionhidden): .page() patlar -> atla
        try:
            page = log.page()
        except HiddenKeyError:
            if VERBOSE: print("  · Atlandı (gizli başlık/actionhidden).")
            new_last_ts = max(new_last_ts, ts_sec)
            continue

        target_name = page.title(with_ns=False)
        admin_name = log.user()
        marker = f"{int(ts_sec)}-{admin_name}-{action}"

        count_seen += 1
        if VERBOSE:
            print(f"[{count_seen}] {ts} | {target_name} | action={action} | reason={reason!r}")

        if marker in seen:
            if VERBOSE: print("  · Atlandı (zaten işlenmiş marker).")
            continue

        if not is_username_policy_9(reason):
            if VERBOSE: print("  · Atlandı (gerekçe #9-[[VP:KA|Uygun olmayan kullanıcı adı]] değil).")
            continue

        # Konuşma sayfası
        talk = page.toggleTalkPage()
        old_text = talk.get() if talk.exists() else ""
        if already_notified(old_text, marker):
            if VERBOSE: print("  · Atlandı (aynı marker yorum imleci var).")
            seen.add(marker)
            continue

        # EŞLEŞTİ
        count_match += 1
        message = "{{yk:ku-kaengel|imza=evet}}\n" f"<!-- KAENGEL:{marker} -->"
        print(f"==> EŞLEŞTİ: {target_name} | DRY_RUN={DRY_RUN}")

        if not DRY_RUN:
            new_text = (old_text + ("\n\n" if old_text else "")) + f"== {SECTION_TITLE} ==\n{message}\n"
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
