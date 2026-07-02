#  /app/version_info.py
# ----------------------


"""
Központi alkalmazás-, verzió- és kiadási csatorna információk.

Ez legyen az egyetlen hely, ahol az app neve, verziója, csatornája,
csomagneve és megjelenített neve alapértelmezés szerint definiálva van.
"""


APP_NAME = "FilmekAdatbazis"
APP_DISPLAY_NAME = "Filmek Adatbázis"
APP_ORG = "Filmekadatbazis"

APP_VERSION = "10.0"
DEB_VERSION = APP_VERSION
APP_CHANNEL = "stable"


CHANNEL_LABELS = {
    "stable": "Stabil",
    "preview": "Előzetes",
    "dev": "Fejlesztői",
}


APP_CHANNEL_LABEL = CHANNEL_LABELS.get(APP_CHANNEL, APP_CHANNEL)


PACKAGE_NAME = "filmek-adatbazis"
EXECUTABLE_NAME = PACKAGE_NAME
DESKTOP_FILE_NAME = f"{PACKAGE_NAME}.desktop"
DESKTOP_FILE_ID = PACKAGE_NAME
ARTIFACT_NAME = f"{PACKAGE_NAME}_{DEB_VERSION}"


def get_window_title() -> str:
    """Ablakcím előállítása az aktuális verzió- és csatornaadatokból."""

    if APP_CHANNEL == "stable":
        return f"{APP_DISPLAY_NAME} {APP_VERSION}"

    return f"{APP_DISPLAY_NAME} {APP_VERSION} - {APP_CHANNEL_LABEL}"


def get_about_version_text() -> str:
    """Névjegyben megjelenő verzió/csatorna szöveg."""

    if APP_CHANNEL == "stable":
        return f"Verzió: {APP_VERSION}"

    return f"Verzió: {APP_VERSION} ({APP_CHANNEL_LABEL})"


def get_artifact_name() -> str:
    """Build artifact / csomagfájl alapnév."""

    return ARTIFACT_NAME
