# First Run Wizard — archivált kód (csak Windows build esetén javasolt)

## Miért lett kivéve a `main` (Linux) ágból?

A Linux `main` ágon a DB útvonal **mindig fix**, a `config.py`-beli `IS_INSTALLED`
flag dönti el:

- telepített (`.deb`) állapotban → `~/.local/share/FilmekAdatbazis/movies.db`
- fejlesztői módban → `_appdata/dev/movies.db`

A felhasználó Linuxon **sosem választ** DB helyet — nincs erre igény, és a
`QSettings`-alapú `db_path` felülírás csak zavaró duplikációt okozott a
naplózásban (a `config.DB_PATH` és a ténylegesen használt útvonal eltért
egymástól, mert a `QSettings`-ben egy korábbi futtatásból megmaradt érték
felülbírálta a config alapértéket).

## Mikor érdemes visszahozni?

**Kizárólag Windows build esetén**, ahol nincs olyan egységes, kiszámítható
adatkönyvtár-konvenció, mint Linuxon a `~/.local/share/`. Windowson hasznos
lehet, ha a felhasználó az első indításkor eldöntheti:
- hozzon létre egy új, üres adatbázist egy általa választott helyen, vagy
- nyisson meg egy már meglévő adatbázis-fájlt (amit a program bemásol
  `shutil.copy2`-vel a saját `_appdata` könyvtárába, hogy elkerülje egy
  külső fájl véletlen módosítását).

Ha Windows build mégsem valósul meg, ez a fájl egyszerűen archívumként marad.

## 1. `resolve_db_path()` függvény (main.py-ból)

```python
def resolve_db_path() -> Path:
    """
    Visszaadja a használandó adatbázis útvonalat.
    - Ha van elmentett és létező db_path a QSettings-ben, azt használjuk.
    - Különben visszaesünk a config.DB_PATH alapértelmezettre.
    """
    settings = QSettings(APP_ORG, APP_NAME)
    saved_path = settings.value("db_path", "", str)
    if saved_path:
        p = Path(saved_path)
        if p.exists():
            return p
        LOGGER.warning(
            "Elmentett db_path nem letezik: %s. Visszaesunk az alapertelmezettre.", saved_path
        )
    return DB_PATH
```

## 2. `main()` döntési blokk (main.py-ból)

Ez a blokk a `main()` függvényen belül, az `app.setApplicationName(APP_NAME)`
sor után, a téma alkalmazása előtt helyezkedett el:

```python
    # --- Első indítás ellenőrzése ---
    settings = QSettings(APP_ORG, APP_NAME)
    saved_db_path = settings.value("db_path", "", str)
    db_path: Path | None = None
    if not saved_db_path:
        LOGGER.info("Nincs mentett db_path, elso inditas varazslo indul.")
        wizard = FirstRunWizard(DB_PATH)
        if wizard.exec():
            chosen = wizard.chosen_db_path()
            if chosen:
                settings.setValue("db_path", chosen)
                settings.sync()
                LOGGER.info("First run wizard: db_path elmentve: %s", chosen)
                db_path = Path(chosen)
        else:
            LOGGER.info("Első indítás Varázsló megszakítva. Kilépés...")
            return 0
    if db_path is None:
        db_path = resolve_db_path()
    LOGGER.info("Hasznalt adatbazis: %s", db_path)
```

Szükséges import ehhez a blokkhoz:

```python
from wizard.first_run_wizard import FirstRunWizard
```

## 3. A wizard osztály maga

A teljes `FirstRunWizard` osztály a `wizard/first_run_wizard.py` fájlban van,
és **ez a fájl nem lett törölve** a repóból — a `main` ágon egyszerűen nincs
importálva/meghívva sehonnan. Ha Windows build készül, ez a fájl változatlanul
felhasználható, `QWizard`/`QWizardPage` alapon épül, opciókkal:
- új, üres adatbázis létrehozása
- meglévő adatbázis megnyitása (`shutil.copy2` másolással az app saját
  `_appdata` könyvtárába)

## Visszaállítás lépései (ha Windows build esetén szükség lesz rá)

1. Add vissza az importot a `main.py` tetejére:
   `from wizard.first_run_wizard import FirstRunWizard`
2. Illeszd vissza a `resolve_db_path()` függvényt a `main.py`-ba (1. pont
   kódja fentebb).
3. Illeszd vissza a `main()`-beli döntési blokkot (2. pont kódja fentebb),
   a `db_path = DB_PATH` sor helyére.
4. Ellenőrizd, hogy a `wizard/first_run_wizard.py` naprakész-e (nem változott
   azóta, hogy kikerült a main ágból).

## Megjegyzés a `QSettings` "árva" bejegyzésről

A Linux gépeken, ahol korábban lefutott a wizard (vagy manuálisan be lett
állítva egy `db_path` a `QSettings`-ben), ez az érték **megmarad** a
`~/.config/Filmekadatbazis/FilmekAdatbazis.conf`-ban, de a `main` ág mostantól
nem olvassa ki. Törléséhez (ha valaha zavarna):

```bash
python -c "from PySide6.QtCore import QSettings; s = QSettings('Filmekadatbazis', 'FilmekAdatbazis'); s.remove('db_path'); s.sync(); print('torolve')"
```