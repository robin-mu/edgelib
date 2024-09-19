from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from binary_reader import BinaryReader

# avoid cyclic imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dynamic_parts import MovingPlatform, Bumper, Button

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


class BlockEvent:
    @classmethod
    def read(cls, reader: BinaryReader):
        type = BlockEventType(reader.read_uint8())
        id = reader.read_int16()
        payload = reader.read_uint16()

        if type == BlockEventType.AFFECT_MOVING_PLATFORM:
            return AffectMovingPlatformEvent(moving_platform=id, traverse_waypoints=payload)
        elif type == BlockEventType.AFFECT_BUMPER:
            return AffectBumperEvent(bumper=id, event=BumperEventType(payload))
        elif type == BlockEventType.TRIGGER_ACHIEVEMENT:
            return TriggerAchievementEvent(achievement_id=id, metadata=payload)
        elif type == BlockEventType.AFFECT_BUTTON:
            return AffectButtonEvent(button=id, start_behavior=ButtonStartType(payload))

@dataclass
class AffectMovingPlatformEvent(BlockEvent):
    moving_platform: MovingPlatform
    traverse_waypoints: int


@dataclass
class AffectBumperEvent(BlockEvent):
    bumper: Bumper
    event: BumperEventType


@dataclass
class TriggerAchievementEvent(BlockEvent):
    achievement_id: int
    metadata: int


@dataclass
class AffectButtonEvent(BlockEvent):
    button: Button
    start_behavior: ButtonStartType


class Direction(Enum):
    """
    North is -Y or top-right
    """
    WEST = 0
    EAST = 1
    NORTH = 2
    SOUTH = 3


class KeyEventType(Enum):
    DOWN = 0
    UP = 1


@dataclass
class KeyEvent:
    """
    :cvar time_offset: The number of ticks from triggering the othercube to the key event being triggered
    """
    time_offset: int
    direction: Direction
    event_type: KeyEventType

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(time_offset=reader.read_uint16(),
                   direction=Direction(reader.read_uint8()),
                   event_type=KeyEventType(reader.read_uint8()))