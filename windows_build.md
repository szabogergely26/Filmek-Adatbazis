# Windows build útmutató — Filmek-Adatbázis

> ⚠️ **Ez a leírás egyelőre VÁZLAT.** A PyInstaller és Inno Setup lépések
> ehhez a projekthez még nincsenek kidolgozva — a lenti szakaszok
> placeholder-ként szerepelnek, hogy a struktúra készen álljon, amint a
> tényleges csomagolási lépések elkészülnek. A `[TODO: ...]` jelölésű
> részeket kell kitölteni, mihelyt megvan a konkrét PyInstaller
> parancs / Inno Setup fájl-elrendezés.

Ez a leírás azoknak szól, akik **saját maguk** szeretnék lefordítani és
telepíteni a Filmek-Adatbázist Windows-on, a forráskódból kiindulva.

> A fejlesztő (Szabó Gergely) Linux alatt dolgozik, és nem vállal
> folyamatos Windows csomagolást/karbantartást. Ez a leírás egyszeri,
> önkiszolgáló útmutató — ha valami elakad, a hibaüzenet és a lenti
> "Gyakori hibák" szakasz általában elég támpontot ad.

---

## Amire szükséged lesz

- Windows 10/11 (x64)
- [Python 3.11+](https://www.python.org/downloads/) (telepítéskor pipáld be a "Add python.exe to PATH"-t)
- [Inno Setup 6/7](https://jrsoftware.org/isinfo.php) (a telepítő `.exe` legyártásához) — `[TODO: ha végül más csomagolót választunk, itt frissítendő]`
- Git

---

## 1. lépés — Forráskód beszerzése

```powershell
git clone https://github.com/<repo-url>/filmek-adatbazis.git
cd filmek-adatbazis
```

Elérhető Windows branch-ek jelenleg:

- `windows/stable` — stabil verzió
- `windows/dev` — fejlesztői verzió (belső tesztelésre, nem publikus kiadás)

> **Nincs `windows/preview` ág** — ha a projektben később bevezetésre kerül
> az Előzetes (Preview) csatorna (a Pénzügyi Napló mintájára), ez a szakasz
> bővítendő.

```powershell
git checkout windows/stable
```

---

## 2. lépés — Python virtuális környezet

```powershell
python -m venv venv
```

**Aktiválás:**

```powershell
venv\Scripts\activate
```

Ha ezt a hibát kapod:

```
File ...\venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system.
```

akkor a PowerShell biztonsági beállítása blokkolja a szkriptet. Ez a parancs
**csak az aktuális ablakra** oldja fel (nem kell rendszerszinten semmit módosítani):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
```

Sikeres aktiválás esetén a sor elején megjelenik: `(venv)`.

Ezután telepítsd a függőségeket:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

---

## 3. lépés — Standalone .exe legyártása (PyInstaller)

`[TODO: ez a lépés még nincs kidolgozva ehhez a projekthez.]`

Várhatóan a Pénzügyi Napló mintáját követi majd:

```powershell
pyinstaller [TODO: belépési pont, pl. main.py] --name [TODO: AppName] --windowed --icon [TODO: ikon .ico útvonala] --workpath build\pyinstaller --distpath dist --noconfirm
```

**Fontos (a Pénzügyi Napló tapasztalata alapján):** ezt a lépést **minden
alkalommal újra kell futtatni**, ha branch-et váltasz (pl. stable → dev),
különben a régi, elavult build kerül becsomagolásra — ablakcímben, Névjegyben
stb. a rossz verzió jelenik meg.

---

## 4. lépés — Telepítő csomagolása (Inno Setup)

`[TODO: ez a lépés még nincs kidolgozva ehhez a projekthez — nincsenek még
.iss fájlok.]`

Várhatóan a Pénzügyi Napló mintáját követi majd: egy közös `common.iss`
logikafájl + vékony variant fájlok (`installer-stable.iss`,
`installer-dev.iss`), hogy a variánsok egymás mellett, egymást felül nem
írva telepíthetők legyenek ugyanarra a gépre (külön `AppId`, ikon, célmappa).

---

## Gyakori hibák

| Hiba | Ok | Megoldás |
|---|---|---|
| `pyinstaller : term not recognized` | A venv nincs aktiválva | `venv\Scripts\activate` (lásd 2. lépés) |
| `running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Klasszikus kék "Windows protected your PC" képernyő | A hagyományos SmartScreen — a telepítő/exe nincs digitálisan aláírva, még nincs elég "reputációja" | A "További információ" → "Futtatás mindenképp" opcióval felülbírálható, saját felelősségre. |
| "Az Intelligens alkalmazáskezelés letiltott egy alkalmazást, amely esetleg nem biztonságos" | Ez **nem** a klasszikus SmartScreen, hanem a **Smart App Control (SAC)** — lásd külön szakasz lent | Lásd "Smart App Control (SAC)" szakasz lent |

---

## Smart App Control (SAC) — mit tegyél, ha letiltja a programot

Ha a fenti "Intelligens alkalmazáskezelés" üzenetet kapod, az nem azt jelenti,
hogy a build hibás vagy a program vírusos — ez egy Windows 11-es funkció,
ami **kizárólag aláíratlan** futtatható fájlokat (exe, dll, telepítő) tilt le,
függetlenül attól, hogy honnan származnak.

**Miért fordulhat elő akkor is, ha te magad fordítod a saját gépeden?**

A SAC két módban működhet:
- **Evaluation (kiértékelő) mód** — ez az alapállapot egy friss Windows 11
  telepítésen. Ilyenkor a rendszer csak figyel, nem tilt le semmit.
- **Enforce (kikényszerítő) mód** — a rendszer egy idő után automatikusan
  átválthat erre a módra a háttérben, akár egyetlen felhasználó/gép
  beavatkozása nélkül is. Innentől **minden** aláíratlan futtatható
  (a saját maga fordította exe is) blokkolva lehet — nem számít, hogy
  sosem lett letöltve internetről, helyben lett fordítva.

**Ellenőrzés és kikapcsolás:**

1. `Windows Security` (Windows Biztonság) → `App & browser control`
   (Alkalmazás- és böngészővezérlés) → `Smart App Control settings`
   (Intelligens alkalmazáskezelés beállításai).
2. Ha az állapot `On` (Be), állítsd `Off`-ra (Ki) — akár csak ideiglenesen,
   a teszteléshez.
3. Ha a Windows Security appban nem jelenik meg ez az opció (régebbi build),
   a registry-n keresztül is állítható:
   ```
   regedit.exe
   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CI\Policy
   VerifiedAndReputablePolicyState → állítsd 0-ra (kikapcsolás)
   ```
   majd indítsd újra a gépet.

> **Fontos:** a kikapcsolás **nem feltétlenül végleges** — a rendszer a
> viselkedés alapján később **magától újra bekapcsolhatja** a SAC-ot.
> Érdemes ezt a beállítást időről időre ellenőrizni, ha a program
> hirtelen leáll futni.

**Ha valaki más (nem te) fut bele ebbe, amikor a te forráskódodból fordít:**
Ez elméletileg őt is érintheti, ha az ő gépén a SAC Enforce módban fut —
ez nem a build-en vagy a fordításon múlik, hanem kizárólag azon, hogy az
adott gépen a SAC épp melyik módban van.

**Miért nem oldja meg ezt tartósan/mindenkinek a fenti lépés?**
A SAC kikapcsolása csak az adott gépen, ideiglenesen oldja fel a blokkolást,
és mint fent említve, magától vissza is kapcsolódhat. Egy szélesebb körben,
idegen felhasználóknak szánt, aláíratlan telepítő tartós, felhasználói
beavatkozás nélküli terjesztéséhez **code signing certificate** kellene
(kb. 200+ USD/év, OV szinten) — ez jelenleg tudatosan **nincs** ennek a
projektnek a tervei között, ezért marad a forráskódos fordítás mint
elsődleges (és egyetlen) Windows-út. Ennek megfelelően **nincs is publikus
letöltési gomb** kész Windows telepítőhöz — csak ez a leírás.

---

*Ez a leírás vázlat, a Pénzügyi Napló projekt hasonló dokumentációjának
mintájára. Frissítendő, amint a PyInstaller és Inno Setup lépések
konkretizálódnak a Filmek-Adatbázishoz.*