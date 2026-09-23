import enum
import logging
import queue
import re
import threading
from typing import TYPE_CHECKING, ClassVar, Self

from src.game_data import GameCatalog

if TYPE_CHECKING:
    from collections.abc import Callable

from src.perception.backend.core import load_backend

CONNECTED = False
LAST_ITEM: list[str] = []
_DATA_QUEUE = queue.Queue(maxsize=100)
_backend = load_backend()
LOGGER = logging.getLogger(__name__)


class ItemIdentifiers(enum.Enum):
    COMPASS = "Compass"
    ESCALATION_SIGIL = "Escalation Sigil"
    NIGHTMARE_SIGIL = "Nightmare Sigil"
    TRIBUTE = "TRIBUTE OF"
    WHISPERING_KEY = "WHISPERING KEY"


_KOREAN_RARITIES = ("일반", "마법", "희귀", "전설", "고유", "신화", "세트")
_ITEM_BOUNDARY_MARKERS = (
    "mouse button",
    "action button",
    "마우스 버튼",
    "마우스 왼쪽 버튼",
    "마우스 오른쪽 버튼",
    "동작 버튼",
    "행동 버튼",
)


def _is_korean_item_descriptor(text: str) -> bool:
    """Return whether text looks like the short Korean rarity/type header.

    Rarity words also occur later in tooltip sentences such as
    "요구 레벨: 70. 고유 장착".  Treating those sentences as headers drops the
    item name and all affixes from the payload.
    """
    if not re.search(r"[가-힣]", text) or any(marker in text for marker in (":", ".")):
        return False
    tokens = text.split()
    if tokens and tokens[0] == "선조":
        tokens = tokens[1:]
    rarity_indexes = [index for index, token in enumerate(tokens[:2]) if token in _KOREAN_RARITIES]
    if not rarity_indexes:
        return False
    item_type_text = " ".join(tokens[max(rarity_indexes) + 1 :])
    return GameCatalog().item_type_from_text(item_type_text) is not None


def find_item_start(data: list[str]) -> int | None:
    ignored_words = ["COMPASS AFFIXES", "DUNGEON AFFIXES", "AFFIXES", "SELECT ALL"]
    for index, item in reversed(list(enumerate(data))):
        if any(ignored in item for ignored in ignored_words):
            continue
        if any(item.startswith(identifier.value) for identifier in ItemIdentifiers):
            return index
        if len(re.sub(r"[^A-Za-z]", "", item)) >= 3 and item.isupper():
            return index
        if index > 0 and _is_korean_item_descriptor(item):
            return index - 1
    return None


def is_item_boundary(data: str) -> bool:
    normalized = data.casefold()
    return any(marker in normalized for marker in _ITEM_BOUNDARY_MARKERS)


def filter_data(data: str) -> bool:
    return "Champions who earn the favor of" in data


def fix_data(data: str) -> str:
    for token in [
        "&apos;",
        "&quot;",
        "[FAVORITED ITEM]. ",
        "[즐겨찾는 아이템]. ",
        "[즐겨찾는 아이템] ",
        "ￂﾠ",
        "(Spiritborn Only)",
        "[MARKED AS JUNK]. ",
        "[쓰레기로 표시된 아이템]. ",
        "[폐품으로 표시]. ",
        "[폐품으로 표시] ",
    ]:
        data = data.replace(token, "")
    return data.strip()


class Publisher:
    _instance: ClassVar[Self | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()
    _item_subscribers: set[Callable[..., None]]
    _info_subscribers: set[Callable[..., None]]
    _subscriber_lock: threading.Lock

    def __new__(cls) -> Self:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._item_subscribers = set()
                cls._instance._info_subscribers = set()
                cls._instance._subscriber_lock = threading.Lock()
        return cls._instance

    def find_item(self) -> None:
        local_cache: list[str] = []
        while True:
            data = fix_data(_DATA_QUEUE.get())
            LOGGER.debug("Raw TTS line: %s", data)
            if "gold" in data.lower() or "experience" in data.lower():
                self.publish_info(data)
            local_cache.append(data)
            if filter_data(data) or not is_item_boundary(data):
                continue
            start = find_item_start(local_cache)
            if start is None:
                continue
            global LAST_ITEM
            LAST_ITEM = local_cache[start:]
            self.publish_item(LAST_ITEM)
            local_cache = []

    def publish_item(self, data: list[str]) -> None:
        LOGGER.debug("Raw TTS payload: %s", data)
        with self._subscriber_lock:
            for subscriber in self._item_subscribers:
                subscriber(data)

    def subscribe_item(self, subscriber: Callable[[list[str]], None]) -> None:
        with self._subscriber_lock:
            self._item_subscribers.add(subscriber)

    def unsubscribe_item(self, subscriber: Callable[[list[str]], None]) -> None:
        with self._subscriber_lock:
            self._item_subscribers.discard(subscriber)

    def publish_info(self, data: str) -> None:
        with self._subscriber_lock:
            for subscriber in self._info_subscribers:
                subscriber(data)

    def subscribe_info(self, subscriber: Callable[[str], None]) -> None:
        with self._subscriber_lock:
            self._info_subscribers.add(subscriber)

    def unsubscribe_info(self, subscriber: Callable[[str], None]) -> None:
        with self._subscriber_lock:
            self._info_subscribers.discard(subscriber)


def set_connected(value: bool) -> None:
    global CONNECTED
    CONNECTED = value


def create_pipe() -> int:
    return _backend.create_pipe(LOGGER)


def read_pipe() -> None:
    _backend.read_pipe(create_pipe, _DATA_QUEUE, LOGGER, set_connected)


def start_connection() -> None:
    _backend.start_connection(Publisher().find_item, read_pipe, LOGGER)
