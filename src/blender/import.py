import bpy, random
from mathutils import Vector


class Configurator:
    def __init__(self):
        self.apply()

    def apply(self) -> None:
        self.enable_addons()
        self.reset_scene()
        self.set_units_to_mm()

    def set_units_to_mm(self) -> None:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"

    def reset_scene(self) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Select all objects except the camera and light
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
    def set_active_object(self, obj) -> None:
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

    def clean_up_mesh(self, target_obj: object) -> None:
        self.set_active_object(target_obj)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as e:
            raise ValueError(f"Error while cleaning up the mesh: {e}")

    def apply_boolean_modifier(
        self, target_obj: bpy.types.Object, holes: bpy.types.Object
    ) -> None:
        self.set_active_object(target_obj)
        bpy.ops.object.modifier_add(type="BOOLEAN")
        bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
        bpy.context.object.modifiers["Boolean"].object = holes
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.modifier_apply(modifier="Boolean")

    def add_bevel(self, obj, width: float, segments: int) -> None:
        self.set_active_object(obj)
        bpy.ops.object.modifier_add(type="BEVEL")
        bpy.context.object.modifiers["Bevel"].width = width
        bpy.context.object.modifiers["Bevel"].segments = segments
        bpy.ops.object.modifier_apply(modifier="BEVEL")

    def add_subdivision_surface(self, obj, levels: int, render_levels: int) -> None:
        self.set_active_object(obj)
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels
        bpy.ops.object.modifier_apply(modifier="SUBSURF")

    def hide_collection(self, obj: bpy.types.Object) -> None:
        obj.hide_viewport = True


class Extruder:
    def __init__(self, manipulator: ObjectManipulator):
        self.manipulator = manipulator

    def extrude_object(self, obj: bpy.types.Object, height: float, fill=True) -> None:
        self.manipulator.convert_to_mesh(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0, height)}
        )

        if fill:
            self.fill_face()

        self.manipulator.clean_up_mesh(obj)

    def extrude_body(self) -> bool:
        try:
            body_obj = bpy.data.collections["body"].objects[0]
            self.extrude_object(body_obj, height=1.3, fill=True)
            self.manipulator.add_bevel(
                body_obj,
                width=random.uniform(0.05, 0.15),
                segments=random.randint(5, 10),
            )
            self.manipulator.add_subdivision_surface(
                body_obj, levels=1, render_levels=1
            )
        except Exception as e:
            print(f"Error while extruding the body: {e}")
            return False
        return True

    def extrude_holes(self) -> bool:
        try:
            hole_obj = bpy.data.collections["handles"].objects[0]
            self.extrude_object(hole_obj, height=1.3, fill=True)
        except Exception as e:
            print(f"Error while extruding the holes: {e}")
            return False
        return True

    def extrude_engraving(self) -> bool:
        try:
            engraving = bpy.data.collections["engraving"].objects[0]
            self.extrude_object(engraving, height=0.5, fill=True)
        except Exception as e:
            print(f"Error while extruding the engraving: {e}")
            return False
        return True

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()


class MaterialManager:
    def create_material(self, name: str, color: tuple) -> bpy.types.Material:
        material = bpy.data.materials.new(name=name)
        material.diffuse_color = color
        return material

    def apply_material(
        self, obj: bpy.types.Object, material: bpy.types.Material
    ) -> None:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    def set_materials(self):
        silver_material = self.create_material("Silver", (0.8, 0.8, 0.8, 1))
        dark_material = self.create_material("Dark", (0.2, 0.2, 0.2, 1))  # Dark color

        body_obj = bpy.data.collections["body"].objects[0]
        self.apply_material(body_obj, silver_material)

        engraving_obj = bpy.data.collections["engraving"].objects[0]
        self.apply_material(engraving_obj, dark_material)

    def add_light(
        self, location: tuple, type: str = "POINT", energy: float = 1000.0
    ) -> None:
        bpy.ops.object.light_add(type=type, location=location)
        bpy.context.active_object.data.energy = energy


class BlenderWorker:
    def __init__(self, path):
        self.importer = Importer(path)
        self.manipulator = ObjectManipulator()
        self.extruder = Extruder(self.manipulator)
        self.material_manager = MaterialManager()

    def main(self):
        imported_objects = self.importer.main()
        if imported_objects:
            self.extruder.extrude_body()
            self.extruder.extrude_holes()
            self.extruder.extrude_engraving()
            self.add_holes()
            self.apply_engraving()
            self.material_manager.set_materials()

    def add_holes(self) -> bool:
        try:
            body = bpy.data.collections["body"].objects[0]
            holes = bpy.data.collections["handles"].objects[0]
            self.manipulator.apply_boolean_modifier(body, holes)
            self.manipulator.hide_collection(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(self) -> bool:
        try:
            engraving = bpy.data.collections["engraving"].objects[0]
            body = bpy.data.collections["body"].objects[0]
            self.manipulator.apply_boolean_modifier(body, engraving)
            self.manipulator.hide_collection(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
        return True


file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
blender_worker = BlenderWorker(file_path)
blender_worker.main()
