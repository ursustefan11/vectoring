import bpy, math, sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from material import MaterialManager
from object import ObjectManipulator

class WorldObjects:
    def __init__(self):
        self.manipulator = ObjectManipulator()

    def create_backdrop_plane(self):
        bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -20))
        plane = bpy.context.object
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        plane.data.vertices[2].select = True
        plane.data.vertices[3].select = True
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 200)})

        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        plane.data.edges[2].select = True
        plane.data.edges[6].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.bevel(offset_type="OFFSET", offset=50, segments=100, profile=0.5)

        bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.shade_smooth()

        self.manipulator.rotate_object(plane, 0, 0, 90)
        plane_material = MaterialManager.create_material(name="BG", color=(1, 1, 1, 1))
        MaterialManager.apply_material(plane, plane_material)

    def add_light(
        self,
        name: str,
        location: tuple,
        type: str = "POINT",
        energy: float = 1000.0,
        size: float = 1.0,
    ) -> bpy.types.Object:
        
        bpy.ops.object.light_add(type=type, location=location)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        if type == "AREA":
            light.data.size = size
        return light

    def add_lights(self):
        d = 150
        s = 20
        angle = 45

        x = d * math.cos(math.radians(angle))
        y = d * math.sin(math.radians(angle))

        f = self.add_light("front", (x, -y, 10), type="AREA", energy=2000.0, size=s)
        pitch = math.degrees(math.atan2(10, x))
        yaw = math.degrees(math.atan2(-y, x))
        ObjectManipulator.rotate_object(f, 0, 0, 45)

        # r = self.add_light("right", (0, d, 0), type="AREA", energy=1200.0, size=s)
        # ObjectManipulator.rotate_object(r, -90, 0, 0)

        # l = self.add_light("left", (0, -d, 0), type="AREA", energy=2000.0, size=s)
        # ObjectManipulator.rotate_object(l, 90, 0, 0)