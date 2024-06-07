import bpy, random, bmesh, math
from mathutils import Vector


class Configurator:
    def __init__(self):
        self.apply()

    def apply(self) -> None:
        self.enable_addons()
        self.reset_scene()
        self.set_units_to_mm()
        self.set_render_engine_to_gpu()

    def set_units_to_mm(self) -> None:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"

    def reset_scene(self) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        for obj in bpy.context.scene.objects:
            if obj.type not in ["CAMERA", "LIGHT"]:
                obj.select_set(True)
            else:
                obj.select_set(False)

        bpy.ops.object.delete(use_global=False, confirm=False)

        for collection in bpy.data.collections:
            if collection.name not in ["Camera", "Light"]:
                bpy.data.collections.remove(collection)

    def enable_addons(self) -> None:
        if not bpy.ops.preferences.addon_enable(module="io_import_dxf"):
            bpy.ops.preferences.addon_install(module="io_import_dxf")

    def set_render_engine_to_gpu(self) -> None:
        bpy.context.scene.cycles.device = "GPU"
        prefs = bpy.context.preferences
        cprefs = prefs.addons["cycles"].preferences

        for compute_device_type in ("CUDA", "OPENCL", "NONE"):
            try:
                cprefs.compute_device_type = compute_device_type
                break
            except TypeError:
                pass

        for device in cprefs.devices:
            device.use = True

    @staticmethod
    def create_collections() -> list[bpy.types.Collection]:
        collection_names = ["body", "engraving", "handles"]
        collections = []

        for name in collection_names:
            if name not in bpy.data.collections:
                coll = bpy.data.collections.new(name)
                bpy.context.scene.collection.children.link(coll)
            else:
                coll = bpy.data.collections[name]
            collections.append(coll)

        return collections


class Importer:
    def __init__(self, path):
        self.path = path
        self.config = Configurator()

    def main(self) -> bool:
        return self.import_file()

    def import_file(self) -> bool:
        collections = self.config.create_collections()
        bpy.ops.import_scene.dxf(filepath=self.path)
        imported_svg = bpy.context.scene.objects

        if imported_svg:
            self.organize_imported_objects(imported_svg, collections)
            return True
        else:
            raise ValueError("No objects were imported. Check the SVG file.")

    def organize_imported_objects(self, imported_svg, collections) -> None:
        for obj in imported_svg:
            for collection in obj.users_collection:
                collection.objects.unlink(obj)

            if "body" in obj.name.lower():
                collections[0].objects.link(obj)
            elif "engraving" in obj.name.lower():
                collections[1].objects.link(obj)
            elif "handle" in obj.name.lower():
                collections[2].objects.link(obj)

            local_bbox_center = 0.125 * sum(
                (Vector(b) for b in obj.bound_box), Vector()
            )
            obj.location = obj.location - local_bbox_center
            obj.select_set(True)
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")

    def processed_objects(self):
        return bpy.context.scene.objects


class ObjectManipulator:
    def set_active_object(self, obj: bpy.types.Object) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    def convert_to_mesh(self, obj: bpy.types.Object) -> None:
        self.set_active_object(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.curve.select_all(action="SELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.convert(target="MESH")

    def clean_up_mesh(self, target_obj: bpy.types.Object) -> None:
        self.set_active_object(target_obj)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as e:
            raise ValueError(f"Error while cleaning up the mesh: {e}")

    def add_bevel(self, obj: bpy.types.Object, width: float, segments: int) -> None:
        self.set_active_object(obj)
        bpy.ops.object.modifier_add(type="BEVEL")
        bpy.context.object.modifiers["Bevel"].width = width
        bpy.context.object.modifiers["Bevel"].segments = segments
        self.apply_modifier(obj, "Bevel")

    def apply_boolean_modifier(
        self,
        obj: bpy.types.Object,
        target: bpy.types.Object,
        vertex_group_name: str = "",
    ) -> None:
        self.set_active_object(obj)

        original_vertices = set(tuple(v.co) for v in obj.data.vertices)

        bpy.ops.object.modifier_add(type="BOOLEAN")
        bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
        bpy.context.object.modifiers["Boolean"].object = target
        self.apply_modifier(obj, "Boolean")

        if len(vertex_group_name):
            new_vertices = [
                v.index
                for v in obj.data.vertices
                if tuple(v.co) not in original_vertices and v.co.z != 0
            ]
            self.assign_vertices_to_group(obj, new_vertices, vertex_group_name)

    def apply_modifier(self, obj: bpy.types.Object, modifier_name: str) -> None:
        override = bpy.context.copy()
        override["object"] = obj
        override["active_object"] = obj
        override["selected_objects"] = [obj]
        bpy.ops.object.modifier_apply(modifier=modifier_name)

    def assign_vertices_to_group(
        self, obj: bpy.types.Object, vertex_indices: list, group_name: str
    ) -> None:
        if group_name not in obj.vertex_groups:
            vertex_group = obj.vertex_groups.new(name=group_name)
        else:
            vertex_group = obj.vertex_groups[group_name]

        vertex_group.add(vertex_indices, 1.0, "ADD")

    def add_subdivision_surface(
        self, obj: bpy.types.Object, levels: int, render_levels: int
    ) -> None:
        self.set_active_object(obj)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels
        self.apply_modifier(obj, "Subdivision")

    def hide_object(self, obj: bpy.types.Object) -> None:
        obj.hide_viewport = True

    def add_holes(self, body, holes) -> bool:
        try:
            self.apply_boolean_modifier(body, holes)
            self.hide_object(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(
        self, body: bpy.types.Object, engraving: bpy.types.Object
    ) -> bool:
        try:
            self.apply_boolean_modifier(body, engraving, vertex_group_name="engraving")
            self.hide_object(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
        return True

    def rotate_object(
        self,
        object: bpy.types.Object,
        rotation_x: float,
        rotation_y: float,
        rotation_z: float,
    ):
        object.rotation_euler[0] = math.radians(rotation_x)
        object.rotation_euler[1] = math.radians(rotation_y)
        object.rotation_euler[2] = math.radians(rotation_z)


class WorldObjects:
    def __init__(self):
        self.manipulator = ObjectManipulator()

    def white_background(self):
        bpy.ops.mesh.primitive_plane_add(
            size=100, enter_editmode=False, location=(-50, 0, 0)
        )
        plane = bpy.context.object
        mat = bpy.data.materials.new(name="WhiteMaterial")
        mat.diffuse_color = (1, 1, 1, 1)
        plane.data.materials.append(mat)

        # Rotate the plane
        self.manipulator.rotate_object(plane, 0, 90, 0)

    def add_light(
        self, location: tuple, type: str = "POINT", energy: float = 1000.0
    ) -> None:
        bpy.ops.object.light_add(type=type, location=location)
        bpy.context.active_object.data.energy = energy

    def add_lights(self):
        self.add_light((20, 0, 0), type="POINT", energy=1000.0)
        self.add_light((0, 20, 0), type="POINT", energy=1000.0)
        self.add_light(
            (0, -20, 0),
            type="POINT",
            energy=1000.0,
        )


class Extruder:
    def __init__(self, manipulator: ObjectManipulator):
        self.manipulator = manipulator

    def extrude_object(
        self, obj: bpy.types.Object, height: float, fill: bool = True
    ) -> None:
        self.manipulator.convert_to_mesh(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0, height)}
        )

        if fill:
            self.fill_face()

        self.manipulator.clean_up_mesh(obj)

    def extrude_body(self, body: bpy.types.Object) -> bool:
        try:
            self.extrude_object(body, height=1.3)
            # self.manipulator.add_subdivision_surface(body, levels=2, render_levels=1)
            self.manipulator.add_bevel(
                body,
                width=random.uniform(0.1, 0.2),
                segments=random.randint(10, 20),
            )
        except Exception as e:
            print(f"Error while extruding the body: {e}")
            return False
        return True

    def extrude_holes(self, hole: bpy.types.Object) -> bool:
        try:
            self.extrude_object(hole, height=1.3)
        except Exception as e:
            print(f"Error while extruding the holes: {e}")
            return False
        return True

    def extrude_engraving(self, engraving: bpy.types.Object) -> bool:
        try:
            self.extrude_object(engraving, height=0.25)
        except Exception as e:
            print(f"Error while extruding the engraving: {e}")
            return False
        return True

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()


class MaterialManager:
    def create_material(
        self, name: str, color: tuple, metallic: float = 0.5
    ) -> bpy.types.Material:
        material = bpy.data.materials.new(name=name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        return material

    def apply_material(
        self, obj: bpy.types.Object, material: bpy.types.Material
    ) -> None:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    def assign_material_to_vertex_group(
        self, obj: bpy.types.Object, group_name: str, material_index: int
    ):
        vertex_group = obj.vertex_groups.get(group_name)
        if not vertex_group:
            print(f"Vertex group '{group_name}' not found in object '{obj.name}'")
            return

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.object.vertex_group_set_active(group=vertex_group.name)
        bpy.ops.object.vertex_group_select()

        bpy.context.object.active_material_index = material_index
        bpy.ops.object.material_slot_assign()

        bpy.ops.object.mode_set(mode="OBJECT")

    def set_materials(self, body: bpy.types.Object):
        silver_material = self.create_material(
            name="Silver", color=(0.8, 0.8, 0.8, 1), metallic=1
        )
        dark_material = self.create_material(
            name="Dark", color=(0.2, 0.2, 0.2, 1), metallic=0.5
        )

        self.apply_material(body, silver_material)
        body.data.materials.append(dark_material)
        dark_material_index = len(body.material_slots) - 1

        self.assign_material_to_vertex_group(body, "engraving", dark_material_index)


class BlenderWorker:
    def __init__(self, path):
        self.importer = Importer(path)
        self.manipulator = ObjectManipulator()
        self.extruder = Extruder(self.manipulator)
        self.material_manager = MaterialManager()
        self.world_objects = WorldObjects()

    def main(self):
        imported_objects = self.importer.main()
        if imported_objects:
            body = bpy.data.collections["body"].objects[0]
            holes = bpy.data.collections["handles"].objects[0]
            engraving = bpy.data.collections["engraving"].objects[0]

            self.extruder.extrude_body(body)
            self.extruder.extrude_holes(holes)
            self.extruder.extrude_engraving(engraving)
            self.manipulator.add_holes(body, holes)
            self.manipulator.apply_engraving(body, engraving)
            self.material_manager.set_materials(body)
            self.manipulator.rotate_object(body, 90, 0, -90)
            self.world_objects.white_background()
            # self.world_objects.add_lights()


file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
blender_worker = BlenderWorker(file_path)
blender_worker.main()
