from dataclasses import dataclass, field
from enum import Enum

from binary_reader import BinaryReader


class BlockEventType(Enum):
    AFFECT_MOVING_PLATFORM = 0
    AFFECT_BUMPER = 1
    TRIGGER_ACHIEVEMENT = 2
    AFFECT_BUTTON = 3


class BumperEventType(Enum):
    """
    Whether the targeted bumper should stop (STOP / 0) or start (START / 1) when the button triggering this event is pressed.
    """
    STOP = 0
    START = 1


class ButtonStartType(Enum):
    """
    Whether the button targeted by this event should be pressed (DOWN / 0) or not pressed (UP / 1) when starting the level.
    """
    DOWN = 0
    UP = 1


@dataclass
class BlockEvent:
    id: int
    _payload: int = field(init=False, repr=False)

    @classmethod
    def read(cls, reader: BinaryReader):
        type = BlockEventType(reader.read_uint8())
        id = reader.read_int16()
        payload = reader.read_uint16()

        if type == BlockEventType.AFFECT_MOVING_PLATFORM:
            return AffectMovingPlatformEvent(id, traverse_waypoints=payload)
        elif type == BlockEventType.AFFECT_BUMPER:
            return AffectBumperEvent(id, event=BumperEventType(payload))
        elif type == BlockEventType.TRIGGER_ACHIEVEMENT:
            return TriggerAchievementEvent(id, metadata=payload)
        elif type == BlockEventType.AFFECT_BUTTON:
            return AffectButtonEvent(id, start_behavior=ButtonStartType(payload))


@dataclass
class AffectMovingPlatformEvent(BlockEvent):
    traverse_waypoints: int

    @property
    def traverse_waypoints(self):
        return self._payload

    @traverse_waypoints.setter
    def traverse_waypoints(self, value):
        self._payload = value


@dataclass
class AffectBumperEvent(BlockEvent):
    event: BumperEventType

    @property
    def event(self):
        return self._payload

    @event.setter
    def event(self, value):
        self._payload = value


@dataclass
class TriggerAchievementEvent(BlockEvent):
    metadata: int

    @property
    def metadata(self):
        return self._payload

    @metadata.setter
    def metadata(self, value):
        self._payload = value


@dataclass
class AffectButtonEvent(BlockEvent):
    start_behavior: ButtonStartType

    @property
    def start_behavior(self):
        return self._payload

    @start_behavior.setter
    def start_behavior(self, value):
        self._payload = value
