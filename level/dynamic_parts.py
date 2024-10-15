from dataclasses import dataclass, field
from enum import Enum
from types import NoneType

from binary_reader import BinaryReader

from level.events import KeyEvent, BlockEvent
from level.space import Point3D, Size2D

class DynamicPart:
    def __radd__(self, other):
        """
        In some cases, multiple dynamic parts are located at the same coordinate, e.g. moving platforms that are on the
        same loop, but with different time offsets. With this method dynamic parts can be added together (or to a list
        of dynamic parts), which will result in a list.
        """
        if other is None:
            return self
        elif isinstance(other, list):
            return other + [self]
        else:
            return [other, self]

    def __add__(self, other):
        if isinstance(other, DynamicPart):
            return other.__radd__(self)

@dataclass
class SpawnPoint(DynamicPart):
    pass

@dataclass
class ExitPoint(DynamicPart):
    pass


@dataclass
class Waypoint:
    offset: Point3D = Point3D(0, 0, 0)
    travel_time: int = 0
    pause_time: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)

        waypoint = cls(travel_time=reader.read_uint16(),
                       pause_time=reader.read_uint16())
        waypoint._position = position
        return waypoint

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        writer.write_uint16(self.travel_time)
        writer.write_uint16(self.pause_time)


@dataclass
class MovingPlatform(DynamicPart):
    """
    :cvar loop_start_index: None means the platform will not loop, i.e. stop at its last waypoint. An int denotes the
    waypoint index (starting from 0) to which the platform will return to after the last waypoint
    """
    auto_start: bool = True
    loop_start_index: int | None = None
    full_block: bool = True
    waypoints: list[Waypoint] = field(default_factory=list, repr=False)

    _clones: int = field(default=-1, repr=False, init=False)  # deprecated

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = dict(auto_start=reader.read_uint8() == 2)
        loop_start_index = reader.read_uint8()
        if loop_start_index == 0:
            kwargs['loop_start_index'] = None
        else:
            kwargs['loop_start_index'] = loop_start_index - 1

        clones = reader.read_int16()
        assert clones == -1

        kwargs['full_block'] = bool(reader.read_uint8())

        waypoint_count = reader.read_uint8()
        waypoints = [Waypoint.read(reader) for _ in range(waypoint_count)]
        position = waypoints[0]._position
        for w in waypoints:
            w.offset = w._position - position
        kwargs['waypoints'] = waypoints

        p = cls(**kwargs)
        p._clones = clones
        p._position = position
        return p

    def write(self, writer: BinaryReader):
        writer.write_uint8(2 if self.auto_start else 0)
        writer.write_uint8(0 if self.loop_start_index is None else self.loop_start_index + 1)
        writer.write_int16(self._clones)
        writer.write_uint8(self.full_block)
        writer.write_uint8(len(self.waypoints))
        for w in self.waypoints:
            w._position = self._position + w.offset
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
class Bumper(DynamicPart):
    """
    North is -Y or top-right
    :cvar _id: This is only used internally when writing a level and should not be changed manually
    """
    enabled: bool = True
    north: BumperSide = field(default_factory=BumperSide)
    east: BumperSide = field(default_factory=BumperSide)
    south: BumperSide = field(default_factory=BumperSide)
    west: BumperSide = field(default_factory=BumperSide)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = dict(enabled=bool(reader.read_uint8()))
        position = Point3D.read(reader)
        kwargs['north'] = BumperSide.read(reader)
        kwargs['east'] = BumperSide.read(reader)
        kwargs['south'] = BumperSide.read(reader)
        kwargs['west'] = BumperSide.read(reader)

        bumper = cls(**kwargs)
        bumper._position = position
        return bumper

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.enabled)
        self._position.write(writer)
        self.north.write(writer)
        self.east.write(writer)
        self.south.write(writer)
        self.west.write(writer)


@dataclass
class FallingPlatform(DynamicPart):
    float_time: int = 20

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)
        platform = cls(float_time=reader.read_uint16())
        platform._position = position
        return platform

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        writer.write_uint16(self.float_time)


@dataclass
class Checkpoint(DynamicPart):
    respawn_z: int = 0
    radius: Size2D = field(default_factory=Size2D)

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)
        cp = cls(respawn_z=reader.read_int16(), radius=Size2D.read(reader))
        cp._position = position
        return cp

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        writer.write_int16(self.respawn_z)
        self.radius.write(writer)


@dataclass
class CameraTrigger(DynamicPart):
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
        position = Point3D.read(reader)
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

        trigger = cls(**kwargs)
        trigger._position = position
        return trigger

    def write(self, writer: BinaryReader):
        self._position.write(writer)
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
class Prism(DynamicPart):
    _energy: int = field(default=1, repr=False, init=False)  # deprecated

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)
        energy = reader.read_uint8()
        assert energy == 1

        p = cls()
        p._position = position
        p._energy = energy
        return p

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        writer.write_uint8(self._energy)


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
class Button(DynamicPart):
    """
    :cvar disable_count: How many times the button can be disabled before it can no longer be re-enabled by other buttons (0 means infinite)
    :cvar _id: This is only used internally when writing a level and should not be changed manually
    """
    visible: ButtonVisibility = ButtonVisibility.VISIBLE
    disable_count: int = 0
    mode: ButtonMode = ButtonMode.STAY_DOWN

    _parent_id: int = field(default=-1, repr=False, init=False, compare=False)
    _sequence_in_order: bool = field(default=False, repr=False, init=False, compare=False)
    _children_count: int = field(default=0, repr=False, init=False, compare=False)

    moving_platform: MovingPlatform = None

    events: list[BlockEvent] = field(default_factory=list, repr=False)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = dict(visible=ButtonVisibility(reader.read_uint8()),
                      disable_count=reader.read_uint8(),
                      mode=ButtonMode(reader.read_uint8()))
        parent_id = reader.read_int16()
        sequence_in_order = bool(reader.read_uint8())
        children_count = reader.read_uint8()
        is_moving = bool(reader.read_uint8())

        if is_moving:
            kwargs['moving_platform'] = reader.read_int16()
            position = None
        else:
            position = Point3D.read(reader)

        event_count = reader.read_uint16()
        kwargs['events'] = [reader.read_uint16() for _ in range(event_count)]

        if parent_id >= 0:
            assert kwargs['mode'] == ButtonMode.STAY_DOWN
            assert event_count == 0
            assert children_count == 0

        b = cls(**kwargs)
        b._parent_id = parent_id
        b._sequence_in_order = sequence_in_order
        b._children_count = children_count
        b._position = position
        return b

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.visible.value)
        writer.write_uint8(self.disable_count)
        writer.write_uint8(self.mode.value)
        writer.write_int16(self._parent_id)
        writer.write_uint8(self._sequence_in_order)
        writer.write_uint8(self._children_count)

        if self.moving_platform:
            writer.write_uint8(1)  # is_moving == True
            writer.write_int16(self.moving_platform._id)
        else:
            writer.write_uint8(0)  # is_moving == False
            self._position.write(writer)

        writer.write_uint16(len(self.events))
        for e in self.events:
            writer.write_uint16(e._id)


@dataclass
class ButtonSequence:
    """
    :cvar buttons: A list that has to contain at least 2 ``Button``. All buttons should have
    ``mode = ButtonMode.STAY_DOWN`` and no events set.
    :cvar events: A list of BlockEvents that are triggered when all buttons of the sequence are pressed.
    """
    buttons: list[Button]
    sequence_in_order: bool = False
    events: list[BlockEvent] = field(default_factory=list, repr=False)


@dataclass
class HoloCube(DynamicPart):
    """
    :cvar moving_block_sync: The ID of the moving platform to sync with. The holocube will start
    moving when the specified moving platform reaches its first waypoint. A value of -1 means no sync.
    """
    offset_cube: Point3D
    moving_block_sync: MovingPlatform | NoneType = None
    key_events: list[KeyEvent] = field(default_factory=list)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = {}
        dark_cube = False

        position_trigger = Point3D.read(reader)
        moving_block_sync = reader.read_int16()
        if moving_block_sync == -2:  # dark cube
            dark_cube = True
            kwargs['radius'] = Size2D.read(reader)
            moving_block_sync = reader.read_int16()

        kwargs['moving_block_sync'] = None if moving_block_sync == -1 else moving_block_sync

        key_event_count = reader.read_uint16()
        position_cube = Point3D.read(reader)
        kwargs['offset_cube'] = position_cube - position_trigger
        kwargs['key_events'] = [KeyEvent.read(reader) for _ in range(key_event_count)]

        if dark_cube:
            cube = DarkCube(**kwargs)
        else:
            cube = HoloCube(**kwargs)

        cube._position = position_trigger
        return cube

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        if isinstance(self, DarkCube):
            writer.write_int16(-2)  # dark cube
            self.radius.write(writer)
        writer.write_int16(self.moving_block_sync._id if self.moving_block_sync else -1)
        writer.write_uint16(len(self.key_events))

        position_cube = self._position + self.offset_cube
        position_cube.write(writer)
        for e in self.key_events:
            e.write(writer)

@dataclass
class DarkCube(HoloCube):
    radius: Size2D = field(default_factory=Size2D)


class ResizerDirection(Enum):
    SHRINK = 0
    GROW = 1


@dataclass
class Resizer(DynamicPart):
    direction: ResizerDirection
    visible: bool = True

    @classmethod
    def read(cls, reader: BinaryReader):
        position = Point3D.read(reader)
        resizer = cls(visible=bool(reader.read_uint8()),
                      direction=ResizerDirection(reader.read_uint8()))
        resizer._position = position
        return resizer

    def write(self, writer: BinaryReader):
        self._position.write(writer)
        writer.write_uint8(self.visible)
        writer.write_uint8(self.direction.value)