import bpy, random
from mathutils import Vector


class Configurator:

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


class SVGImporter:
    def __init__(self, path):
        self.path = path
        self.config = Configurator()

    def main(self):
        self.config.apply()

        if self.import_file():
            self.process_object()

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

    def extrude_object(self, object, height: float, fill=True) -> None:
        self.convert_to_mesh(object)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0, height)}
        )

        if fill:
            self.fill_face()

        self.clean_up_mesh(object)

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

    def add_subdivision_surface(self, obj, levels: int, render_levels: int) -> None:
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels
        # bpy.ops.object.shade_smooth()

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()

        # self.clean_up_mesh()

    def fill_object(self, obj: bpy.types.Object) -> None:
        # Fill the top face
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.data.polygons[0].select = True
        self.fill_face()

        # Fill the bottom face
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.data.polygons[-1].select = True
        self.fill_face()

    def apply_boolean_modifier(
        self, target_obj: bpy.types.Object, holes: list[bpy.types.Object]
    ) -> None:
        self.set_active_object(target_obj)
        for hole in holes:
            bpy.ops.object.modifier_add(type="BOOLEAN")
            bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
            bpy.context.object.modifiers["Boolean"].object = hole
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.modifier_apply(modifier="Boolean")

    def add_bevel(self, obj, width: float, segments: int) -> None:
        self.set_active_object(obj)
        bpy.ops.object.modifier_add(type="BEVEL")
        bpy.context.object.modifiers["Bevel"].width = width
        bpy.context.object.modifiers["Bevel"].segments = segments

    def extrude_body(self) -> bool:
        try:
            body_obj = bpy.data.collections["body"].objects[0]
            self.extrude_object(body_obj, height=1.3, fill=True)
            self.add_bevel(
                body_obj,
                width=random.uniform(0.05, 0.15),
                segments=random.randint(5, 10),
            )
            # self.add_subdivision_surface(body_obj, levels=2, render_levels=1)
        except Exception as e:
            print(f"Error while extruding the body: {e}")
            return False
        return True

    def extrude_holes(self) -> bool:
        hole_obj = bpy.data.collections["handles"].objects[0]

        try:
            self.extrude_object(hole_obj, height=1.3, fill=True)
        except Exception as e:
            print(f"Error while extruding the holes: {e}")
            return False
        return True

    def add_thickness(self, obj, thickness: float) -> None:
        solidify = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
        solidify.thickness = thickness

    def extrude_engraving(self) -> bool:
        engraving = bpy.data.collections["engraving"].objects[0]

        try:
            self.extrude_object(engraving, height=0.5, fill=True)

        except Exception as e:
            print(f"Error while extruding the engraving: {e}")
            return False

        return True

    def add_holes(self) -> bool:
        try:
            body = bpy.data.collections["body"].objects[0]
            holes = [x for x in bpy.data.collections["handles"].objects]
            self.apply_boolean_modifier(body, holes)
            self.hide_collection(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def hide_collection(self, collection: bpy.types.Collection) -> None:
        for obj in collection:
            obj.hide_viewport = True

    def apply_engraving(self) -> bool:
        engraving = [x for x in bpy.data.collections["engraving"].objects]

        try:
            body = bpy.data.collections["body"].objects[0]
            self.apply_boolean_modifier(body, engraving)
            self.hide_collection(engraving)
        except Exception as e:
            print(f"Error while engraving: {e}")
            return False

    def create_material(self, name: str, color: tuple) -> bpy.types.Material:
        material = bpy.data.materials.new(name=name)
        material.diffuse_color = color
        return material

    def apply_material(
        self, obj: bpy.types.Object, material: bpy.types.Material
    ) -> None:
        if obj.data.materials:
            # assign to 1st material slot
            obj.data.materials[0] = material
        else:
            # no slots
            obj.data.materials.append(material)

    def add_light(
        self, location: tuple, type: str = "POINT", energy: float = 1000.0
    ) -> None:
        bpy.ops.object.light_add(type=type, location=location)
        bpy.context.active_object.data.energy = energy

    def set_materials(self):
        # Create materials
        silver_material = self.create_material(
            "Silver", (0.8, 0.8, 0.8, 1)
        )  # Silver color
        dark_material = self.create_material("Dark", (0.2, 0.2, 0.2, 1))  # Dark color

        # Apply materials
        body_obj = bpy.data.collections["body"].objects[0]
        self.apply_material(body_obj, silver_material)

        engraving_obj = bpy.data.collections["engraving"].objects[0]
        self.apply_material(engraving_obj, dark_material)

    def extrude(self) -> None:
        self.extrude_body()
        self.extrude_holes()
        self.extrude_engraving()

    def process_object(self):
        self.extrude()
        # self.add_holes()
        self.apply_engraving()
        # self.set_materials()
        # self.add_light((0, 0, 5))


svg_file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
svg_importer = SVGImporter(svg_file_path)
svg_importer.main()
