import struct
from dataclasses import dataclass, field
from enum import Enum, Flag

from binary_reader import BinaryReader

from model.space import Vec2D, Vec3D


@dataclass
class Color:
    a: int
    r: int
    g: int
    b: int

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(*struct.unpack('BBBB', struct.pack('>I', reader.read_uint32())))

    def write(self, writer: BinaryReader):
        writer.write_uint32(int.from_bytes(struct.pack('BBBB', self.a, self.r, self.g, self.b)))


class EngineVersion(Enum):
    Version1803Rush = 0x0018000000000003
    Version1804Edge = 0x0018000000000004
    VersionD003EdgeOld = 0x00D0000000000003
    VersionD103EdgeOld = 0x00D1000000000003
    VersionD603EdgeOld = 0x00D6000000000003
    VersionDb03EdgeOld = 0x00DB000000000003
    VersionDf03EdgeOld = 0x00DF000000000003


@dataclass
class AssetHeader:
    engine_version: EngineVersion
    name: str
    namespace: str

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(engine_version=EngineVersion(reader.read_uint64()),
                   name=reader.read_str(64, 'ascii').rstrip('\x00'),
                   namespace=reader.read_str(64, 'ascii').rstrip('\x00'))

    def write(self, writer: BinaryReader):
        writer.write_uint64(self.engine_version.value)
        writer.write_str(self.name.ljust(64, '\x00'), encoding='ascii')
        writer.write_str(self.namespace.ljust(64, '\x00'), encoding='ascii')


@dataclass
class AssetHash:
    name: int = 0
    namespace: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(name=reader.read_uint32(),
                   namespace=reader.read_uint32())

    def write(self, writer: BinaryReader):
        writer.write_uint32(self.name)
        writer.write_uint32(self.namespace)

    def __repr__(self):
        return f'AssetHash({self.name:08X}{self.namespace:08X})'


@dataclass
class ESOHeader:
    unknown_1: int = 1
    unknown_2: int = 4096
    asset_child: AssetHash = field(default_factory=AssetHash)
    asset_sibling: AssetHash = field(default_factory=AssetHash)
    unknown_3: int = 0
    unknown_4: int = 0
    unknown_5: int = 0
    scale_xyz: float = 1
    translate: Vec3D = field(default_factory=Vec3D.zeros)
    rotate: Vec3D = field(default_factory=Vec3D.zeros)
    scale: Vec3D = field(default_factory=Vec3D.ones)
    unknown_6: float = 1
    unknown_7: int = 0
    num_models: int = 0
    bounding_min: Vec3D = field(default_factory=Vec3D.zeros)
    bounding_max: Vec3D = field(default_factory=Vec3D.zeros)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = dict(unknown_1=reader.read_int32(),
                      unknown_2=reader.read_int32(),
                      asset_child=AssetHash.read(reader),
                      asset_sibling=AssetHash.read(reader),
                      unknown_3=reader.read_int32(),
                      unknown_4=reader.read_int32(),
                      unknown_5=reader.read_int32(),
                      scale_xyz=reader.read_float(),
                      translate=Vec3D.read(reader),
                      rotate=Vec3D.read(reader),
                      scale=Vec3D.read(reader),
                      unknown_6=reader.read_float(),
                      unknown_7=reader.read_int32(),
                      num_models=reader.read_int32())

        if kwargs['num_models'] > 0:
            kwargs['bounding_min'] = Vec3D.read(reader)
            kwargs['bounding_max'] = Vec3D.read(reader)
        else:
            kwargs['bounding_min'] = Vec3D(0, 0, 0)
            kwargs['bounding_max'] = Vec3D(0, 0, 0)

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        writer.write_int32(self.unknown_1)
        writer.write_int32(self.unknown_2)
        self.asset_child.write(writer)
        self.asset_sibling.write(writer)
        writer.write_int32(self.unknown_3)
        writer.write_int32(self.unknown_4)
        writer.write_int32(self.unknown_5)
        writer.write_float(self.scale_xyz)
        self.translate.write(writer)
        self.rotate.write(writer)
        self.scale.write(writer)
        writer.write_float(self.unknown_6)
        writer.write_int32(self.unknown_7)
        writer.write_int32(self.num_models)

        if self.num_models > 0:
            self.bounding_min.write(writer)
            self.bounding_max.write(writer)


class TypeFlag(Flag):
    NORMALS = 1
    COLORS = 2
    TEX_COORDS = 4
    TEX_COORDS_2 = 8


@dataclass
class ESOModel:
    asset_material: AssetHash
    type_flags: TypeFlag
    unknown_1: int = 0
    vertices: list[Vec3D] = field(default_factory=list)
    normals: list[Vec3D] = field(default_factory=list)
    colors: list[Color] = field(default_factory=list)
    tex_coords: list[Vec2D] = field(default_factory=list)
    tex_coords_2: list[Vec2D] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, reader: BinaryReader):
        kwargs = dict(asset_material=AssetHash.read(reader),
                      type_flags=TypeFlag(reader.read_int32()))

        num_verts = reader.read_int32()
        num_polys = reader.read_int32()

        assert num_verts == num_polys * 3
        kwargs['unknown_1'] = reader.read_int32()
        assert kwargs['unknown_1'] == 0
        kwargs['vertices'] = [Vec3D.read(reader) for _ in range(num_verts)]

        if TypeFlag.NORMALS in kwargs['type_flags']:
            kwargs['normals'] = [Vec3D.read(reader) for _ in range(num_verts)]

        if TypeFlag.COLORS in kwargs['type_flags']:
            kwargs['colors'] = [Color.read(reader) for _ in range(num_verts)]

        if TypeFlag.TEX_COORDS in kwargs['type_flags']:
            kwargs['tex_coords'] = [Vec2D.read(reader) for _ in range(num_verts)]

        if TypeFlag.TEX_COORDS_2 in kwargs['type_flags']:
            kwargs['tex_coords_2'] = [Vec2D.read(reader) for _ in range(num_verts)]

        kwargs['indices'] = [reader.read_uint16() for _ in range(num_polys * 3)]

        return cls(**kwargs)

    def write(self, writer: BinaryReader):
        self.asset_material.write(writer)
        writer.write_uint32(self.type_flags.value)
        writer.write_int32(len(self.vertices))
        writer.write_int32(len(self.vertices) // 3)
        writer.write_int32(self.unknown_1)

        for v in self.vertices:
            v.write(writer)

        if TypeFlag.NORMALS in self.type_flags:
            for v in self.normals:
                v.write(writer)

        if TypeFlag.COLORS in self.type_flags:
            for c in self.colors:
                c.write(writer)

        if TypeFlag.TEX_COORDS in self.type_flags:
            for v in self.tex_coords:
                v.write(writer)

        if TypeFlag.TEX_COORDS_2 in self.type_flags:
            for v in self.tex_coords_2:
                v.write(writer)

        if not self.indices:
            self.indices = list(range(len(self.vertices)))

        assert len(self.indices) == len(self.vertices)
        for i in self.indices:
            writer.write_uint16(i)


@dataclass
class ESOFooter:
    unknown_1: float = 0
    unknown_2: float = 0
    unknown_3: int = 0
    unknown_4: int = 0

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(unknown_1=reader.read_float(),
                   unknown_2=reader.read_float(),
                   unknown_3=reader.read_int32(),
                   unknown_4=reader.read_int32())

    def write(self, writer: BinaryReader):
        writer.write_float(self.unknown_1)
        writer.write_float(self.unknown_2)
        writer.write_int32(self.unknown_3)
        writer.write_int32(self.unknown_4)


@dataclass
class ESO:
    asset_header: AssetHeader
    eso_header: ESOHeader
    models: list[ESOModel]
    footer_check: bool = False
    eso_footer: ESOFooter = field(default_factory=ESOFooter)

    @classmethod
    def read(cls, path: str):
        with open(path, 'rb') as f:
            reader = BinaryReader(bytearray(f.read()))

        kwargs = dict(asset_header=AssetHeader.read(reader),
                      eso_header=ESOHeader.read(reader))

        kwargs['models'] = [ESOModel.read(reader) for _ in range(kwargs['eso_header'].num_models)]

        if kwargs['eso_header'].num_models > 0:
            kwargs['footer_check'] = reader.read_uint32() == 1

            if kwargs['footer_check']:
                kwargs['eso_footer'] = ESOFooter.read(reader)

        return cls(**kwargs)

    def write(self, path: str):
        writer = BinaryReader()
        self.asset_header.write(writer)
        self.eso_header.write(writer)

        assert self.eso_header.num_models == len(self.models)
        for model in self.models:
            model.write(writer)

        if len(self.models) > 0:
            writer.write_uint32(self.footer_check)
            if self.footer_check:
                self.eso_footer.write(writer)

        with open(path, 'wb') as f:
            f.write(writer.buffer())

if __name__ == '__main__':
    ESO.read('12222669050DB82A.eso').write('test.eso')
    print(ESO.read('test.eso'))
