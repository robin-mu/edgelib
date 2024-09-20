from dataclasses import dataclass, field
from enum import Enum
from types import NoneType

from binary_reader import BinaryReader

from space import Point3D, Size2D
from events import KeyEvent, BlockEvent


@dataclass
class Waypoint:
    position: Point3D
    travel_time: int = 0
    pause_time: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        kwargs['position'] = Point3D.read(reader)
        kwargs['travel_time'] = reader.read_uint16()
        kwargs['pause_time'] = reader.read_uint16()

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        self.position.write(writer)
        writer.write_uint16(self.travel_time)
        writer.write_uint16(self.pause_time)


@dataclass
class MovingPlatform:
    auto_start: bool = True
    loop_start_index: int = 1
    _clones: int = field(default=-1, repr=False)  # deprecated
    full_block: bool = True
    waypoints: list[Waypoint] = field(default_factory=list, repr=False)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        kwargs['auto_start'] = bool(reader.read_uint8())
        kwargs['loop_start_index'] = reader.read_uint8()
        kwargs['_clones'] = reader.read_int16()
        assert kwargs['_clones'] == -1
        kwargs['full_block'] = bool(reader.read_uint8())

        waypoint_count = reader.read_uint8()
        kwargs['waypoints'] = [Waypoint.read(reader) for _ in range(waypoint_count)]

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.auto_start)  # maybe 2 if True
        writer.write_uint8(self.loop_start_index)
        writer.write_int16(self._clones)
        writer.write_uint8(self.full_block)
        writer.write_uint8(len(self.waypoints))
        for w in self.waypoints:
            w.write(writer)


@dataclass
class BumperSide:
    start_delay: int = -1
    pulse_rate: int = -1

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(start_delay=reader.read_int16(), pulse_rate=reader.read_int16())

    def write(self, writer: BinaryReader):
        writer.write_int16(self.start_delay)
        writer.write_int16(self.pulse_rate)


@dataclass
class Bumper:
    """
    North is -Y or top-right
    """
    position: Point3D
    enabled: bool = True
    north: BumperSide = field(default_factory=BumperSide)
    east: BumperSide = field(default_factory=BumperSide)
    south: BumperSide = field(default_factory=BumperSide)
    west: BumperSide = field(default_factory=BumperSide)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        kwargs['enabled'] = bool(reader.read_uint8())
        kwargs['position'] = Point3D.read(reader)
        kwargs['north'] = BumperSide.read(reader)
        kwargs['east'] = BumperSide.read(reader)
        kwargs['south'] = BumperSide.read(reader)
        kwargs['west'] = BumperSide.read(reader)

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.enabled)
        self.position.write(writer)
        self.north.write(writer)
        self.east.write(writer)
        self.south.write(writer)
        self.west.write(writer)


@dataclass
class FallingPlatform:
    position: Point3D
    float_time: int = 20

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(position=Point3D.read(reader), float_time=reader.read_uint16())

    def write(self, writer: BinaryReader):
        self.position.write(writer)
        writer.write_uint16(self.float_time)


@dataclass
class Checkpoint:
    position: Point3D
    respawn_z: int = 0
    radius: Size2D = field(default_factory=Size2D)

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(position=Point3D.read(reader), respawn_z=reader.read_int16(), radius=Size2D.read(reader))

    def write(self, writer: BinaryReader):
        self.position.write(writer)
        writer.write_int16(self.respawn_z)
        self.radius.write(writer)


@dataclass
class CameraTrigger:
    position: Point3D
    zoom: int = -1
    radius: Size2D = field(default_factory=Size2D)
    reset: bool = None  # seems to be only True when is_angle is False
    start_delay: int = 0
    duration: int = 0
    angle_or_fov: int = 22
    single_use: bool = False
    is_angle: bool = None

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        kwargs['position'] = Point3D.read(reader)
        kwargs['zoom'] = reader.read_int16()
        assert -1 <= kwargs['zoom'] <= 6
        kwargs['radius'] = Size2D.read(reader)
        if kwargs['zoom'] == -1:
            kwargs['reset'] = bool(reader.read_uint8())
            kwargs['start_delay'] = reader.read_uint16()
            kwargs['duration'] = reader.read_uint16()
            kwargs['angle_or_fov'] = reader.read_int16()
            kwargs['single_use'] = bool(reader.read_uint8())
            kwargs['is_angle'] = bool(reader.read_uint8())

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        self.position.write(writer)
        writer.write_int16(self.zoom)
        self.radius.write(writer)
        if self.zoom != -1:
            return
        writer.write_uint8(self.reset)
        writer.write_uint16(self.start_delay)
        writer.write_uint16(self.duration)
        writer.write_int16(self.angle_or_fov)
        writer.write_uint8(self.single_use)
        writer.write_uint8(self.is_angle)


@dataclass
class Prism:
    position: Point3D
    energy: int = field(default=1, repr=False)  # deprecated

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)
        energy = reader.read_uint8()
        assert energy == 1

        return cls(position=position, energy=energy)

    def write(self, writer: BinaryReader):
        self.position.write(writer)
        writer.write_uint8(self.energy)


class ButtonVisibility(Enum):
    INVISIBLE = 0
    VISIBLE = 1
    SEMI_TRANSPARENT = 2


class ButtonMode(Enum):
    """
    :cvar TOGGLE: When the button is released, it pops back up and all affected moving platforms move back to their original position
    :cvar STAY_UP: The button can be pressed multiple times
    :cvar STAY_DOWN: The button can only be pressed once, but can be re-enabled by other buttons
    """
    TOGGLE = 0
    STAY_UP = 1
    STAY_DOWN = 2


@dataclass
class Button:
    """
    :cvar disable_count: How many times the button can be disabled before it can no longer be re-enabled by other buttons (0 means infinite)
    """
    visible: ButtonVisibility = ButtonVisibility.VISIBLE
    disable_count: int = 0
    mode: ButtonMode = ButtonMode.STAY_DOWN

    _parent_id: int = -1
    _sequence_in_order: bool = False
    _children_count: int = 0

    _is_moving: bool = False
    moving_platform: MovingPlatform = None
    position: Point3D = None

    events: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        kwargs['visible'] = ButtonVisibility(reader.read_uint8())
        kwargs['disable_count'] = reader.read_uint8()
        kwargs['mode'] = ButtonMode(reader.read_uint8())
        kwargs['_parent_id'] = reader.read_int16()
        kwargs['_sequence_in_order'] = bool(reader.read_uint8())
        kwargs['_children_count'] = reader.read_uint8()
        kwargs['_is_moving'] = bool(reader.read_uint8())

        if kwargs['_is_moving']:
            kwargs['moving_platform'] = reader.read_int16()
        else:
            kwargs['position'] = Point3D.read(reader)

        event_count = reader.read_uint16()
        kwargs['events'] = [reader.read_uint16() for _ in range(event_count)]

        if kwargs['_parent_id'] > 0:
            assert kwargs['mode'] == ButtonMode.STAY_DOWN
            assert event_count == 0
            assert kwargs['_children_count'] == 0

        return cls(**kwargs)


@dataclass
class ButtonSequence:
    """
    :cvar buttons: A list that has to contain at least 2 ``Button``. All buttons should have
    ``mode = ButtonMode.STAY_DOWN`` and no events set.
    :cvar events: A list of BlockEvents that are triggered when all buttons of the sequence are pressed.
    """
    buttons: list[Button]
    sequence_in_order: bool = False
    events: list[BlockEvent] = field(default_factory=list)


@dataclass
class HoloCube:
    """
    :cvar moving_block_sync: The ID of the moving platform to sync with. The holocube will start
    moving when the specified moving platform reaches its first waypoint. A value of -1 means no sync.
    """
    position_trigger: Point3D
    position_cube: Point3D
    moving_block_sync: MovingPlatform | NoneType = None
    key_events: list[KeyEvent] = field(default_factory=list)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        dark_cube = False

        kwargs['position_trigger'] = Point3D.read(reader)
        moving_block_sync = reader.read_int16()
        if moving_block_sync == -2:  # dark cube
            dark_cube = True
            kwargs['radius'] = Size2D.read(reader)
            moving_block_sync = reader.read_int16()

        kwargs['moving_block_sync'] = None if moving_block_sync == -1 else moving_block_sync

        key_event_count = reader.read_uint16()
        kwargs['position_cube'] = Point3D.read(reader)
        kwargs['key_events'] = [KeyEvent.read(reader) for _ in range(key_event_count)]

        if dark_cube:
            return DarkCube(**kwargs)
        else:
            return HoloCube(**kwargs)


@dataclass
class DarkCube(HoloCube):
    radius: Size2D = field(default_factory=Size2D)


class ResizerDirection(Enum):
    SHRINK = 0
    GROW = 1


@dataclass
class Resizer:
    position: Point3D
    direction: ResizerDirection
    visible: bool = True

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(position=Point3D.read(reader),
                   visible=bool(reader.read_uint8()),
                   direction=ResizerDirection(reader.read_uint8()))