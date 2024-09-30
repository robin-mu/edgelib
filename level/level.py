import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from binary_reader import BinaryReader

from level.dynamic_parts import MovingPlatform, Bumper, FallingPlatform, Checkpoint, CameraTrigger, Prism, Button, \
    HoloCube, Resizer, ButtonSequence, ButtonMode
from level.events import BlockEvent, AffectMovingPlatformEvent, AffectBumperEvent, AffectButtonEvent
from level.space import Size3D, Point3D, BitCube, StaticMap
from model.model import ESOModel, AssetHash, TypeFlag


class Theme(Enum):
    WHITE = 0
    LIGHT_GRAY = 1
    DARK_GRAY = 2
    BLACK = 3


class MusicJava(Enum):
    MENUS = 0
    BRAINTONIK = 1
    CUBE_DANCE = 2
    ESSAI_2 = 3
    ESSAI_01 = 4
    TEST = 5
    MYSTERYCUBE = 6
    EDGE = 7
    JUNGLE = 8
    RETARD_TONIC = 9
    OLDSCHOOL_SIMON = 10
    PLANANT = 11


class Music(Enum):
    TITLE = 0
    ETERNITY = 1
    QUIET = 2
    PAD = 3
    JINGLE = 4
    TEC = 5
    KAKKOI = 6
    DARK = 7
    SQUADRON = 8
    EIGHT_BITS = 9
    PIXEL = 10
    JUPITER = 11
    SHAME = 12
    DEBRIEF = 13
    SPACE = 14
    VOYAGE_GEOMETRIQUE = 15
    MZONE = 16
    R2 = 17
    MYSTERY_CUBE = 18
    DUTY = 19
    PERFECT_CELL = 20
    FUN = 21
    LOL = 22
    LOSTWAY = 23
    WALL_STREET = 24


@dataclass
class Level:
    id: int
    spawn_point: Point3D
    exit_point: Point3D
    name: str = ''
    s_plus_time: int = 1
    s_time: int = 2
    a_time: int = 3
    b_time: int = 4
    c_time: int = 5
    theme: Theme = Theme.WHITE
    model_theme: Theme = theme
    music_java: MusicJava = MusicJava.MENUS
    music: Music = Music.KAKKOI
    zoom: int = -1
    angle_or_fov: int = 0
    is_angle: bool = False

    _legacy_minimap: BitCube = field(default=None, repr=False, init=False)

    static_map: StaticMap = None

    moving_platforms: list[MovingPlatform] = field(default_factory=list, repr=False)
    bumpers: list[Bumper] = field(default_factory=list, repr=False)
    falling_platforms: list[FallingPlatform] = field(default_factory=list, repr=False)
    checkpoints: list[Checkpoint] = field(default_factory=list, repr=False)
    camera_triggers: list[CameraTrigger] = field(default_factory=list, repr=False)
    prisms: list[Prism] = field(default_factory=list, repr=False)
    buttons: list[Button] = field(default_factory=list, repr=False)
    button_sequences: list[ButtonSequence] = field(default_factory=list, repr=False)
    othercubes: list[HoloCube] = field(default_factory=list, repr=False)
    resizers: list[Resizer] = field(default_factory=list, repr=False)

    @property
    def size(self):
        return self.static_map.size

    @classmethod
    def read(cls, path):
        kwargs = {}
        with open(path, 'rb') as f:
            reader = BinaryReader(bytearray(f.read()))

        kwargs['id'] = reader.read_int32()

        name_len = reader.read_int32()
        kwargs['name'] = reader.read_str(name_len, encoding='utf-8')

        kwargs['s_plus_time'] = reader.read_uint16()
        kwargs['s_time'] = reader.read_uint16()
        kwargs['a_time'] = reader.read_uint16()
        kwargs['b_time'] = reader.read_uint16()
        kwargs['c_time'] = reader.read_uint16()
        assert kwargs['s_plus_time'] < kwargs['s_time'] < kwargs['a_time'] < kwargs['b_time'] < kwargs['c_time']

        prisms_count = reader.read_uint16()

        size = Size3D.read(reader)

        unknown_short_1 = reader.read_uint16()  # size.x + size.y
        assert unknown_short_1 == size.x + size.y
        unknown_short_2 = reader.read_uint16()  # size.x + size.y + 2 * size.z
        assert unknown_short_2 == unknown_short_1 + 2 * size.z

        legacy_minimap_width = reader.read_uint16()  # (size.x + size.y + 9) // 10
        assert legacy_minimap_width == (unknown_short_1 + 9) // 10
        legacy_minimap_length = reader.read_uint16()  # (size.x + size.y + 2 * size.z + 9) // 10
        assert legacy_minimap_length == (unknown_short_2 + 9) // 10

        unknown_byte_1 = reader.read_uint8()  # 10
        assert unknown_byte_1 == 10
        unknown_short_5 = reader.read_uint16()  # size.y - 1
        assert unknown_short_5 == size.y - 1
        unknown_short_6 = reader.read_uint16()  # 0
        assert unknown_short_6 == 0

        legacy_minimap = BitCube.read(reader, Size3D(x=legacy_minimap_width, y=legacy_minimap_length, z=1))

        collision_map = BitCube.read(reader, size)
        kwargs['static_map'] = collision_map.to_static_map()

        kwargs['spawn_point'] = Point3D.read(reader)
        assert kwargs['spawn_point'].z >= -20

        kwargs['zoom'] = reader.read_int16()
        if kwargs['zoom'] < 0:
            kwargs['angle_or_fov'] = reader.read_int16()
            kwargs['is_angle'] = bool(reader.read_uint8())

        kwargs['exit_point'] = Point3D.read(reader)

        moving_platform_count = reader.read_uint16()
        kwargs['moving_platforms'] = [MovingPlatform.read(reader) for _ in range(moving_platform_count)]

        bumper_count = reader.read_uint16()
        kwargs['bumpers'] = [Bumper.read(reader) for _ in range(bumper_count)]

        falling_platform_count = reader.read_uint16()
        kwargs['falling_platforms'] = [FallingPlatform.read(reader) for _ in range(falling_platform_count)]

        checkpoint_count = reader.read_uint16()
        kwargs['checkpoints'] = [Checkpoint.read(reader) for _ in range(checkpoint_count)]

        camera_trigger_count = reader.read_uint16()
        kwargs['camera_triggers'] = [CameraTrigger.read(reader) for _ in range(camera_trigger_count)]

        prism_count = reader.read_uint16()
        assert prism_count == prisms_count
        kwargs['prisms'] = [Prism.read(reader) for _ in range(prism_count)]

        fan_count = reader.read_uint16()  # deprecated
        assert fan_count == 0

        block_event_count = reader.read_uint16()
        block_events = [BlockEvent.read(reader) for _ in range(block_event_count)]

        button_count = reader.read_uint16()
        kwargs['buttons'] = [Button.read(reader) for _ in range(button_count)]

        # resolve references in block events
        for event in block_events:
            if isinstance(event, AffectMovingPlatformEvent):
                event.moving_platform = kwargs['moving_platforms'][event.moving_platform]
            elif isinstance(event, AffectBumperEvent):
                event.bumper = kwargs['bumpers'][event.bumper]
            elif isinstance(event, AffectButtonEvent):
                event.button = kwargs['buttons'][event.button]

        # resolve references in buttons
        for button in kwargs['buttons']:
            button.events = [block_events[i] for i in button.events]
            if button.moving_platform:
                button.moving_platform = kwargs['moving_platforms'][button.moving_platform]

        # extract button sequences
        kwargs['button_sequences'] = []
        for id, button in enumerate(kwargs['buttons']):
            if button._children_count > 0:
                children = [b for b in kwargs['buttons'] if b._parent_id == id]
                assert button._children_count == len(children)
                events = button.events
                button.events = []
                kwargs['button_sequences'].append(ButtonSequence(buttons=[button] + children,
                                                                 sequence_in_order=button._sequence_in_order,
                                                                 events=events))

        # remove elements which are part of a button sequence from buttons
        kwargs['buttons'] = [b for b in kwargs['buttons'] if b._children_count == 0 and b._parent_id == -1]

        othercube_count = reader.read_uint16()
        kwargs['othercubes'] = [HoloCube.read(reader) for _ in range(othercube_count)]

        # resolve references in other cubes
        for cube in kwargs['othercubes']:
            if cube.moving_block_sync:
                cube.moving_block_sync = kwargs['moving_platforms'][cube.moving_block_sync]

        resizer_count = reader.read_uint16()
        kwargs['resizers'] = [Resizer.read(reader) for _ in range(resizer_count)]

        mini_block_count = reader.read_uint16()  # deprecated
        assert mini_block_count == 0

        kwargs['theme'] = Theme(reader.read_uint8())
        kwargs['music_java'] = MusicJava(reader.read_uint8())
        kwargs['music'] = Music(reader.read_uint8())

        level = cls(**kwargs)
        level._legacy_minimap = legacy_minimap
        return level

    def write(self, path):
        writer = BinaryReader()
        writer.write_int32(self.id)
        writer.write_int32(len(self.name))
        writer.write_str(self.name)

        writer.write_uint16(self.s_plus_time)
        writer.write_uint16(self.s_time)
        writer.write_uint16(self.a_time)
        writer.write_uint16(self.b_time)
        writer.write_uint16(self.c_time)

        writer.write_uint16(len(self.prisms))

        size = self.static_map.size
        size.write(writer)

        unknown_short_1 = size.x + size.y
        unknown_short_2 = unknown_short_1 + 2 * size.z
        legacy_minimap_width = (unknown_short_1 + 9) // 10
        legacy_minimap_length = (unknown_short_2 + 9) // 10
        unknown_byte_1 = 10
        unknown_short_5 = size.y - 1
        unknown_short_6 = 0

        writer.write_uint16(unknown_short_1)
        writer.write_uint16(unknown_short_2)
        writer.write_uint16(legacy_minimap_width)
        writer.write_uint16(legacy_minimap_length)
        writer.write_uint8(unknown_byte_1)
        writer.write_uint16(unknown_short_5)
        writer.write_uint16(unknown_short_6)

        legacy_minimap_size = Size3D(legacy_minimap_width, legacy_minimap_length, 1)
        if not self._legacy_minimap:
            self._legacy_minimap = BitCube.zeros(legacy_minimap_size)
        assert self._legacy_minimap.data.shape == legacy_minimap_size
        self._legacy_minimap.write(writer)

        collision_map = self.static_map.to_collision_map()
        assert collision_map.data.shape == size
        collision_map.write(writer)
        self.spawn_point.write(writer)

        writer.write_int16(self.zoom)
        if self.zoom < 0:
            writer.write_int16(self.angle_or_fov)
            writer.write_uint8(self.is_angle)

        self.exit_point.write(writer)

        writer.write_uint16(len(self.moving_platforms))
        for e in self.moving_platforms:
            e.write(writer)

        writer.write_uint16(len(self.bumpers))
        for e in self.bumpers:
            e.write(writer)

        writer.write_uint16(len(self.falling_platforms))
        for e in self.falling_platforms:
            e.write(writer)

        writer.write_uint16(len(self.checkpoints))
        for e in self.checkpoints:
            e.write(writer)

        writer.write_uint16(len(self.camera_triggers))
        for e in self.camera_triggers:
            e.write(writer)

        writer.write_uint16(len(self.prisms))
        for e in self.prisms:
            e.write(writer)

        writer.write_uint16(0)  # fans_count

        # turn button sequences into normal buttons
        for seq in self.button_sequences:
            parent_id = len(self.buttons)
            parent = seq.buttons[0]
            parent._parent_id = -1
            parent._sequence_in_order = seq.sequence_in_order
            parent._children_count = len(seq.buttons) - 1
            if parent.events:
                print('overwriting events')
            parent.events = seq.events
            assert parent.mode == ButtonMode.STAY_DOWN

            self.buttons.append(parent)
            for child in seq.buttons[1:]:
                assert child.events == []
                assert child.mode == ButtonMode.STAY_DOWN
                assert child._children_count == 0

                child._sequence_in_order = seq.sequence_in_order
                child._parent_id = parent_id
                self.buttons.append(child)

        # assign indices to everything that can be referenced
        for i, p in enumerate(self.moving_platforms):
            assert p._id is None
            p._id = i

        for i, b in enumerate(self.bumpers):
            assert b._id is None
            b._id = i

        event_id = 0
        block_events = []
        for i, b in enumerate(self.buttons):
            assert b._id is None
            b._id = i

            for e in b.events:
                if e._id is not None:
                    print('duplicate blockevent')
                    continue

                e._id = event_id
                block_events.append(e)
                event_id += 1

        writer.write_uint16(len(block_events))
        for e in block_events:
            e.write(writer)

        writer.write_uint16(len(self.buttons))
        for e in self.buttons:
            e.write(writer)

        writer.write_uint16(len(self.othercubes))
        for e in self.othercubes:
            e.write(writer)

        writer.write_uint16(len(self.resizers))
        for e in self.resizers:
            e.write(writer)

        writer.write_uint16(0)  # mini_blocks_count
        writer.write_uint8(self.theme.value)
        writer.write_uint8(self.music_java.value)
        writer.write_uint8(self.music.value)

        with open(path, 'wb') as f:
            f.write(writer.buffer())


    def generate_model(self):
        models_namespace = 0x050DB82A
        materials = [0x2F2CC05D, 0x55ECE3AD, 0xC273F284, 0x0D11C513]
        child_models = [0x67228D77, 0x1DE2AE87, 0x8A7DBFAE, 0x451F8839]

        themes = list(range(4))
        themes = themes[self.model_theme.value:] + themes[:self.model_theme.value]
        # themes now is the list [0, 1, 2, 3] but rotated so that level.model_theme is the first value

        models = [None, None, None, None]  # One model for each theme

        for (x, y, z), block in self.static_map.to_model_map().items():
            if block.theme is None:
                theme = self.model_theme.value
            elif block.theme < 0:
                theme = themes[-block.theme]
            else:
                theme = block.theme

            if models[theme] is None:
                models[theme] = ESOModel(asset_material=AssetHash(name=materials[theme], namespace=models_namespace),
                                         type_flags=TypeFlag.NORMALS | TypeFlag.TEX_COORDS)

            model = models[theme]


if __name__ == '__main__':
    np.set_printoptions(threshold=np.inf)
    t = time.time()
    l = Level.read('level300.bin')

    l.generate_model()


    # l.write('test.bin')
    # l = Level.read('test.bin')
    #
    # np.set_printoptions(threshold=np.inf)
    # map = l.static_map
    #
    # map.resize(30, 30, 5)
    #
    # print(map[0])
    #
    # b = StaticMap(size=Size3D(3, 4, 5))
    # print(b)
    # print(b.size)
    # b[:, 2] = Block.full()
    #
    # b[0] = Block.half()
    # print(b)
    #
    # print(time.time() - t)