# db.py — egységes DatabaseManager a 'movies' táblához

import json
import logging
import re
import sqlite3
from typing import Any

ALLOWED_COLS = [
    "type",
    "title",
    "part",
    "year",
    "is_seasonal",
    "seasonal_type",
    "genre",
    "genre_general",
    "genre_official",
    "duration",
    "size",
    "storage_location",
    "format_type",
    "format",
    "director",
    "audio_tracks",
    "subtitle_tracks",
    "episode_title",
    "end_year",
    "is_completed",
    "provider",
    "parts_count",
    "seasonal_tag",
    "cover_path",
    "video_codec",
    "hdr_type",
    "audio_codec",
    "audio_bitrate",
    "notes",
    "storage_breakdown",
    "total_size_gb",
]


LOGGER = logging.getLogger("FilmekAdatbazis")



# ---- Segédek -----

_RANGE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def _parse_size_text_to_gb(size_text: str | None) -> float | None:
    """
    "23 GB", "23,5 GB", "1024 MB", "1.2 TB" -> GB float
    """
    if not size_text:
        return None
    s = size_text.strip().lower().replace(",", ".")
    m = re.match(r"^\s*([\d.]+)\s*(tb|gb|mb)\s*$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "mb":
        return val / 1024.0
    if unit == "gb":
        return val
    if unit == "tb":
        return val * 1024.0
    return None


def _load_breakdown(raw: Any) -> list[dict[str, Any]]:
    """
    Accepts:
      - None / "" -> []
      - JSON string -> list[dict]
      - list[dict] (ha valahol már úgy adod) -> list[dict]
    """
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            if isinstance(obj, list):
                return [x for x in obj if isinstance(x, dict)]
        except Exception:
            return []
    return []


def _dump_breakdown(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def _to_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _calc_total_gb(items: list[dict[str, Any]]) -> float:
    total = 0.0
    for it in items:
        v = _to_float(it.get("size_gb"))
        if v is None or v < 0:
            continue
        total += v
    return round(total, 2)


def _norm_loc(x: Any) -> str:
    return (str(x) if x is not None else "").strip()


def _parse_season_range(text: str) -> tuple[int, int] | None:
    m = _RANGE_RE.match(text or "")
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2))
    if a < 1 or b < 1 or a > b:
        return None
    return a, b


def _normalize_storage_breakdown(
    row_type: str,
    parts_count: int,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    """
    Nálad: row_type = "film" vagy "sorozat"
    Film: {"part": N, "loc": "...", "size_gb": ...}
    Sorozat: {"season": N, ...} vagy {"seasons": "1-3", ...}
    """
    if row_type == "film":
        by_part: dict[int, dict[str, Any]] = {}
        for it in items:
            p = it.get("part")
            if p is None:
                continue
            try:
                p = int(p)
            except Exception:
                continue
            if p < 1 or p > parts_count:
                continue
            out: dict[str, Any] = {
                "part": p,
                "loc": _norm_loc(it.get("loc")),
            }
            # opcionális alcím
            sub = (str(it.get("subtitle")) if it.get("subtitle") is not None else "").strip()
            if sub:
                out["subtitle"] = sub

            v = _to_float(it.get("size_gb"))
            if v is not None:
                out["size_gb"] = round(v, 2)

            by_part[p] = out

        return [by_part[p] for p in sorted(by_part.keys())]

    # sorozat
    out_list: list[dict[str, Any]] = []
    for it in items:
        base: dict[str, Any] = {"loc": _norm_loc(it.get("loc"))}
        v = _to_float(it.get("size_gb"))
        if v is not None:
            base["size_gb"] = round(v, 2)

        if it.get("season") is not None:
            try:
                n = int(it.get("season"))
            except Exception:
                continue
            if n < 1:
                continue
            base["season"] = n
            out_list.append(base)
            continue

        if isinstance(it.get("seasons"), str):
            rng = _parse_season_range(it["seasons"])
            if not rng:
                continue
            a, b = rng
            base["seasons"] = f"{a}-{b}"
            out_list.append(base)
            continue

    def _key(x: dict[str, Any]) -> tuple[int, int]:
        if "season" in x:
            return (0, int(x["season"]))
        if "seasons" in x and isinstance(x["seasons"], str):
            a, _ = _parse_season_range(x["seasons"]) or (10**9, 10**9)
            return (1, a)
        return (2, 10**9)

    out_list.sort(key=_key)
    return out_list


def _ensure_storage_fields(row: dict[str, Any]) -> None:
    """
    row-t módosítja:
      - ha van storage_breakdown, normalizálja és újraírja stringként
      - total_size_gb-t kiszámolja breakdown-ból
      - ha nincs breakdown/total, fallback: size mezőből parse
    """
    row_type = (row.get("type") or "").strip()
    if row_type not in ("film", "sorozat"):
        # Ha nincs típus, breakdown-ot ne normalizáljunk.
        # Fallback total_size_gb kitöltés size-ból maradhat:
        if row.get("total_size_gb") in (None, "", 0):
            gb = _parse_size_text_to_gb(row.get("size"))
            if gb is not None:
                row["total_size_gb"] = round(gb, 2)
        return

    parts_count = int(row.get("parts_count") or 1)

    items = _load_breakdown(row.get("storage_breakdown"))
    if items:
        normalized = _normalize_storage_breakdown(row_type, parts_count, items)
        row["storage_breakdown"] = _dump_breakdown(normalized) if normalized else ""
        row["total_size_gb"] = _calc_total_gb(normalized)
        return

    # nincs breakdown: ha total_size_gb hiányzik, próbáljuk size-ból
    if row.get("total_size_gb") in (None, "", 0):
        gb = _parse_size_text_to_gb(row.get("size"))
        if gb is not None:
            row["total_size_gb"] = round(gb, 2)






def _normalize_alias_fields(row: dict[str, Any]) -> None:
    """
    UI/legacy kompatibilitás: eltérő kulcsnevek egységesítése DB oszlopokra.
    - 'season' -> 'part'  (Évad/Rész)
    - 'subtitle' -> 'episode_title' (Alcím)
    """
    if "part" not in row and "season" in row:
        row["part"] = row.get("season")

    if "episode_title" not in row and "subtitle" in row:
        row["episode_title"] = row.get("subtitle")

    # 'part' takarítás: üres stringek -> None, string számok -> int
    if "part" in row:
        v = row.get("part")
        if v in ("", "—", None):
            row["part"] = None
        else:
            try:
                row["part"] = int(str(v).strip())
            except Exception:
                # ha valamiért nem konvertálható, hagyjuk úgy, de legalább benne legyen
                pass



















# ------ Segédek vége ----------------



class DatabaseManager:
    def __init__(self, path: str):
        self.path = path
        self.conn: sqlite3.Connection | None = None
        self.connect()

    # --- infra ---
    def connect(self) -> None:
        if self.conn is not None:
            return
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._enable_fk()
        self._ensure_schema()
        # ha szeretnéd látni az SQL-eket:
        # self.conn.set_trace_callback(lambda s: print("[SQL]", s))

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _enable_fk(self) -> None:
        cur = self.conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.close()




    def _ensure_schema(self) -> None:
        cur = self.conn.cursor()
        sql = """
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            title TEXT NOT NULL,
            part INTEGER,
            year INTEGER,
            end_year INTEGER,
            is_completed BOOLEAN,
            is_seasonal BOOLEAN,
            genre TEXT,
            genre_general TEXT,
            genre_official TEXT,
            duration TEXT,
            size TEXT,
            storage_location TEXT,
            format_type TEXT,
            format TEXT,
            director TEXT,
            audio_tracks TEXT,
            subtitle_tracks TEXT,
            episode_title TEXT,
            provider TEXT,
            parts_count INTEGER,
            seasonal_tag TEXT DEFAULT NULL,
            seasonal_type TEXT DEFAULT 'none',
            cover_path TEXT,
            video_codec TEXT,
            hdr_type TEXT DEFAULT 'none',
            audio_codec TEXT,
            audio_bitrate INTEGER,
            notes TEXT,
            storage_breakdown TEXT,
            total_size_gb REAL
        );
        """
        try:
            cur.execute(sql)
        except Exception as e:
            print("DB schema error:", e)
            print(sql)
            raise
        self.conn.commit()



    #----------------- idempotens migrációk régi adatbázisokra  --------------------

        self._migrate_add_genre_cols()
        self._migrate_add_new_cols()
        self._migrate_seasonal_type_values()


        cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_type ON movies(type)")
        self.conn.commit()
        cur.close()












    def _migrate_add_genre_cols(self) -> None:
        """Hozzáadja a genre_general/genre_official oszlopokat, ha hiányoznak,
        és a régi 'genre' mezőt szétpróbálja osztani 'bal | jobb' minta alapján."""


        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(movies)")
        cols = {r[1] for r in cur.fetchall()}


        if "genre_general" not in cols:
            try:
                cur.execute("ALTER TABLE movies ADD COLUMN genre_general TEXT")
            except sqlite3.OperationalError:
                pass

        if "genre_official" not in cols:
            try:
                cur.execute("ALTER TABLE movies ADD COLUMN genre_official TEXT")
            except sqlite3.OperationalError:
                pass

        cur.execute(
            """
            UPDATE movies
            SET
                genre_general = CASE
                WHEN (genre_general IS NULL OR TRIM(genre_general) = '')
                    AND genre LIKE '%|%'
                THEN TRIM(SUBSTR(genre, 1, INSTR(genre, '|') - 1))
                WHEN (genre_general IS NULL OR TRIM(genre_general) = '')
                THEN genre
                ELSE genre_general
                END,
                genre_official = CASE
                WHEN (genre_official IS NULL OR TRIM(genre_official) = '')
                    AND genre LIKE '%|%'
                THEN TRIM(SUBSTR(genre, INSTR(genre, '|') + 1))
                ELSE genre_official
            END
            WHERE genre IS NOT NULL AND TRIM(genre) <> ''
                AND (
                    genre_general IS NULL OR TRIM(genre_general) = ''
                    OR (genre LIKE '%|%' AND (genre_official IS NULL OR TRIM(genre_official) = ''))
            );
            """
        )


        self.conn.commit()
        cur.close()


    def _migrate_add_new_cols(self) -> None:
        """
        Hozzáadja az új oszlopokat, ha hiányoznak.
        (Idempotens: ha már léteznek, csendben továbblép.)
        """
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(movies)")
        cols = {r[1] for r in cur.fetchall()}

        migrations: list[str] = []

        if "parts_count" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN parts_count INTEGER")

        if "seasonal_tag" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN seasonal_tag TEXT DEFAULT NULL")

        if "seasonal_type" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN seasonal_type TEXT DEFAULT 'none'")

        if "cover_path" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN cover_path TEXT")

        if "video_codec" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN video_codec TEXT")

        if "hdr_type" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN hdr_type TEXT DEFAULT 'none'")

        if "audio_codec" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN audio_codec TEXT")

        if "audio_bitrate" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN audio_bitrate INTEGER")

        if "storage_breakdown" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN storage_breakdown TEXT")

        if "total_size_gb" not in cols:
            migrations.append("ALTER TABLE movies ADD COLUMN total_size_gb REAL")


        for sql in migrations:
            try:
                cur.execute(sql)
            except sqlite3.OperationalError:
                pass

        self.conn.commit()
        cur.close()



    def _migrate_seasonal_type_values(self) -> None:
        cur = self.conn.cursor()

        cur.execute("PRAGMA table_info(movies)")
        cols = {r[1] for r in cur.fetchall()}
        if "seasonal_type" not in cols:
            cur.close()
            return

        cur.execute("""
            UPDATE movies
            SET seasonal_type = 'karácsonyi'
            WHERE seasonal_type IS NOT NULL
            AND LOWER(seasonal_type) IN ('christmas', 'xmas')
        """)
        cur.execute("""
            UPDATE movies
            SET seasonal_type = 'szilveszteri'
            WHERE seasonal_type IS NOT NULL
            AND LOWER(seasonal_type) IN ('newyear', 'new_year', 'new-year')
        """)
        cur.execute("""
            UPDATE movies
            SET seasonal_type = 'mindkettő'
            WHERE seasonal_type IS NOT NULL
            AND LOWER(seasonal_type) IN ('both', 'mixed')
        """)

        self.conn.commit()
        cur.close()










    def _attach_parts_for_details(self, row: dict[str, Any]) -> None:
        """
        Detail_window számára egységes 'Részek' mezők.
        - Film esetén: parts = a fetch_parts_for_movie() eredménye (azonos cím/év alapján)
        - Sorozat esetén: parts = [ {"season": 1}, ... ] parts_count alapján (ha van)
        """
        row_type = (row.get("type") or "").strip().lower()
        title = (row.get("title") or "").strip()
        year = row.get("year")
        try:
            year_int = int(year) if year not in (None, "") else None
        except Exception:
            year_int = None

        # alapértelmezések
        row["parts"] = []
        row["parts_label"] = "-"

        # --- FILM: részek a táblában több sor (azonos title + year) ---
        if row_type == "film" and title:
            parts_rows = self.fetch_parts_for_movie(title, year_int)  # már létező metódus
            # csak akkor legyen "Részek", ha tényleg több értelmes elem van
            meaningful = [p for p in parts_rows if p.get("part") not in (None, 0, "")]
            row["parts"] = parts_rows

            # parts_count normalizálás: ha nincs kitöltve, számoljuk
            if row.get("parts_count") in (None, "", 0):
                if meaningful:
                    mx = 0
                    for p in meaningful:
                        try:
                            mx = max(mx, int(p.get("part") or 0))
                        except Exception:
                            pass
                    if mx > 0:
                        row["parts_count"] = mx

            pc = int(row.get("parts_count") or 0)
            part = int(row.get("part") or 0)

            if pc > 0:
                # pl. "2/5" vagy "0/5"
                row["parts_label"] = f"{part}/{pc}" if part > 0 else f"0/{pc}"
            elif len(meaningful) > 1:
                # ha nincs parts_count, de több part sor van
                row["parts_label"] = str(len(meaningful))

            return

        # --- SOROZAT: nálad parts_count tipikusan évadok száma (ha használod így) ---
        if row_type == "sorozat":
            try:
                pc = int(row.get("parts_count") or 0)
            except Exception:
                pc = 0
            if pc > 0:
                row["parts"] = [{"season": i} for i in range(1, pc + 1)]
                row["parts_label"] = str(pc)

    def _enrich_row_for_ui(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        Egységes UI-kompatibilis rekord:
        - storage_breakdown/total_size_gb normalizálás (nálad már megvan)
        - Részek mezők hozzácsatolása
        """
        _ensure_storage_fields(row)
        self._attach_parts_for_details(row)
        return row












    # --- CRUD / Queries ( Insert, Update, Delete metódusok) ---
    def fetch_all(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id,
                    type,
                    title,
                    part,
                    year,
                    end_year,
                    is_completed,
                    is_seasonal,
                    seasonal_type,
                    genre,
                    genre_general,
                    genre_official,
                    duration,
                    size,
                    storage_location,
                    format_type,
                    format, director,
                    audio_tracks,
                    subtitle_tracks,
                    episode_title,
                    provider,
                    parts_count,
                    seasonal_tag,
                    cover_path,
                    video_codec,
                    hdr_type,
                    audio_codec,
                    audio_bitrate,
                    notes,
                    storage_breakdown,
                    total_size_gb
            FROM movies
            ORDER BY LOWER(title), COALESCE(part, 0), COALESCE(year, 0)
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        for r in rows:
            self._enrich_row_for_ui(r)
        return rows



    def get_by_id(self, movie_id: int) -> dict | None:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM movies WHERE id = ?", (int(movie_id),))
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            self._enrich_row_for_ui(d)
            return d
        finally:
            cur.close()

















    def insert(self, row: dict[str, Any]) -> int:
        title = (row.get("title") or "").strip()
        if not title:
            raise ValueError("A 'title' mező kötelező.")

        # --- Időszakos mező alapértelmezés ---
        # Ha a hívó nem ad seasonal_type-ot, állítsuk "none"-ra
        if "seasonal_type" not in row or not (row.get("seasonal_type") or "").strip():
            row["seasonal_type"] = "none"

        _normalize_alias_fields(row)
        _ensure_storage_fields(row)

        data = {k: row.get(k) for k in ALLOWED_COLS if k in row}
        if not data:
            data = {"title": title}
        else:
            data["title"] = title  # biztosan stripelve

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO movies ({cols}) VALUES ({placeholders})"

        safe_values = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            for v in data.values()
        ]

        cur = self.conn.cursor()
        try:
            cur.execute(sql, safe_values)
            self.conn.commit()
            return cur.lastrowid
        finally:
            cur.close()



    def update(self, movie_id: int, row: dict[str, Any]) -> None:
        # Csak akkor validáljuk a címet, ha a hívó meg is adta
        if "title" in row:
            row["title"] = (row.get("title") or "").strip()
            if not row["title"]:
                raise ValueError("A 'title' mező nem lehet üres.")

        if "seasonal_type" in row:
            # üres → none
            if not (row.get("seasonal_type") or "").strip():
                row["seasonal_type"] = "none"


        _normalize_alias_fields(row)
        _ensure_storage_fields(row)

        data = {k: row.get(k) for k in ALLOWED_COLS if k in row}
        if not data:
            return  # nincs mit frissíteni

        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        sql = f"UPDATE movies SET {set_clause} WHERE id = ?"

        cur = self.conn.cursor()
        try:
            cur.execute(sql, list(data.values()) + [movie_id])
            self.conn.commit()
        finally:
            cur.close()


    def delete_by_id(self, row_id: int) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM movies WHERE id = ?", (row_id,))
            self.conn.commit()
        finally:
            cur.close()




    def delete_by_title(self, title: str) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM movies WHERE title = ?", ((title or "").strip(),))
            self.conn.commit()
        finally:
            cur.close()


    def clear_all_movies(self) -> int:
        """
        Minden rekord törlése a movies táblából.
        Visszatér: hány sort törölt.
        """
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM movies;")
            deleted = cur.rowcount
            self.conn.commit()
        finally:
            cur.close()

        # Opcionális: VACUUM, hogy a fájlméret is zsugorodjon
        cur2 = self.conn.cursor()
        try:
            cur2.execute("VACUUM;")
            self.conn.commit()
        finally:
            cur2.close()


        # Log:
        LOGGER.info("Adatbázis ürítve. Törölt sorok: %s", deleted)

        return deleted if deleted is not None else 0





        # --- Kereső motor: szöveg + időszakos kulcsszavak ---
    def _apply_seasonal_filters(self, text: str, conditions: list[str], params: list) -> str:
        """
        Feldolgozza a szöveget és kiszedi belőle a szezonális kulcsszavakat
        (karácsonyi, szilveszteri), majd SQL feltételt ad hozzá.

        Visszatér: a "megtisztított" keresőszöveggel.
        """
        if not text:
            return text

        t = text.lower()

        # Kulcsszavas detektálás
        has_christmas = any(p in t for p in ["karácsony", "karacsony", "karácsonyi", "karacsonyi"])
        has_newyear   = any(p in t for p in ["szilveszter", "szilveszteri"])

        seasonal_conds: list[str] = []

        if has_christmas:
            # 1) explicit seasonal_type (karácsonyi VAGY mindkettő)
            seasonal_conds.append("LOWER(seasonal_type) IN ('karácsonyi','mindkettő')")

            # 2) seasonal_tag tartalmazza a karácsonyt
            seasonal_conds.append("LOWER(COALESCE(seasonal_tag, '')) LIKE '%karácsony%'")

            # 3) régi adatok: csak is_seasonal = 1, seasonal_type még 'none'/NULL
            seasonal_conds.append(
                "(is_seasonal = 1 AND (seasonal_type IS NULL OR seasonal_type = 'none'))"
            )

        if has_newyear:
            # Szilveszteri: explicit típus/tag alapján (szilveszteri VAGY mindkettő)
            seasonal_conds.append("LOWER(seasonal_type) IN ('szilveszteri','mindkettő')")
            seasonal_conds.append("LOWER(COALESCE(seasonal_tag, '')) LIKE '%szilveszter%'")

        if seasonal_conds:
            conditions.append("(" + " OR ".join(seasonal_conds) + ")")

            # tisztítsuk a szöveget, hogy a LIKE ne keresse ezeket a szavakat
            for p in [
                "karácsonyi", "karacsonyi", "karácsony", "karacsony",
                "szilveszteri", "szilveszter"
            ]:
                t = t.replace(p, "")

        return t.strip()






    def search_movies(self, text: str) -> list[dict]:
        """
        SQL-alapú keresés a címre + időszakos kulcsszavakra.
        A main_window apply_filter() ezt fogja hívni.
        """
        conditions = []
        params = []

        raw = (text or "").strip().lower()

        # Szezonális kulcsszavak kezelése
        cleaned = self._apply_seasonal_filters(raw, conditions, params)

        # Maradék szöveg LIKE
        if cleaned:
            conditions.append("(LOWER(title) LIKE ?)")
            params.append(f"%{cleaned}%")

        where = " AND ".join(conditions) if conditions else "1"
        sql = f"""
            SELECT *
            FROM movies
            WHERE {where}
            ORDER BY LOWER(title), COALESCE(part,0), COALESCE(year,0)
        """

        cur = self.conn.cursor()
        cur.execute(sql, params)

        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        for r in rows:
            self._enrich_row_for_ui(r)
        return rows





    def fetch_parts_for_movie(self, title: str, year: int | None) -> list[dict]:
        """
        Visszaadja az azonos című (és ha van év, akkor azonos évű) filmrészeket.
        A part szerinti sorrend fontos.
        """
        title = (title or "").strip()
        if not title:
            return []

        cur = self.conn.cursor()
        try:
            if year is None:
                cur.execute(
                    """
                    SELECT id, part, size, storage_location
                    FROM movies
                    WHERE type='film' AND title=?
                    ORDER BY COALESCE(part, 999999), id
                    """,
                    (title,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, part, size, storage_location
                    FROM movies
                    WHERE type='film' AND title=? AND year=?
                    ORDER BY COALESCE(part, 999999), id
                    """,
                    (title, year),
                )

            rows = cur.fetchall()
            out = []
            for r in rows:
                out.append(
                    {
                        "id": r[0],
                        "part": r[1],
                        "size": r[2],
                        "storage_location": r[3],
                    }
                )
            return out
        finally:
            cur.close()




