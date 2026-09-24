from src.app.dashboard.equipment import _label
from src.localization import tr


def test_equipment_target_labels_use_dashboard_localization() -> None:
    assert _label("weapon") == tr("Weapon")
