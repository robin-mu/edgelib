from dataclasses import dataclass

from binary_reader import BinaryReader


@dataclass(frozen=True)
class Vec2D:
    x: float
    y: float

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_float(),
                   y=reader.read_float())

    def write(self, writer: BinaryReader):
        writer.write_float(self.x)
        writer.write_float(self.y)

@dataclass(frozen=True)
class Vec3D:
    x: float
    y: float
    z: float

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(x=reader.read_float(),
                   y=reader.read_float(),
                   z=reader.read_float())

    def write(self, writer: BinaryReader):
        writer.write_float(self.x)
        writer.write_float(self.y)
        writer.write_float(self.z)

    def __add__(self, other):
        if isinstance(other, Vec3D):
            return Vec3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        if isinstance(other, Vec3D):
            return Vec3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other):
        return Vec3D(self.x * other, self.y * other, self.z * other)

    @classmethod
    def zeros(cls):
        return cls(0, 0, 0)

    @classmethod
    def ones(cls):
        return cls(1, 1, 1)