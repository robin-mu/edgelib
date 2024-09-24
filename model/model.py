from binary_reader import BinaryReader

from dataclasses import dataclass, field

from space import Vec2D, Vec3D
from enum import Enum, Flag


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


@dataclass
class AssetHash:
    name: int
    namespace: int

    @classmethod
    def read(cls, reader: BinaryReader):
        return cls(name=reader.read_uint32(),
                   namespace=reader.read_uint32())


@dataclass
class ESOHeader:
    unknown_1: int
    unknown_2: int
    asset_child: AssetHash
    asset_sibling: AssetHash
    unknown_3: int
    unknown_4: int
    unknown_5: int
    scale_xyz: float
    translate: Vec3D
    rotate: Vec3D
    scale: Vec3D
    unknown_6: float
    unknown_7: int
    num_models: int
    bounding_min: Vec3D
    bounding_max: Vec3D

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


class TypeFlag(Flag):
    NORMALS = 1
    COLORS = 2
    TEX_COORDS = 4
    TEX_COORDS_2 = 8


@dataclass
class ESOModel:
    asset_material: AssetHash
    type_flags: TypeFlag
    num_verts: int
    num_polys: int
    unknown_1: int
    vertices: list[Vec3D] = field(default_factory=list)
    normals: list[Vec3D] = field(default_factory=list)
    colors: list[int] = field(default_factory=list)
    tex_coords: list[Vec2D] = field(default_factory=list)
    tex_coords_2: list[Vec2D] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)


@dataclass
class ESOFooter:
    unknown_1: float
    unknown_2: float
    unknown_3: int
    unknown_4: int


@dataclass
class ESO:
    asset_header: AssetHeader
    eso_header: ESOHeader
    models: list[ESOModel] = None
    footer_check: int = None
    eso_footer: ESOFooter = None

    @classmethod
    def read(cls, path: str):
        with open(path, 'rb') as f:
            reader = BinaryReader(bytearray(f.read()))

        kwargs = dict(asset_header=AssetHeader.read(reader),
                      eso_header=ESOHeader.read(reader))

        return cls(**kwargs)


print(ESO.read('F388B822050DB82A.eso'))
