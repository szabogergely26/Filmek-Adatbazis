# Verziószámozás

A projekt szemantikus verziószámozást (SemVer) követ: `MAJOR.MINOR.PATCH`, pl. `10.1.0`.

## Szabályok

**MAJOR** — nagy, visszafelé nem kompatibilis változás (pl. adatbázis-séma átírás migráció nélkül, teljes UI-újratervezés).
→ `MINOR` és `PATCH` nullázódik. Példa: `10.4.2` → `11.0.0`

**MINOR** — új funkció, visszafelé kompatibilis módon.
→ `PATCH` nullázódik. Példa: `10.0.5` → `10.1.0`

**PATCH** — hibajavítás, refaktor, apró UX-finomítás; nincs új funkció.
→ Csak a `PATCH` nő. Példa: `10.1.0` → `10.1.1`

## Vegyes tartalmú kiadás

Ha egy kiadás új funkciót **és** hibajavítást is tartalmaz egyszerre, a `MINOR` emelés a mérvadó
(a hibajavítás "beleolvad"), a `PATCH` ilyenkor is nullázódik.

Példa: keresőmező storage-szűrés (új funkció) + cover-kezelés bugfix (javítás) egy kiadásban
→ `10.0.1` → `10.1.0`, nem `10.1.1`.

## Hol kell frissíteni

Kiadáskor mindhárom helyen egységesen:

- `config.py` → `APP_VERSION` konstans
- `changelog.html` → új bejegyzés a változásokról
- `README.md` → verziószám említése (ha szerepel)

## Verzió láthatósága

A verziószám csak az alkalmazáson belül jelenik meg (pl. Beállítások / Névjegy nézetben).
Nem szerepel fájlnevekben vagy release tag-ekben — a GitHub Releases "latest" rolling tag
stratégiát használ (lásd README, "Stabil letöltési URL" szakasz).
