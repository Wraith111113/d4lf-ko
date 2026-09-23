import logging

from src.perception.listener import Publisher, filter_data, find_item_start, fix_data, is_item_boundary


def test_listener_identifies_item_start_and_cleans_tts_markers() -> None:
    assert find_item_start(["Noise", "RARE SWORD", "Right mouse button"]) == 1
    assert find_item_start(["소음", "피바람", "선조 전설 양손 낫", "마우스 오른쪽 버튼"]) == 1
    assert (
        find_item_start([
            "장착 중",
            "무덤방랑자의 손",
            "선조 고유 부적",
            "아이템 위력 900",
            "고유 능력 설명",
            "요구 레벨: 70강령술사. 전용. 고유 장착. 증오의 군주 아이템",
            "판매가: 8,879,022 금화",
            "마우스 오른쪽 버튼",
        ])
        == 1
    )
    assert is_item_boundary("Right mouse button")
    assert is_item_boundary("마우스 오른쪽 버튼")
    assert filter_data("Champions who earn the favor of the season")
    assert fix_data("[MARKED AS JUNK]. [FAVORITED ITEM]. Name") == "Name"
    assert fix_data("[즐겨찾는 아이템]. 으스러뜨리는 썩은 제웅") == "으스러뜨리는 썩은 제웅"
    assert fix_data("[즐겨찾는 아이템] 범람의 거대심장 가락지") == "범람의 거대심장 가락지"
    assert fix_data("[폐품으로 표시]. 지옥의 사령관 목띠") == "지옥의 사령관 목띠"


def test_listener_item_publication_logs_raw_tts_payload(caplog) -> None:
    payload = ["RARE SWORD", "Right mouse button"]

    with caplog.at_level(logging.DEBUG, logger="src.perception.listener"):
        Publisher().publish_item(payload)

    assert f"Raw TTS payload: {payload}" in caplog.messages
