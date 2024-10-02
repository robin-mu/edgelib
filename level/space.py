from __future__ import annotations

from dataclasses import dataclass, InitVar
from typing import TYPE_CHECKING  # avoid cyclic imports

import numpy as np
from binary_reader import BinaryReader
from bitstring import BitArray

if TYPE_CHECKING:
    from level.level import Theme


@dataclass
class Size2D:
    x: int = 0
    y: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_uint8(), y=reader.read_uint8())

    def write(self, writer: BinaryReader):
        writer.write_uint8(self.x)
        writer.write_uint8(self.y)

@dataclass
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


@dataclass
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

@dataclass
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
        return StaticMap(blocks=np.vectorize(lambda bit: Block.full() if bit else Block.empty())(self.data))


@dataclass(frozen=True)
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
class StaticMap:
    blocks: np.ndarray = None
    size: InitVar[Size3D] = None

    def __post_init__(self, size: Size3D):
        if self.blocks is None:
            self.blocks = np.full((size.x, size.y, size.z), Block.empty())

    @property
    def size(self):
        return Size3D(*self.blocks.shape)

    def resize(self, newsize: Size3D=None, top=0, bottom=0, north=0, south=0, east=0, west=0):
        """
        Either newsize or the other six parameters have to be given. If you enter newsize, it determines the new size of
        the level and the other parameters are ignored. New blocks are added or removed at the top, east, and south faces of the
        level.
        If you enter the other six parameters, the level is padded with the specified number of blocks on each side.
        Negative numbers are allowed to make the level smaller.
        """
        if newsize is not None:
            self.blocks = np.pad(self.blocks, ((0, max(0, newsize.x - self.blocks.shape[0])),
                                               (0, max(0, newsize.y - self.blocks.shape[1])),
                                               (0, max(0, newsize.z - self.blocks.shape[2]))),
                                 constant_values=Block.empty())
            self.blocks = self.blocks[:newsize.x, :newsize.y, :newsize.z]
        else:
            self.blocks = np.pad(self.blocks, ((max(0, west), max(0, east)),
                                               (max(0, north), max(0, south)),
                                               (max(0, bottom), max(0, top))),
                                 constant_values=Block.empty())
            self.blocks = self.blocks[max(0, -west):self.blocks.shape[0] + east,
                                      max(0, -north):self.blocks.shape[1] + south,
                                      max(0, -bottom):self.blocks.shape[2] + top]

    def to_collision_map(self) -> BitCube:
        return BitCube(data=np.vectorize(lambda block: int(block.collision))(self.blocks))

    def to_model_map(self) -> dict:
        mask = np.vectorize(lambda block: block.visible)(self.blocks)
        coords = np.argwhere(mask)
        return dict(zip([tuple(c) for c in coords], self.blocks[tuple(coords.T)]))


    def __getitem__(self, item):
        try:
            if isinstance(item, tuple):
                return self.blocks[*item]
            return self.blocks[item]
        except IndexError:
            return Block.empty()

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            self.blocks[*key] = value
        else:
            self.blocks[key] = value

    def __repr__(self):
        return str(self.blocks.T)