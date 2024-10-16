import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from binary_reader import BinaryReader

from level.crc_gen import generate_crc
from level.dynamic_parts import MovingPlatform, Bumper, FallingPlatform, Checkpoint, CameraTrigger, Prism, Button, \
    HoloCube, Resizer, ButtonSequence, ButtonMode
from level.events import BlockEvent, AffectMovingPlatformEvent, AffectBumperEvent, AffectButtonEvent
from level.space import Size3D, Point3D, BitCube, StaticMap, DynamicMap, Block
from model.model import ESOModel, AssetHash, TypeFlag, ESO, AssetHeader, EngineVersion, ESOHeader
from model.space import Vec3D, Vec2D


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
    """
    Providing a size is not necessary, as the level map will expand automatically as you add elements, and the level
    size will be calculated when saving the level.
    """

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
    model_theme: Theme = None
    music_java: MusicJava = MusicJava.MENUS
    music: Music = Music.KAKKOI
    zoom: int = -1
    angle_or_fov: int = 0
    is_angle: bool = False

    _legacy_minimap: BitCube = field(default=None, repr=False, init=False)  # deprecated

    static_map: StaticMap = field(default=None, repr=False)
    dynamic_map: DynamicMap = field(default=None, repr=False)

    button_sequences: list[ButtonSequence] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if self.model_theme is None:
            self.model_theme = self.theme
        if self.static_map is None:
            self.static_map = StaticMap(size=Size3D(1, 1, 1))
        if self.dynamic_map is None:
            self.dynamic_map = DynamicMap(size=Size3D(1, 1, 1))

    @property
    def size(self):
        return self.static_map.size

    def __getitem__(self, item):
        static = self.static_map.__getitem__(item)
        if static != Block.empty():
            return static
        else:
            return self.dynamic_map.__getitem__(item)

    def __setitem__(self, key, value):
        if isinstance(value, Block) or (isinstance(value, np.ndarray) and all([isinstance(b, Block) for b in value.flat])):
            self.static_map.__setitem__(key, value)
        else:
            self.dynamic_map.__setitem__(key, value)

    @classmethod
    def read(cls, path):
        kwargs: dict = {}
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

        spawn_point = Point3D.read(reader)
        kwargs['spawn_point'] = spawn_point
        assert spawn_point.z >= -20

        kwargs['zoom'] = reader.read_int16()
        if kwargs['zoom'] < 0:
            kwargs['angle_or_fov'] = reader.read_int16()
            kwargs['is_angle'] = bool(reader.read_uint8())

        exit_point = Point3D.read(reader)
        kwargs['exit_point'] = exit_point

        moving_platform_count = reader.read_uint16()
        moving_platforms = [MovingPlatform.read(reader) for _ in range(moving_platform_count)]

        bumper_count = reader.read_uint16()
        bumpers = [Bumper.read(reader) for _ in range(bumper_count)]

        falling_platform_count = reader.read_uint16()
        falling_platforms = [FallingPlatform.read(reader) for _ in range(falling_platform_count)]

        checkpoint_count = reader.read_uint16()
        checkpoints = [Checkpoint.read(reader) for _ in range(checkpoint_count)]

        camera_trigger_count = reader.read_uint16()
        camera_triggers = [CameraTrigger.read(reader) for _ in range(camera_trigger_count)]

        prism_count = reader.read_uint16()
        assert prism_count == prisms_count
        prisms = [Prism.read(reader) for _ in range(prism_count)]

        fan_count = reader.read_uint16()  # deprecated
        assert fan_count == 0

        block_event_count = reader.read_uint16()
        block_events = [BlockEvent.read(reader) for _ in range(block_event_count)]

        button_count = reader.read_uint16()
        buttons = [Button.read(reader) for _ in range(button_count)]

        # resolve references in block events
        for event in block_events:
            if isinstance(event, AffectMovingPlatformEvent):
                event.moving_platform = moving_platforms[event.moving_platform]
            elif isinstance(event, AffectBumperEvent):
                event.bumper = bumpers[event.bumper]
            elif isinstance(event, AffectButtonEvent):
                event.button = buttons[event.button]

        # resolve references in buttons
        for button in buttons:
            button.events = [block_events[i] for i in button.events]
            if button.moving_platform:
                button.moving_platform = moving_platforms[button.moving_platform]
                button._position = button.moving_platform._position + Point3D(0, 0, 1)

        # extract button sequences
        kwargs['button_sequences'] = []
        for id, button in enumerate(buttons):
            if button._children_count > 0:
                children = [b for b in buttons if b._parent_id == id]
                assert button._children_count == len(children)
                events = button.events
                kwargs['button_sequences'].append(ButtonSequence(buttons=[button] + children,
                                                                 sequence_in_order=button._sequence_in_order,
                                                                 events=events))

        # remove elements which are part of a button sequence from buttons
        # buttons = [b for b in buttons if b._children_count == 0 and b._parent_id == -1]

        othercube_count = reader.read_uint16()
        othercubes = [HoloCube.read(reader) for _ in range(othercube_count)]

        # resolve references in othercubes
        for cube in othercubes:
            if cube.moving_block_sync:
                cube.moving_block_sync = moving_platforms[cube.moving_block_sync]

        resizer_count = reader.read_uint16()
        resizers = [Resizer.read(reader) for _ in range(resizer_count)]

        mini_block_count = reader.read_uint16()  # deprecated
        assert mini_block_count == 0

        kwargs['theme'] = Theme(reader.read_uint8())
        kwargs['music_java'] = MusicJava(reader.read_uint8())
        kwargs['music'] = Music(reader.read_uint8())

        # generate map
        kwargs['static_map'] = collision_map.to_static_map()
        kwargs['dynamic_map'] = DynamicMap(size=kwargs['static_map'].size)
        for part in sum((moving_platforms, bumpers, falling_platforms, checkpoints, camera_triggers, prisms, buttons,
                        othercubes, resizers), start=[]):
            kwargs['dynamic_map'][part._position.x, part._position.y, part._position.z] += part
            del part._position

        level = cls(**kwargs)
        level._legacy_minimap = legacy_minimap
        return level

    def write(self, path, generate_model=True):
        moving_platforms = self.dynamic_map.get_all(MovingPlatform)
        bumpers = self.dynamic_map.get_all(Bumper)
        buttons = self.dynamic_map.get_all(Button)

        # turn button sequences into normal buttons
        buttons_without_coords = [b[1] for b in buttons]
        buttons_from_sequences = []
        for seq in self.button_sequences:
            parent = seq.buttons[0]
            parent_id = len(buttons_from_sequences)

            index = buttons_without_coords.index(parent)
            coords = buttons.pop(index)[0]
            buttons_without_coords.pop(index)

            parent._parent_id = -1
            parent._sequence_in_order = seq.sequence_in_order
            parent._children_count = len(seq.buttons) - 1
            if parent.events:
                print('overwriting events')
            parent.events = seq.events
            assert parent.mode == ButtonMode.STAY_DOWN
            buttons_from_sequences.append((coords, parent))

            for child in seq.buttons[1:]:
                assert child.events == []
                assert child.mode == ButtonMode.STAY_DOWN
                assert child._children_count == 0

                child._sequence_in_order = seq.sequence_in_order
                child._parent_id = parent_id

                index = buttons_without_coords.index(child)
                coords = buttons.pop(index)[0]
                buttons_without_coords.pop(index)
                buttons_from_sequences.append((coords, child))

        buttons = buttons_from_sequences + buttons

        # assign indices to everything that can be referenced
        for i, (_, p) in enumerate(moving_platforms):
            assert not hasattr(p, '_id')
            p._id = i

        for i, (_, b) in enumerate(bumpers):
            assert not hasattr(b, '_id')
            b._id = i

        # create block events
        event_id = 0
        block_events = []
        for i, (_, b) in enumerate(buttons):
            assert not hasattr(b, '_id')
            b._id = i

            for e in b.events:
                if hasattr(e, '_id'):
                    print('duplicate blockevent')
                    continue

                e._id = event_id
                block_events.append(e)
                event_id += 1

        writer = BinaryReader()
        writer.write_int32(self.id)
        writer.write_int32(len(self.name))
        writer.write_str(self.name)

        writer.write_uint16(self.s_plus_time)
        writer.write_uint16(self.s_time)
        writer.write_uint16(self.a_time)
        writer.write_uint16(self.b_time)
        writer.write_uint16(self.c_time)

        writer.write_uint16(len(self.dynamic_map.get_all(Prism)))

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

        writer.write_uint16(len(moving_platforms))
        for pos, e in moving_platforms:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        writer.write_uint16(len(bumpers))
        for pos, e in bumpers:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        falling_platforms = self.dynamic_map.get_all(FallingPlatform)
        writer.write_uint16(len(falling_platforms))
        for pos, e in falling_platforms:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        checkpoints = self.dynamic_map.get_all(Checkpoint)
        writer.write_uint16(len(checkpoints))
        for pos, e in checkpoints:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        camera_triggers = self.dynamic_map.get_all(CameraTrigger)
        writer.write_uint16(len(camera_triggers))
        for pos, e in camera_triggers:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        prisms = self.dynamic_map.get_all(Prism)
        writer.write_uint16(len(prisms))
        for pos, e in prisms:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        writer.write_uint16(0)  # fans_count

        writer.write_uint16(len(block_events))
        for e in block_events:
            e.write(writer)

        writer.write_uint16(len(buttons))
        for pos, e in buttons:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        othercubes = self.dynamic_map.get_all(HoloCube)
        writer.write_uint16(len(othercubes))
        for pos, e in othercubes:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        resizers = self.dynamic_map.get_all(Resizer)
        writer.write_uint16(len(resizers))
        for pos, e in resizers:
            e._position = Point3D(*pos)
            e.write(writer)
            del e._position

        writer.write_uint16(0)  # mini_blocks_count
        writer.write_uint8(self.theme.value)
        writer.write_uint8(self.music_java.value)
        writer.write_uint8(self.music.value)

        with open(path, 'wb') as f:
            f.write(writer.buffer())

        for (_, e) in moving_platforms + bumpers + buttons:
            del e._id

        for e in block_events:
            del e._id

        if generate_model:
            self.generate_model(path)

    def generate_model(self, levelname: str):
        def to_modelspace(v: Vec3D) -> Vec3D:
            return (v - translates[self.model_theme.value] - Vec3D(0, 0, size.y)) * 10

        size = self.size
        exit = self.exit_point

        models_namespace = 0x050DB82A
        materials = [0x2F2CC05D, 0x55ECE3AD, 0xC273F284, 0x0D11C513]
        child_models = [0x67228D77, 0x1DE2AE87, 0x8A7DBFAE, 0x451F8839]

        translates = [Vec3D(53.5, 2.25, -46), Vec3D(89.5, 2.25, -90), Vec3D(43, 2.25, -32.5), Vec3D(30, 2.25, -74.5)]

        themes = list(range(4))
        themes = themes[self.model_theme.value:] + themes[:self.model_theme.value]
        # themes now is the list [0, 1, 2, 3] but rotated so that level.model_theme is the first value

        models = [None, None, None, None]  # One model for each theme

        model_map = self.static_map.to_model_map()

        # resolve automatic values for height and theme
        for coords, block in model_map.items():
            if block.height is None:
                model_map[coords] += {'height': 1.0 if coords[2] > 0 else 0.5}
            if block.theme is None:
                model_map[coords] += {'theme': self.model_theme.value}
            elif block.theme < 0:
                model_map[coords] += {'theme': themes[-block.theme]}


        for (x, y, z), block in model_map.items():
            theme = block.theme

            if models[theme] is None:
                models[theme] = ESOModel(asset_material=AssetHash(name=materials[theme], namespace=models_namespace),
                                         type_flags=TypeFlag.NORMALS | TypeFlag.TEX_COORDS)

            model = models[theme]

            # top face: only drawn when there is no full block above and the block is not overlapping with the exit
            if model_map.get((x, y, z + 1), Block(height=0)).height < 1 and (abs(x - exit.x) > 1 or abs(y - exit.y) > 1 or z + 1 != exit.z):
                model.vertices.append(to_modelspace(Vec3D(x,     z + 1, y)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1, y)))
                model.vertices.append(to_modelspace(Vec3D(x,     z + 1, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x,     z + 1, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1, y)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1, y + 1)))
                model.normals += [Vec3D(0, 1, 0)] * 6

                tex_x = 0.51 if ((x + y) & 1) == 0 else 0.76  # check whether x + y is even to create a chessboard pattern
                tex_x_plus_1 = tex_x + 0.23
                tex_y = 1 - (z + 1) * 0.25  # the lowest 3 z layers have a gradient
                tex_y_plus_1 = tex_y + 0.25
                model.tex_coords.append(Vec2D(tex_x,        tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y))
                model.tex_coords.append(Vec2D(tex_x,        tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x,        tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y_plus_1))

            if block.height <= 0:
                continue

            z_base = z + 1 - block.height
            # south face
            if model_map.get((x + 1, y, z), Block(height=0)).height < block.height:
                model.vertices.append(to_modelspace(Vec3D(x + 1, z_base, y)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z_base, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1,  y)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z_base, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1,  y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1,  y)))
                model.normals += [Vec3D(1, 0, 0)] * 6

                tex_x = 0.26
                tex_x_plus_1 = 0.49
                tex_y = 1 - (z + 1) * 0.25  # the lowest 3 z layers have a gradient
                tex_y_plus_1 = tex_y + 0.25 - 0.25 * (1 - block.height)
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x,        tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y))
                model.tex_coords.append(Vec2D(tex_x,        tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x,        tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y))

            # east face
            if model_map.get((x, y + 1, z), Block(height=0)).height < block.height:
                model.vertices.append(to_modelspace(Vec3D(x,     z_base, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x,     z + 1,  y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z_base, y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x,     z + 1,  y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z + 1,  y + 1)))
                model.vertices.append(to_modelspace(Vec3D(x + 1, z_base, y + 1)))
                model.normals += [Vec3D(0, 0, 1)] * 6

                tex_x = 0.01
                tex_x_plus_1 = 0.24
                tex_y = 1 - (z + 1) * 0.25  # the lowest 3 z layers have a gradient
                tex_y_plus_1 = tex_y + 0.25 - 0.25 * (1 - block.height)
                model.tex_coords.append(Vec2D(tex_x,        tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x,        tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y_plus_1))
                model.tex_coords.append(Vec2D(tex_x,        tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y))
                model.tex_coords.append(Vec2D(tex_x_plus_1, tex_y_plus_1))

        models = [m for m in models if m is not None]

        name = '.'.join(levelname.split('.')[:-1]) if '.' in levelname else levelname
        eso = ESO(asset_header=AssetHeader(engine_version=EngineVersion.Version1804Edge,
                                           name=name + '.rmdl', namespace='models'),
                  eso_header=ESOHeader(num_models=len(models),
                                       scale=Vec3D(0.1, 0.1, 0.1),
                                       translate=translates[self.model_theme.value],
                                       asset_child=AssetHash(name=child_models[self.model_theme.value],
                                                             namespace=models_namespace),
                                       bounding_min=to_modelspace(Vec3D(0, 0, 0)),
                                       bounding_max=to_modelspace(Vec3D(size.x, size.z, size.y))),
                  models=models)

        eso.write(generate_crc(name=name, namespace='models') + '.eso')



if __name__ == '__main__':
    np.set_printoptions(threshold=np.inf)
    t = time.time()
    l = Level.read('babylonian_817.bin')
    print('write test.bin')
    l.write('test.bin')
    print('write test2.bin')
    l.write('test2.bin')

    test = Level.read('test.bin')
    test2 = Level.read('test2.bin')
    print(l == test)
    print(l == test2)

    # print(l.static_map[1, 2, 3])
    #
    # d = DynamicMap(size=Size3D(3, 4, 5))
    #
    # print(d[1, 2, 3])
    # print(d[100].shape)
    # print(d[100, 100].shape)
    # print(d[100, 100, 100])
    # print(d[:, :, 5])
    #
    # d[0, 0, 0] = MovingPlatform()
    #
    # d[-1, -2, -3] = Prism()
    # print(d.offset)
    #
    # d[6, 7, 8] = Bumper()
    # print(d.offset)
    # print(d.map)
    #
    # print(d[0, 0, 0])
    # print(d[-1, -2, -3])
    # print(d[6, 7, 8])


    print(time.time() - t)