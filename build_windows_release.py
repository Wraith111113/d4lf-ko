import os
import shutil
from pathlib import Path

from src import __ko_build__, __version__

ROOT = Path(__file__).resolve().parent
RELEASE_NAME = f"D4LF-v{__version__}-{__ko_build__}-Windows"
OUTPUT_ROOT = ROOT / "dist-win-portable"
PACKAGE_DIR = OUTPUT_ROOT / RELEASE_NAME
ZIP_PATH = OUTPUT_ROOT / f"{RELEASE_NAME}.zip"
PYTHON_HOME = Path(os.environ["APPDATA"]) / "uv" / "python" / "cpython-3.14-windows-x86_64-none"
SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"

IGNORE_RUNTIME = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "PyInstaller",
    "pyinstaller*",
    "pytest",
    "_pytest",
    "ruff",
    "ty",
    "lxml-stubs",
)


def copytree(src: Path, dst: Path, ignore: shutil.IgnorePattern | None = None) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def build_release() -> Path:
    if os.name != "nt":
        message = "The standalone Windows release must be built on Windows."
        raise RuntimeError(message)
    if PACKAGE_DIR.exists() or ZIP_PATH.exists():
        message = f"Release output already exists: {PACKAGE_DIR} or {ZIP_PATH}"
        raise FileExistsError(message)
    if not PYTHON_HOME.exists():
        message = f"Python runtime was not found: {PYTHON_HOME}"
        raise FileNotFoundError(message)
    if not SITE_PACKAGES.exists():
        message = f"Project environment was not found: {SITE_PACKAGES}"
        raise FileNotFoundError(message)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PACKAGE_DIR.mkdir()

    copytree(PYTHON_HOME, PACKAGE_DIR / "runtime", ignore=IGNORE_RUNTIME)
    copytree(SITE_PACKAGES, PACKAGE_DIR / "runtime" / "Lib" / "site-packages", ignore=IGNORE_RUNTIME)
    copytree(ROOT / "src", PACKAGE_DIR / "src", ignore=IGNORE_RUNTIME)
    copytree(ROOT / "assets", PACKAGE_DIR / "assets")
    copytree(ROOT / "docs", PACKAGE_DIR / "docs")
    copytree(ROOT / "tts", PACKAGE_DIR / "tts", ignore=shutil.ignore_patterns("*.cpp", "*.h", "*.vcxproj"))

    shutil.copy2(ROOT / "README-koKR.md", PACKAGE_DIR)
    shutil.copy2(ROOT / "LICENSE", PACKAGE_DIR)
    shutil.copy2(ROOT / "D4LF-koKR-portable.bat", PACKAGE_DIR)
    shutil.make_archive(str(ZIP_PATH.with_suffix("")), "zip", OUTPUT_ROOT, RELEASE_NAME)
    return ZIP_PATH


if __name__ == "__main__":
    print(f"Building {RELEASE_NAME}")
    print(f"Created: {build_release()}")
