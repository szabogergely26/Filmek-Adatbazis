# --- README for Filmek-Adatbázis ---

## Filmek Adatbázis

**Filmek Adatbázis** egy helyi, offline használatra készült film- és sorozatkatalógus alkalmazás.
A program célja, hogy a saját filmek, sorozatok, részek, évadok, tárhelyek, formátumok és kiegészítő adatok áttekinthetően kezelhetők legyenek egy asztali grafikus felületen.

A projekt jelenlegi állapota: **Filmek Adatbázis 10.0**.

---

## Fő funkciók

- Filmek és sorozatok nyilvántartása.
- Új tétel felvétele varázslóval.
- Meglévő film/sorozat szerkesztése.
- Modern részletek ablak.
- Kártyanézet és listanézet.
- Szűrők és keresés.
- Többrészes filmek és sorozatévadok kezelése.
- Tárhely / méret / formátum / felbontás / hangsáv / felirat adatok kezelése.
- Borítóképek megjelenítése.
- Import / export funkciók.
- Beállítások ablak.
- Modern / klasszikus megjelenés.
- Naplózás és log megtekintő ablak.
- Egypéldányos indításvédelem.

---

## Jelenlegi állapot

A projekt jelenleg fejlesztői futtatásra van felkészítve.

Már rendben van:

- Python/PySide6 alapú GUI.
- Ruff ellenőrzés beállítva.
- `python -m ruff check .` jelenleg tiszta állapotot ad.
- Alkalmazás fejlesztői módban futtatható.
- Projektstruktúra nagyjából szét van választva modulokra.

Még nincs kész:

- Debian `.deb` csomag.
- Frissíthető APT szoftverforrás.
- GitHub Actions alapú DEB build.
- Stabil telepített adatkönyvtár-logika teljes leválasztása a fejlesztői projektkönyvtárról.
- Windows build / installer.

---

## Technológia

- Python 3
- PySide6
- SQLite
- Ruff
- Bash indítószkript

A jelenlegi `requirements.txt` fő függőségei:

```text
PySide6==6.10.2
PySide6_Addons==6.10.2
PySide6_Essentials==6.10.2
shiboken6==6.10.2
```

---

## Fejlesztői futtatás

### 1. Virtuális környezet létrehozása

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Függőségek telepítése

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Indítás

A projekt gyökeréből:

```bash
./run.sh
```

Vagy közvetlenül:

```bash
cd app
../venv/bin/python ./movies7.0.py
```

---

## Ruff ellenőrzés

A projekt Ruff-fal ellenőrizhető.

```bash
python -m ruff check .
```

A jelenlegi cél:

```text
All checks passed!
```

A Ruff konfiguráció a `pyproject.toml` fájlban található.

Jelenlegi fő beállítások:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## Adatkönyvtárak

Fejlesztői módban az alkalmazás jelenleg a projektkönyvtár alatt dolgozik:

```text
_appdata/dev/
```

Itt található fejlesztői futáskor:

```text
_appdata/dev/movies.db
_appdata/dev/logs/
_appdata/dev/Movies7.conf
```

A későbbi telepített stabil verziónál célszerű külön felhasználói adatkönyvtárat használni, például:

```text
~/.local/share/FilmekAdatbazis/
```

Ez azért fontos, mert egy DEB csomagból telepített alkalmazás nem írhat a `/usr/share/...` programkönyvtárba.

---

## Borítóképek

A borítóképek jelenleg külön `cover/` könyvtárban lehetnek.

Fontos:

- A `cover/` felhasználói adatnak tekintendő.
- A személyes borítógyűjtemény nem való automatikusan a DEB csomagba.
- Később érdemes külön kezelni a beépített minta-/assetképeket és a felhasználói borítókat.

---

## Projektstruktúra

```text
app/
  movies7.0.py
  main_window.py
  config.py
  changelog.html

  db/
    database_manager.py

  dialogs/
    details_dialog.py
    edit_dialog.py
    log_window.py
    settings_dialog.py

  themes/
    icons.py
    style.css
    theme_utils.py

  tools/
    diag_movies.py
    migrate_storage.py

  utils/
    storage_breakdown_utils.py
    utils.py

  views/
    list_view.py
    movie_card.py

  wizard/
    wizard.py

  assets/
    filmek.ico
    filmek.png
    wizard/
      local.png
      online.png
```

---

## Fontosabb fájlok

### `app/movies7.0.py`

Az alkalmazás fő belépési pontja.
Feladatai:

- QApplication létrehozása.
- Egypéldányos védelem.
- Globális hibakezelés.
- Adatbázis-kezelő indítása.
- Főablak létrehozása.
- Téma alkalmazása.

### `app/main_window.py`

A főablak modulja.
Tartalmazza:

- menüsor
- bal oldali navigáció
- kezdőoldal
- adatbázis oldal
- kártyanézet / listanézet váltás
- szűrők
- import / export
- súgó / névjegy / változásnapló
- log ablak indítása

### `app/config.py`

Központi konfiguráció:

- alkalmazásnév
- verzió
- ikonútvonalak
- adatbázis útvonala
- logolás
- beállítások
- UI konstansok

### `app/db/database_manager.py`

SQLite adatbázis-kezelés.

### `app/wizard/wizard.py`

Új film vagy sorozat felvételére szolgáló varázsló.

### `app/dialogs/details_dialog.py`

Modern részletek ablak.

### `app/dialogs/edit_dialog.py`

Meglévő tétel szerkesztése.

### `app/views/movie_card.py`

Kártyanézet egy film/sorozat kártyájához.

### `app/views/list_view.py`

Lista nézet.

### `app/dialogs/settings_dialog.py`

Beállítások ablak.

### `app/dialogs/log_window.py`

Log megjelenítő ablak.

### `app/themes/theme_utils.py`

Témák betöltése és alkalmazása.

### `app/themes/icons.py`

Ikon- és provider ikonkezelés.

---

## Naplózás

A program fájlba és konzolra is képes naplózni.

A naplózást környezeti változókkal is lehet befolyásolni:

```bash
FILMEK_LOG_CONSOLE=1
FILMEK_LOG_FILE=1
FILMEK_LOG_LEVEL=DEBUG
```

Példa:

```bash
FILMEK_LOG_LEVEL=INFO ./run.sh
```

---

## Import / export

Az alkalmazás tartalmaz import / export funkciókat, amelyek a filmadatbázis mentésére és visszaállítására szolgálnak.

A későbbi DEB csomagolásnál külön figyelni kell arra, hogy:

- a felhasználói adatbázis ne kerüljön bele a csomagba,
- a csomag csak az alkalmazást és a szükséges statikus asseteket tartalmazza,
- az adatbázis a felhasználó saját adatkönyvtárában jöjjön létre.

---

## Csomagolási állapot

Jelenleg még nincs kész Debian csomagolás.

Későbbi cél:

```text
filmek-adatbazis.deb
```

Tervezett parancs:

```bash
filmek-adatbazis
```

Tervezett desktop fájl:

```text
/usr/share/applications/filmek-adatbazis.desktop
```

Tervezett telepítési hely:

```text
/usr/share/filmek-adatbazis/
```

Tervezett felhasználói adatkönyvtár:

```text
~/.local/share/FilmekAdatbazis/
```

Későbbi cél az is, hogy a DEB csomag automatikusan beállítsa az alkalmazás APT szoftverforrását, hasonlóan a többi saját projekthez.

---

## Tervezett későbbi feladatok

- Debian DEB csomag létrehozása.
- Frissíthető APT szoftverforrás kialakítása.
- GitHub Actions alapú DEB build.
- Stabil telepített adatútvonal beállítása.
- README további bővítése képernyőképekkel.
- LICENSE fájl hozzáadása.
- GPL-3.0 licenc tisztázása / bevezetése.
- Windows build / installer később.
- Frissítéskezelés későbbi Windows verzióhoz.

---

## Fejlesztési megjegyzés

A projekt jelenleg nem használ külön Preview csatornát.

Javasolt egyszerű ágmodell:

```text
main  = stabil állapot
dev   = fejlesztés
```

A jelenlegi Ruff-takarítás után a kód ellenőrizhetőbb és könnyebben karbantartható.
