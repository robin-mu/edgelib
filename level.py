from binary_reader import BinaryReader
from dataclasses import dataclass, field

from space import Size3D, Point3D, Cube
from dynamic_parts import MovingPlatform, Bumper, FallingPlatform, Checkpoint, CameraTrigger, Prism, Button
from events import BlockEvent

@dataclass
class Level:
    id: int
    size: Size3D
    spawn_point: Point3D
    exit_point: Point3D
    name: str = ''
    s_plus_time: int = 1
    s_time: int = 2
    a_time: int = 3
    b_time: int = 4
    c_time: int = 5
    theme: int = 0
    music_java: int = 0
    music: int = 6
    zoom: int = -1
    angle_or_fov: int = 0
    is_angle: bool = False
    model_theme: int = 0

    legacy_minimap: Cube = field(default_factory=Cube)
    collision_map: Cube = field(default_factory=Cube)

    moving_platforms: list[MovingPlatform] = field(default_factory=list, repr=False)
    bumpers: list[Bumper] = field(default_factory=list, repr=False)
    falling_platforms: list[FallingPlatform] = field(default_factory=list, repr=False)
    checkpoints: list[Checkpoint] = field(default_factory=list, repr=False)
    camera_triggers: list[CameraTrigger] = field(default_factory=list, repr=False)
    prisms: list[Prism] = field(default_factory=list, repr=False)
    buttons: list[Button] = field(default_factory=list)
    
    @classmethod
    def read(cls, path):
        kwargs = {}
        with open(path, 'rb') as f:
            reader = BinaryReader(f.read())

        kwargs['id'] = reader.read_int32()

        name_len = reader.read_int32()
        kwargs['name'] = reader.read_str(name_len, encoding='utf-8')

        kwargs['s_plus_time'] = reader.read_uint16()
        kwargs['s_time'] = reader.read_uint16()
        kwargs['a_time'] = reader.read_uint16()
        kwargs['b_time'] = reader.read_uint16()
        kwargs['c_time'] = reader.read_uint16()
        assert kwargs['s_plus_time'] < kwargs['s_time'] < kwargs['a_time'] < kwargs['b_time'] < kwargs['c_time']

        prisms_count = reader.read_int16()

        size = Size3D.read(reader)
        kwargs['size'] = size

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

        kwargs['legacy_minimap'] = Cube.read(reader, Size3D(x=legacy_minimap_width, y=legacy_minimap_length, z=1))
        
        kwargs['collision_map'] = Cube.read(reader, size)

        kwargs['spawn_point'] = Point3D.read(reader)

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
        for button in kwargs['buttons']:
            button.events = [block_events[i] for i in button.events]

        return cls(**kwargs)

print(Level.read('level300.bin'))