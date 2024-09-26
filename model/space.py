from dataclasses import dataclass

from binary_reader import BinaryReader


@dataclass
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

@dataclass
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