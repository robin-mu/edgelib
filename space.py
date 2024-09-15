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

@dataclass
class Size3D:
    x: int
    y: int
    z: int
    
    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(z=reader.read_uint8(), x=reader.read_uint16(), y=reader.read_uint16())

@dataclass
class Point3D:
    x: int
    y: int
    z: int
    
    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_uint16(), y=reader.read_uint16(), z=reader.read_uint16())

@dataclass
class Cube:
    data: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 1)))

    def __getitem__(self, x, y, z):
        return self.data[x, y, z]

    def __repr__(self):
        return f'Cube(size={tuple(reversed(self.data.shape))})'

    @classmethod
    def read(cls, reader: BinaryReader, size: Size3D):
        data = np.zeros((size.z, size.y, size.x), dtype=int)
        layer_length = size.x * size.y
        bytes_per_layer = int(np.ceil(layer_length / 8))

        for i in range(size.z):
            data[i] = np.reshape(BitArray(reader.read_bytes(bytes_per_layer))[:layer_length], (size.y, size.x))

        return cls(data)
    