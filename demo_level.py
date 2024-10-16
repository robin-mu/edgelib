# This demo level is an exact rewrite of the demo level maysunrise used in their EdgeEditLib
# https://github.com/maysunrise/EdgeEditLib/blob/main/Examples/DemoLevel.cs

from level.events import AffectMovingPlatformEvent, Direction, KeyEventType
from level.level import Level, Theme, Music
from level.dynamic_parts import *
from level.space import Block

level = Level(id=9992,
              name='demo level',
              theme=Theme.WHITE,
              music=Music.PAD,
              s_plus_time=20,
              s_time=30,
              a_time=40,
              b_time=50,
              c_time=60,
              spawn_point=Point3D(8, 8, 6),
              exit_point=Point3D(14, 2, 1))

# static blocks
level[0:16, 0:16, 0] = Block.full()
level[6:13, 4:7, 0] = Block.empty()
level[6, 0, 1] = Block.full()
level[6, 1, 2] = Block.full()

for i in range(4):
    level[2, 12, i] = Block.full()

# falling platforms
level[8, 6, 1] = FallingPlatform(float_time=10)
level[8, 5, 1] = FallingPlatform(float_time=10)
level[8, 4, 1] = FallingPlatform(float_time=10)

# prisms
level[5, 2, 1] = Prism()
level[5, 3, 1] = Prism()
level[5, 4, 1] = Prism()

# bumpers
level[10, 1, 1] = Bumper(north=BumperSide(start_delay=10, pulse_rate=10),
                         east=BumperSide(start_delay=10, pulse_rate=10),
                         south=BumperSide(start_delay=10, pulse_rate=10),
                         west=BumperSide(start_delay=10, pulse_rate=10))

# resizers
level[4, 12, 1] = Resizer(ResizerDirection.SHRINK)
level[4, 13, 1] = Resizer(ResizerDirection.GROW)

# camera triggers
level[6, 1, 2] = CameraTrigger(reset=False, duration=30, angle_or_fov=100, is_angle=True)
level[6, 1, 1] = CameraTrigger(reset=True, duration=30)

# moving platforms
waypoints = [Waypoint(offset_to_previous_waypoint=Point3D(0, 0, 0), travel_time=25, pause_time=5),
             Waypoint(offset_to_previous_waypoint=Point3D(4, 0, 0), travel_time=25, pause_time=5),
             Waypoint(offset_to_previous_waypoint=Point3D(0, 4, 0), travel_time=25, pause_time=5),
             Waypoint(offset_to_previous_waypoint=Point3D(-4, 0, 0), travel_time=25, pause_time=5)]
platform = MovingPlatform(auto_start=False, loop_start_index=0, waypoints=waypoints)
level[0, 0, 2] = platform

waypoints2 = [Waypoint(offset_to_previous_waypoint=Point3D(0, 0, 0), travel_time=5, pause_time=5),
              Waypoint(offset_to_previous_waypoint=Point3D(0, 2, 0), travel_time=5, pause_time=10),
              Waypoint(offset_to_previous_waypoint=Point3D(0, -1, 0), travel_time=5, pause_time=5),
              Waypoint(offset_to_previous_waypoint=Point3D(0, -1, 1), travel_time=5, pause_time=5)]
platform2 = MovingPlatform(auto_start=False, loop_start_index=0, waypoints=waypoints2)
level[0, 2, 3] = platform2

# buttons
event = AffectMovingPlatformEvent(platform, traverse_waypoints=0)
level[1, 1, 1] = Button(mode=ButtonMode.TOGGLE, events=[event])

event2 = AffectMovingPlatformEvent(platform2, traverse_waypoints=0)
level[1, 3, 1] = Button(mode=ButtonMode.TOGGLE, events=[event2])

# dark cubes
key_events = [KeyEvent(100, Direction.WEST, KeyEventType.DOWN),
              KeyEvent(120, Direction.WEST, KeyEventType.UP),
              KeyEvent(160, Direction.NORTH, KeyEventType.DOWN),
              KeyEvent(190, Direction.NORTH, KeyEventType.UP),
              KeyEvent(8000, Direction.WEST, KeyEventType.UP)]
level[3, 2, 1] = DarkCube(position_cube=Point3D(4, 8, 2), radius=Size2D(8, 8), key_events=key_events)

level.write('demolevelpy.bin')