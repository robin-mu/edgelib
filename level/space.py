from dataclasses import dataclass, field
from binary_reader import BinaryReader
from bitstring import BitArray
import numpy as np

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
class Cube:
    size: Size3D
    data: np.ndarray = field(default=None, repr=False)

    def __post_init__(self):
        if self.data is None:
            self.data = np.zeros((self.size.z, self.size.y, self.size.x))

    def __getitem__(self, pos: tuple[slice, slice, slice]):
        return self.data[*reversed(pos)]

    @classmethod
    def read(cls, reader: BinaryReader, size: Size3D):
        data = np.zeros((size.z, size.y, size.x), dtype=int)
        layer_length = size.x * size.y
        bytes_per_layer = int(np.ceil(layer_length / 8))

        for i in range(size.z):
            data[i] = np.reshape(BitArray(reader.read_bytes(bytes_per_layer))[:layer_length], (size.y, size.x))

        return cls(size, data)

    def write(self, writer: BinaryReader):
        assert self.size == tuple(reversed(self.data.shape))
        for i in range(self.size.z):
            writer.write_bytes(BitArray(self.data[i].flatten()).tobytes())