import cv2
import pytest

from src.automation import stash_inventory
from src.automation.stash import Stash
from src.perception import update_window_position
from src.settings import BASE_DIR

BASE_PATH = BASE_DIR / "tests/assets/ui"


def test_stash_is_configured_as_stash_menu(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.automation.stash.get_ui_coordinates",
        lambda: type(
            "C",
            (),
            {
                "roi": type(
                    "R", (), {"slots_4x10": (0, 0, 100, 100), "rel_fav_flag": (0, 0, 1, 1), "stash_tab": (0, 0, 1, 1)}
                )()
            },
        )(),
    )
    stash = Stash()
    assert stash.menu_name == "Stash"


@pytest.mark.parametrize("img_res", [(3440, 1440)])
def test_stash_detects_open_chest(img_res) -> None:
    update_window_position(0, 0, *img_res)
    image = cv2.imread(f"{BASE_PATH}/chest_open_1440p_wide.png")

    assert stash_inventory().is_open(image)


def test_stash_header_fallback_detects_localized_header(monkeypatch) -> None:
    image = cv2.imread(f"{BASE_PATH}/chest_open_1440p_wide.png")
    stash = stash_inventory()
    monkeypatch.setattr(stash, "_check_match", lambda _result: False)
    assert stash.is_open(image)


@pytest.mark.parametrize(
    "image_name",
    [
        "char_inv_open_1080p.png",
        "char_inv_open_1440p.png",
        "char_inv_open_1440p_ultra_wide.png",
        "char_inv_open_1440p_wide.png",
        "char_inv_open_2160p.png",
    ],
)
def test_stash_header_fallback_rejects_inventory_at_supported_resolutions(image_name) -> None:
    image = cv2.imread(f"{BASE_PATH}/{image_name}")
    height, width = image.shape[:2]
    update_window_position(0, 0, width, height)
    assert not Stash._looks_like_stash_header(image)
