#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


# ==== BEÁLLÍTÁSOK ====
DB_PATH = Path.home() / ".local" / "share" / "Filmekadatbazis" / "movies.db"       # írd át, ha máshol van a DB
BACKUP_SUFFIX = ".pre_storage_migration.bak"

# A régi oszlop neve a movies táblában:
OLD_LOCATION_COLUMN = "storage_location"

# Ha akarod, később ezeket is lehet bővíteni:
DEFAULT_LOCATION_TYPE = "physical"
DEFAULT_NOTES = None


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT 'physical',
            notes TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS movie_storage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            note TEXT,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
            UNIQUE(movie_id, location_id)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_locations_name
        ON locations(name)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_movie_storage_movie_id
        ON movie_storage(movie_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_movie_storage_location_id
        ON movie_storage(location_id)
    """)


def ensure_location(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM locations WHERE name = ?",
        (name,)
    ).fetchone()

    if row:
        return row[0]

    cur = conn.execute(
        "INSERT INTO locations (name, type, notes) VALUES (?, ?, ?)",
        (name, DEFAULT_LOCATION_TYPE, DEFAULT_NOTES)
    )
    return cur.lastrowid


def migrate_storage(conn: sqlite3.Connection) -> tuple[int, int]:
    cols = table_columns(conn, "movies")
    if OLD_LOCATION_COLUMN not in cols:
        raise RuntimeError(
            f"A(z) '{OLD_LOCATION_COLUMN}' oszlop nem található a movies táblában.\n"
            f"Elérhető oszlopok: {', '.join(sorted(cols))}"
        )

    rows = conn.execute(
        f"""
        SELECT id, {OLD_LOCATION_COLUMN}
        FROM movies
        WHERE {OLD_LOCATION_COLUMN} IS NOT NULL
          AND TRIM({OLD_LOCATION_COLUMN}) != ''
        """
    ).fetchall()

    created_links = 0
    used_locations: set[str] = set()

    for movie_id, raw_location in rows:
        location_name = str(raw_location).strip()
        if not location_name:
            continue

        location_id = ensure_location(conn, location_name)
        used_locations.add(location_name)

        conn.execute(
            """
            INSERT OR IGNORE INTO movie_storage (movie_id, location_id, note)
            VALUES (?, ?, ?)
            """,
            (movie_id, location_id, None)
        )

        # SQLite-nál az INSERT OR IGNORE után így lehet nézni, lett-e tényleges insert:
        changes = conn.execute("SELECT changes()").fetchone()[0]
        if changes > 0:
            created_links += 1

    return created_links, len(used_locations)


def make_backup(db_path: Path) -> Path:
    backup_path = db_path.with_name(db_path.name + BACKUP_SUFFIX)
    shutil.copy2(db_path, backup_path)
    return backup_path


def main() -> None:
    print(f"DB path: {DB_PATH}")
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Nem található az adatbázis: {DB_PATH}")

    backup_path = make_backup(DB_PATH)
    print(f"Backup készült: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        ensure_tables(conn)
        created_links, unique_locations = migrate_storage(conn)
        conn.commit()

        print("Migráció kész.")
        print(f"Létrehozott kapcsolatok: {created_links}")
        print(f"Egyedi tárolási helyek: {unique_locations}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
