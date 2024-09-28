from __future__ import annotations

from dataclasses import dataclass, field
from binary_reader import BinaryReader
from bitstring import BitArray
import numpy as np

# avoid cyclic imports
from typing import TYPE_CHECKING
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
    size: Size3D
    data: np.ndarray

    def __getitem__(self, pos: tuple[slice, slice, slice]):
        return self.data[*pos]

    @classmethod
    def read(cls, reader: BinaryReader, size: Size3D):
        data = np.zeros((size.z, size.y, size.x), dtype=int)
        layer_length = size.x * size.y
        bytes_per_layer = int(np.ceil(layer_length / 8))

        for i in range(size.z):
            data[i] = np.reshape(BitArray(reader.read_bytes(bytes_per_layer))[:layer_length], (size.y, size.x))

        return cls(size, np.transpose(data))

    def write(self, writer: BinaryReader):
        assert self.size == self.data.shape
        data = np.transpose(self.data)
        for i in range(self.size.z):
            writer.write_bytes(BitArray(data[i].flatten()).tobytes())


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
    height of ``0.5`` and all other block have a height of ``1``. Note that this only affects the block appearance,
    the block will still have collision in the transparent part (if ``collision`` is set to ``True``).
    """
    collision: bool = True
    visible: bool = True
    theme: Theme | int = None
    height: float = None

    def __repr__(self):
        if self.collision and self.visible:
            return '█'
        else:
            return ' '

    def __add__(self, other: dict):
        return Block(collision=other['collision'] if 'collision' in other else self.collision,
                     visible=other['visible'] if 'visible' in other else self.visible,
                     theme=other['theme'] if 'theme' in other else self.theme,
                     height=other['height'] if 'height' in other else self.height)

@dataclass
class StaticMap:
    blocks: np.ndarray

    @classmethod
    def from_collision_map(cls, collision_map: BitCube):
        return cls(np.vectorize(lambda bit: Block(collision=bool(bit), visible=bool(bit)))(collision_map.data))

    def resize(self, x, y, z):
        self.blocks = np.pad(self.blocks, ((0, max(0, x - self.blocks.shape[0])),
                                           (0, max(0, y - self.blocks.shape[1])),
                                           (0, max(0, z - self.blocks.shape[2]))))
        self.blocks = self.blocks[:x, :y, :z]