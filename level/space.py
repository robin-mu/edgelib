from __future__ import annotations

from dataclasses import dataclass, InitVar
from typing import TYPE_CHECKING  # avoid cyclic imports

import numpy as np
from binary_reader import BinaryReader
from bitstring import BitArray

if TYPE_CHECKING:
    from level.level import Theme


@dataclass(frozen=True)
class Size2D:
    x: int = 0
    y: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_uint8(), y=reader.read_uint8())

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.x)
        writer.write_uint8(self.y)

@dataclass(frozen=True)
class Size3D:
    x: int
    y: int
    z: int
    
    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(z=reader.read_uint8(), x=reader.read_uint16(), y=reader.read_uint16())

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.z)
        writer.write_uint16(self.x)
        writer.write_uint16(self.y)

    def __eq__(self, other):
        if isinstance(other, Size3D):
            return self.x == other.x and self.y == other.y and self.z == other.z
        return self.x == other[0] and self.y == other[1] and self.z == other[2]


@dataclass(frozen=True)
class Point3D:
    x: int
    y: int
    z: int
    
    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_int16(), y=reader.read_int16(), z=reader.read_int16())

    def write(self, writer: BinaryReader):
        writer.write_int16(self.x)
        writer.write_int16(self.y)
        writer.write_int16(self.z)

    def __add__(self, other):
        if isinstance(other, Point3D):
            return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        if isinstance(other, Point3D):
            return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass(frozen=True)
class BitCube:
    """
    A cube (i.e. 3-dimensional array) of bits
    """
    data: np.ndarray

    @classmethod
    def read(cls, reader: BinaryReader, size: Size3D):
        data = np.zeros((size.z, size.y, size.x), dtype=int)
        layer_length = size.x * size.y
        bytes_per_layer = int(np.ceil(layer_length / 8))

        for i in range(size.z):
            data[i] = np.reshape(BitArray(reader.read_bytes(bytes_per_layer))[:layer_length], (size.y, size.x))

        return cls(data.T)

    @classmethod
    def zeros(cls, size: Size3D):
        return cls(np.zeros((size.x, size.y, size.z), dtype=int))

    def write(self, writer: BinaryReader):
        data = self.data.T
        for layer in data:
            writer.write_bytes(BitArray(layer.flatten()).tobytes())

    def to_static_map(self) -> StaticMap:
        return StaticMap(np.vectorize(lambda bit: Block.full() if bit else Block.empty())(self.data))

    def __eq__(self, other):
        return np.all(self.data == other.data)

@dataclass(frozen=True, eq=True)
class Block:
    """
    :cvar collision: Whether the player cube can collide with this block.
    :cvar visible: A model will be generated for this block, making it visible in the level
    :cvar theme: The brightness theme of this block. Instead of a ``Theme`` enum value, you can also enter ``None`` to use
    the same theme as the level, or a negative number which specifies a brightness difference, where ``-1`` means "1 shade
    darker than the level theme" etc. Note that this wraps around after the darkest theme, so if your level theme is
    ``Theme.BLACK`` and you enter ``-1``, the block will have ``Theme.WHITE`` as its theme.
    :cvar height: The percentage of the block that is visible, starting from the top, e.g. a value of ``0.5`` will make
    the top half of the block visible and the bottom half transparent.  A value of ``0`` doesn't make the block invisible
    (for that you can set ``visible`` to ``False``) but will draw only the top face
    of the block. Set this to ``None`` to use the default block height, i.e. blocks with a Z coordinate of 0 have a
    height of ``0.5`` and all other blocks have a height of ``1``. Note that this only affects the block appearance,
    the block will still have collision in the transparent part (if ``collision`` is set to ``True``).
    """
    collision: bool = True
    visible: bool = True
    theme: Theme | int = None
    height: float = None

    def __repr__(self):
        if self.visible:
            if self.height is None or self.height > 0.5:
                return '█'
            else:
                return '▀'
        else:
            return ' '

    def __add__(self, other: dict):
        return Block(collision=other.get('collision', self.collision),
                     visible=other.get('visible', self.visible),
                     theme=other.get('theme', self.theme),
                     height=other.get('height', self.height))

    @classmethod
    def empty(cls):
        return cls(collision=False, visible=False)

    @classmethod
    def full(cls):
        return cls(collision=True, visible=True)

    @classmethod
    def half(cls):
        return cls(collision=True, visible=True, height=0.5)


@dataclass
class DynamicMap:
    map: np.ndarray = None
    offset: tuple[int, int, int] = (0, 0, 0)
    size: InitVar[Size3D] = None

    def __post_init__(self, size: Size3D):
        if self.map is None:
            self.map = np.full((size.x, size.y, size.z), fill_value=None, dtype=object)

    @staticmethod
    def pad(arr, west=0, east=0, north=0, south=0, bottom=0, top=0):
        return np.pad(arr, ((max(0, west), max(0, east)),
                                           (max(0, north), max(0, south)),
                                           (max(0, bottom), max(0, top))),
                             constant_values=None)

    def get_all(self, type) -> list:
        mask = np.vectorize(lambda part: isinstance(part, type))(self.map)
        coords = np.argwhere(mask)
        coords_with_offset = coords - np.array(self.offset)
        parts = list(zip([tuple(c) for c in coords_with_offset], self.map[tuple(coords.T)]))

        arrays_mask = np.vectorize(lambda part: isinstance(part, list))(self.map)
        arrays_coords = np.argwhere(arrays_mask)
        for c in arrays_coords:
            for part in self.map[tuple(c)]:
                if isinstance(part, type):
                    parts.append((tuple(c - np.array(self.offset)), part))

        return parts

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            item = item,

        pad_args = []
        for i, c in enumerate(item):
            if isinstance(c, slice):
                pad_args.append(-min(c.start or 0, (c.stop or 0) + 1) - self.offset[i])
                pad_args.append(max(c.start or 0, (c.stop or 0) - 1) - (self.map.shape[i] - self.offset[i]))
            else:
                pad_args.append(-c - self.offset[i])
                pad_args.append(c + 1 - (self.map.shape[i] - self.offset[i]))

        if any([arg > 0 for arg in pad_args]):
            temp = DynamicMap.pad(self.map, *pad_args)
            temp_offset = tuple(self.offset[i] + max(0, pad_args[2*i] if 2*i < len(pad_args) else 0) for i in range(3))
        else:
            temp = self.map
            temp_offset = self.offset

        item_plus_offset = []
        for i, c in enumerate(item):
            if isinstance(c, slice):
                new_slice = slice(c.start + temp_offset[i] if c.start is not None else None,
                                  c.stop + temp_offset[i] if c.stop is not None else None,
                                  c.step)
                item_plus_offset.append(new_slice)
            else:
                item_plus_offset.append(c + temp_offset[i])
        return np.ndarray.__getitem__(temp, tuple(item_plus_offset))

    def __setitem__(self, key, value):
        if not isinstance(key, tuple):
            key = key,

        pad_args = []
        for i, c in enumerate(key):
            if isinstance(c, slice):
                pad_args.append(-min(c.start or 0, (c.stop or 0) + 1) - self.offset[i])
                pad_args.append(max(c.start or 0, (c.stop or 0) - 1) - (self.map.shape[i] - self.offset[i]))
            else:
                pad_args.append(-c - self.offset[i])
                pad_args.append(c + 1 - (self.map.shape[i] - self.offset[i]))

        if any([arg > 0 for arg in pad_args]):
            self.map = DynamicMap.pad(self.map, *pad_args)
            self.offset = tuple(self.offset[i] + max(0, pad_args[2*i] if 2*i < len(pad_args) else 0) for i in range(3))

        key_plus_offset = []
        for i, c in enumerate(key):
            if isinstance(c, slice):
                new_slice = slice(c.start + self.offset[i] if c.start is not None else None,
                                 c.stop + self.offset[i] if c.stop is not None else None,
                                 c.step)
                key_plus_offset.append(new_slice)
            else:
                key_plus_offset.append(c + self.offset[i])

        np.ndarray.__setitem__(self.map, tuple(key_plus_offset), value)

    def setitem_append(self, coords: tuple, value) -> None:
        """
        In some cases, multiple dynamic parts are located at the same coordinate, e.g. moving platforms that are on the
        same loop, but with different time offsets. To append a part to the parts which already are at this coordinate,
        you can use ``map[coords] += value``.
        """
        self[coords] += value

    def __eq__(self, other):
        return np.all(self.map == other.map) and self.offset == other.offset

@dataclass
class StaticMap:
    blocks: np.ndarray = None
    size: InitVar[Size3D] = None

    def __post_init__(self, size: Size3D):
        if self.blocks is None:
            self.blocks = np.full((size.x, size.y, size.z), fill_value=Block.empty(), dtype=object)

    @property
    def size(self):
        mask = np.vectorize(lambda block: block != Block.empty())(self.blocks)
        return Size3D(*(np.max(np.argwhere(mask), axis=0) + 1))

    @staticmethod
    def resize(arr, x=0, y=0, z=0):
        return np.pad(arr, ((0, max(0, (x or 0) - arr.shape[0])),
                            (0, max(0, (y or 0) - arr.shape[1])),
                            (0, max(0, (z or 0) - arr.shape[2]))),
                             constant_values=Block.empty())

    def to_collision_map(self) -> BitCube:
        return BitCube(data=np.vectorize(lambda block: int(block.collision))(self.blocks))

    def to_model_map(self) -> dict:
        mask = np.vectorize(lambda block: block.visible)(self.blocks)
        coords = np.argwhere(mask)
        return dict(zip([tuple(c) for c in coords], self.blocks[tuple(coords.T)]))

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            item = item,

        size = [c.stop if isinstance(c, slice) else c + 1 for c in item]

        if any([s > self.blocks.shape[i] for i, s in enumerate(size)]):
            temp = StaticMap.resize(self.blocks, *size)
        else:
            temp = self.blocks
        return np.ndarray.__getitem__(temp, item)

    def __setitem__(self, key, value):
        if not isinstance(key, tuple):
            key = key,

        size = [c.stop if isinstance(c, slice) else c + 1 for c in key]

        if any([s > self.blocks.shape[i] for i, s in enumerate(size)]):
            self.blocks = StaticMap.resize(self.blocks, *size)

        np.ndarray.__setitem__(self.blocks, key, value)

    def __repr__(self):
        return str(self.blocks.T)

    def __eq__(self, other):
        return np.all(self.blocks == other.blocks)