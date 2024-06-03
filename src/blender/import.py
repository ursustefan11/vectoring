import bpy
from mathutils import Vector


class Configurator:

    def config(self) -> None:
        self.enable_addons()
        self.reset_scene()
        self.set_units_to_mm()

    def set_units_to_mm(self) -> None:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"

    def reset_scene(self) -> None:
        # Switch to object mode and delete all objects
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False, confirm=False)

        # Remove all collections
        for collection in bpy.data.collections:
            bpy.data.collections.remove(collection)

    def create_collections(self) -> list[bpy.types.Collection]:
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

    def enable_addons(self) -> None:
        if not bpy.ops.preferences.addon_enable(module="io_import_dxf"):
            bpy.ops.preferences.addon_install(module="io_import_dxf")


class SVGImporter:
    def __init__(self, path):
        self.path = path

    def run(self):
        Configurator().config()
        if self.import_file():
            self.extrude_body()

    def import_file(self) -> bool:
        collections = bpy.context.collections
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

            # Center the object's geometry
            bbox_center = 0.125 * sum((Vector(b) for b in obj.bound_box), Vector())
            obj.location = obj.location - bbox_center

    def set_active_object(self, obj) -> None:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    def convert_to_mesh(self, obj: bpy.types.Object = None) -> None:
        if obj is None:
            obj = bpy.context.view_layer.objects.active
        if obj and obj.type == "CURVE":
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
            self.fill_face(object)

    def clean_up_mesh(self) -> None:
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.remove_doubles()

    def add_subdivision_modifier(self, levels: int = 2, render_levels: int = 1) -> None:
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.fill()
        self.clean_up_mesh()

    def fill_object(self, obj: bpy.types.Object) -> None:
        # Fill the top face
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.data.polygons[0].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        self.fill_face()

        # Fill the bottom face
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.data.polygons[-1].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        self.fill_face()

    def extrude_body(self) -> bool:
        try:
            body_obj = bpy.data.collections["body"].objects[0]
            self.extrude_object(body_obj, height=1.3, fill=True)

            self.add_holes()
        except Exception as e:
            print(e)
            return False
        return True

    def add_holes(self) -> bool:
        try:
            body_obj = bpy.data.collections["body"].objects[0]
            hole_obj = bpy.data.collections["handles"].objects[0]

            self.extrude_object(hole_obj, height=1.3)

            # self.set_active_object(body_obj)
            body_obj.select_set(True)
            # The boolean operation code is commented out and can be uncommented if needed
            # self.apply_boolean_modifier(body_obj, hole_obj)

            bpy.ops.object.select_all(action="DESELECT")
        except Exception as e:
            print(f"Could not add hole {hole_obj.name}, {hole_obj.type}")
            print(e)
            return False
        return True

    def apply_boolean_modifier(
        self, target_obj: bpy.types.Object, tool_obj: bpy.types.Object
    ) -> None:
        bpy.ops.object.modifier_add(type="BOOLEAN")
        bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
        bpy.context.object.modifiers["Boolean"].object = tool_obj
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.modifier_apply(modifier="Boolean")


svg_file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
svg_importer = SVGImporter(svg_file_path)
svg_importer.run()
