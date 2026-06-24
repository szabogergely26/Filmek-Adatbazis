# #  /app/tools/diag_movies.py
# -------------------------------

# -*- coding: utf-8 -*-

import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

DB_PATH = "/home/szaboger/Filmek-Adatbázis/movies.db"  # ha kell, módosítható

SIZE_RE = re.compile(r"([\d.,]+)\s*GB", re.IGNORECASE)


def parse_gb(s):
    if not s:
        return None
    m = SIZE_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except Exception:
        return None


def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH

    if not os.path.exists(db_path):
        print(f"[ERR] DB nem található: {db_path}")
        sys.exit(2)

    print(f"[INFO] DB: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # alap táblák
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"[INFO] Táblák: {tables}")

    if "media" not in tables:
        print("[ERR] Nincs 'media' tábla – ez kell az apphoz.")
        sys.exit(3)

    cur.execute(
        """
        SELECT
            rowid AS id, type, title, part, year, is_seasonal, genre, duration,
            size, storage_location, format_type, format
        FROM media
    """
    )
    rows = [dict(r) for r in cur.fetchall()]
    print(f"[INFO] Sorok száma: {len(rows)}")

    # csoportosítás title szerint
    grouped = defaultdict(list)
    for r in rows:
        t = (r.get("title") or "").strip()
        grouped[t].append(r)

    print(f"[INFO] Címek száma (grouped): {len(grouped)}")
    top5 = sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]
    print("[TOP] Legtöbb rész / azonos cím:")
    for t, g in top5:
        print(f"   - {t!r}: {len(g)} sor")

    # anomáliák
    empty_titles = [r for r in rows if not (r.get("title") or "").strip()]
    non_int_year = [
        r
        for r in rows
        if r.get("year") not in (None, "", 0) and not str(r.get("year")).isdigit()
    ]
    bad_size = [r for r in rows if r.get("size") and parse_gb(r.get("size")) is None]

    print(f"[CHK] Üres cím: {len(empty_titles)}")
    print(f"[CHK] 'year' nem egész: {len(non_int_year)}")
    print(f"[CHK] Méret (GB) nem értelmezhető: {len(bad_size)}")

    # összesített tárhely per cím
    print("[SUM] Összesített méret (GB) címenként – top 10:")
    sums = []
    for t, g in grouped.items():
        total = sum(filter(None, (parse_gb(r.get("size")) for r in g)))
        sums.append((t, total, len(g)))
    for t, total, n in sorted(sums, key=lambda x: x[1] or 0, reverse=True)[:10]:
        print(f"   - {t!r}: {total:.1f} GB ({n} rész)")

    # storage helyek és formátumok stat
    stor = Counter((r.get("storage_location") or "").strip() for r in rows)
    fmt = Counter((r.get("format_type") or "").strip() for r in rows)
    print("[STAT] Tárolási helyek (top 10):")
    for k, v in stor.most_common(10):
        if k:
            print(f"   - {k}: {v}")
    print("[STAT] Felbontások/format_type (top 10):")
    for k, v in fmt.most_common(10):
        if k:
            print(f"   - {k}: {v}")

    # index javaslatok
    print("[TIP] Index javaslatok (title, type, storage_location):")
    print("   CREATE INDEX IF NOT EXISTS idx_media_title ON media(title);")
    print("   CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);")
    print("   CREATE INDEX IF NOT EXISTS idx_media_storage ON media(storage_location);")

    conn.close()


if __name__ == "__main__":
    main()
