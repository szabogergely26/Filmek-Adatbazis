#!/usr/bin/env bash
set -euo pipefail

PACKAGE_NAME="filmek-adatbazis"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Verziószám kiolvasása a config.py-ból (egyetlen forrás az igazságra)
VERSION=$(grep -oP '(?<=APP_VERSION = ")[^"]+' "$PROJECT_DIR/app/config.py")

if [[ -z "$VERSION" ]]; then
    echo "HIBA: nem sikerült kiolvasni az APP_VERSION-t a config.py-ból!" >&2
    exit 1
fi


BUILD_DIR="$SCRIPT_DIR/build"
ROOT_DIR="$SCRIPT_DIR/root"
DIST_DIR="$PROJECT_DIR/dist"

PACKAGE_DIR="$BUILD_DIR/package"
DEBIAN_DIR="$PACKAGE_DIR/DEBIAN"

echo "Projekt könyvtár: $PROJECT_DIR"
echo "Csomag neve: $PACKAGE_NAME"
echo "Verzió: $VERSION"

rm -rf "$BUILD_DIR"
mkdir -p "$PACKAGE_DIR"
mkdir -p "$DEBIAN_DIR"
mkdir -p "$DIST_DIR"

# Alap root fájlok másolása
cp -a "$ROOT_DIR/." "$PACKAGE_DIR/"

# App másolása
mkdir -p "$PACKAGE_DIR/usr/share/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR/usr/share/doc/$PACKAGE_NAME"

cp -a "$PROJECT_DIR/app" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/"
cp -a "$PROJECT_DIR/cover" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/" 2>/dev/null || true
cp -a "$PROJECT_DIR/database" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/" 2>/dev/null || true
cp -a "$PROJECT_DIR/ikonok" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/" 2>/dev/null || true
cp -a "$PROJECT_DIR/settings.json" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/" 2>/dev/null || true
cp -a "$PROJECT_DIR/requirements.txt" "$PACKAGE_DIR/usr/share/$PACKAGE_NAME/" 2>/dev/null || true
cp -a "$PROJECT_DIR/README.md" "$PACKAGE_DIR/usr/share/doc/$PACKAGE_NAME/README.md" 2>/dev/null || true

# Ikon telepítése hicolor alá, ha létezik
ICON_SRC="$PROJECT_DIR/ikonok/sajat/movies2.png"
ICON_DEST="$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps"

if [[ -f "$ICON_SRC" ]]; then
    mkdir -p "$ICON_DEST"
    cp "$ICON_SRC" "$ICON_DEST/$PACKAGE_NAME.png"
fi

# Dokumentáció könyvtár
mkdir -p "$PACKAGE_DIR/usr/share/doc/$PACKAGE_NAME"

# DEBIAN/control — control.in sablonból generálva, VERSION behelyettesítve
sed "s/@VERSION@/$VERSION/" "$SCRIPT_DIR/control.in" > "$DEBIAN_DIR/control"

# Jogosultságok
chmod 755 "$PACKAGE_DIR/usr/bin/$PACKAGE_NAME"

# Python cache törlése
# Python cache fájlok eltávolítása a csomagból
find "$PACKAGE_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$PACKAGE_DIR" -type f -name "*.pyc" -delete
find "$PACKAGE_DIR" -type f -name "*.pyo" -delete

# Csomag építése
# A kimeneti fájl MINDIG fix nevű, verziószám nélkül,
# hogy a weboldali/APT letöltési linket soha ne kelljen módosítani.
OUTPUT_FILE="$DIST_DIR/${PACKAGE_NAME}.deb"


dpkg-deb --root-owner-group --build "$PACKAGE_DIR" "$OUTPUT_FILE"

echo
echo "======================================"
echo "  Csomag elkészült (v$VERSION)"
echo "======================================"
echo "  Fájl: $OUTPUT_FILE"
echo "  Méret: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "======================================"
echo
echo "Telepítéshez:"
echo "  sudo dpkg -i $OUTPUT_FILE"
echo
