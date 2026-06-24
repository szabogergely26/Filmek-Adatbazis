# Filmek-Adatbazis  - Fejlesztői

Filmek-Adatbázis helye


## Főbb modulok

### `main_window.py`

* főablak
* menüsor
* bal oldali navigáció
* adatbázis oldal
* kártya/lista nézet váltás
* szűrők
* import/export
* súgó, névjegy, változásnapló, log ablak

### `details_dialog.py`

* modern részletek ablak

### `edit_dialog.py`

* meglévő film/sorozat szerkesztése

### `wizard.py`

* új film/sorozat felvétele varázslóval

### `movie_card.py`

* kártyanézet egy film/sorozat kártyája

### `list_view.py`

* lista nézet

### `log_window.py`

* log megjelenítő ablak

### `settings_dialog.py`

* beállítások ablak

### `theme_utils.py`

* téma betöltése / alkalmazása

### `config.py`

* app név, verzió
* útvonalak
    * `DB_PATH`
    * `LOG_PATH`




## Későbbi UI-polírozás

### - Menüelemek ikonozása Qt / rendszer témaikonokkal
  * - Fájl menü: hozzáadás, import, export, kilépés
  * - Adatok menü: frissítés, adatbázis műveletek, beállítások
  * - Súgó menü: súgó, változásnapló, névjegy, log ablak

### - Külön eszköztár nem szükséges
  * - A menüsor, a bal oldali navigáció és az oldalak saját gombjai elegendők.
  * - Egy külön toolbar jelenleg csak ismételné a már meglévő funkciókat.

### - Kezdőoldal vízszintes görgetősáv témázása
  * - A Kezdőoldalon megjelenő vízszintes scrollbar stílusa legyen egységes az Adatbázis rész görgetősávjával.
  * - Modern témában ugyanazt a scrollbar QSS-t használja, mint az Adatbázis nézet.
  * - Classic témában maradjon visszafogott, Qt-native jellegű.
  * - Cél: a Kezdőoldal és az Adatbázis oldal vizuálisan egységesebb legyen.