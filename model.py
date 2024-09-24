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
        kwargs = {}
        kwargs['engine_version'] = EngineVersion(reader.read_uint64())
        kwargs['name'] = reader.read_str(64, 'ascii').rstrip('\x00')
        kwargs['namespace'] = reader.read_str(64, 'ascii').rstrip('\x00')

        return cls(**kwargs)


@dataclass
class AssetHash:
    hash_name: int
    hash_namespace: int


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
    eso_header: ESOHeader = None
    models: list[ESOModel] = None
    footer_check: int = None
    eso_footer: ESOFooter = None

    @classmethod
    def read(cls, path: str):
        with open(path, 'rb') as f:
            reader = BinaryReader(bytearray(f.read()))

        kwargs = {}
        kwargs['asset_header'] = AssetHeader.read(reader)


        return cls(**kwargs)

print(ESO.read('F388B822050DB82A.eso'))