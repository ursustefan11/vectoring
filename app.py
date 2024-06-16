import bpy, random, math, bmesh, os
from mathutils import Vector
from typing import Optional


class Config:
    def apply(self) -> None:
        self.reset_scene()
        self.set_units_to_mm()

    def reset_scene(self) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        for obj in bpy.context.scene.objects:
            obj.select_set(True)

        bpy.ops.object.delete(use_global=False, confirm=False)

        for collection in bpy.data.collections:
            bpy.data.collections.remove(collection)

    def set_units_to_mm(self) -> None:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"

    @staticmethod
    def set_render_settings() -> None:
        bpy.context.scene.render.engine          = "CYCLES"
        bpy.context.scene.cycles.device          = "GPU"
        bpy.context.scene.cycles.samples         = 100
        bpy.context.scene.cycles.preview_samples = 50

    @staticmethod
    def set_camera_settings() -> None:
        bpy.ops.object.camera_add(
            enter_editmode=False, align="VIEW", location=(60, 0, 0)
        )
        camera = bpy.context.object
        camera.data.lens = 50
        bpy.context.scene.camera = camera
        ObjectManipulator.point_object_to_position(camera, (0, 0, 0))

    @staticmethod
    def set_world_settings() -> None:
        bpy.context.scene.world.use_nodes = True
        env_texture = bpy.context.scene.world.node_tree.nodes.new('ShaderNodeTexEnvironment')
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, 'assets', 'studio_small_01_4k.hdr')
        env_texture.image = bpy.data.images.load(image_path)        


class Importer:
    def import_file(self, path: str) -> bool:
        Config().apply()

        bpy.ops.import_scene.dxf(filepath=path)

        return self.organize_imported_objects(bpy.context.scene.objects)

    def organize_imported_objects(self, imports: list[bpy.types.Object]) -> None:
        for obj in imports:
            new = obj.name.split("_")[0].lower()
            obj.name = new


class MaterialManager:
    @staticmethod
    def create_material(
        name     : str,
        color    : tuple,
        metallic : float = 0.5,
        roughness: float = 0.5
    ) -> bpy.types.Material:
        
        material = bpy.data.materials.new(name=name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        return material

    @staticmethod
    def apply_material(
        obj     : bpy.types.Object,
        material: bpy.types.Material
    ) -> None:
        
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    @staticmethod
    def assign_material_to_vertex_group(
        obj           : bpy.types.Object,
        group_name    : str,
        material_index: int
    ) -> None:
        
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

    def create_silver(self):
        m = self.create_material("Silver", color=(0.8, 0.8, 0.8, 1), metallic=1.0, roughness=0.18)
        return m

    def create_engraving(self):
        m = self.create_material("engraving", color=(0.0, 0.0, 0.0, 1), metallic=0.2, roughness=0.4)
        return m

    def create_cutout(self):
        m = self.create_material("Cutout", color=(0.2, 0.2, 0.2, 1), metallic=0.0, roughness=1.0)
        return m

    def set_materials(self, body: bpy.types.Object) -> None:
        silver = self.create_silver()
        engraving = self.create_engraving()
        cutout = self.create_cutout()

        self.apply_material(body, silver)
        body.data.materials.append(engraving)

        engraving_index = len(body.material_slots) - 1
        body.data.materials.append(cutout)
        cutout_index = len(body.material_slots) - 1

        self.assign_material_to_vertex_group(body, "engraving", engraving_index)
        self.assign_material_to_vertex_group(body, "holes", cutout_index)


class WorldObjects:
    def create_backdrop_plane(self, object: bpy.types.Object):
        ref_h = object.dimensions[1] * 0.8
        bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -ref_h))
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

        ObjectManipulator.rotate_object(plane, 0, 0, 90)
        plane_material = MaterialManager.create_material("BG", color=(0.974967, 0.5, 0.5, 1))
        MaterialManager.apply_material(plane, plane_material)

    def add_light(self,
        name    : str,
        location: tuple,
        type    : str = "POINT",
        energy  : float = 1000.0,
        size    : float = 1.0,
    ) -> bpy.types.Object:
        
        bpy.ops.object.light_add(type=type, location=location)
        light             = bpy.context.active_object
        light.name        = name
        light.data.energy = energy
        if type == "AREA":
            light.data.size = size
        return light

    def add_lights(self, facing_object: bpy.types.Object):
        up = self.add_light("up", (-10, 0, 100), type="AREA", energy=2e6, size=800)
        ObjectManipulator.point_object_to_position(up, ((facing_object.location)))

        back = self.add_light("back", (-100, 0, 250), type="AREA", energy=2e6, size=30)
        ObjectManipulator.point_object_to_position(back, (0, 0, 0))


class ObjectManipulator:
    @staticmethod
    def set_origin_to_geometry(obj):
        local_bbox_center = 0.125 * sum((Vector(b) for b in obj.bound_box), Vector())
        obj.location = obj.location - local_bbox_center
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")

    def set_active_obj(self, obj: bpy.types.Object) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    def convert_to_mesh(self, obj: bpy.types.Object) -> None:
        self.set_active_obj(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.curve.select_all(action="SELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.convert(target="MESH")

    def clean_up_mesh(self, target_obj: bpy.types.Object) -> None:
        self.set_active_obj(target_obj)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as e:
            raise ValueError(f"Error while cleaning up the mesh: {e}")

    def add_bevel(self,
        obj: bpy.types.Object,
        width: float,
        segments: int
    ) -> None:
        
        self.set_active_obj(obj)
        bpy.ops.object.modifier_add(type="BEVEL")
        bpy.context.object.modifiers["Bevel"].width = width
        bpy.context.object.modifiers["Bevel"].segments = segments
        self.apply_modifier(obj, "Bevel")

    def apply_boolean_modifier(self,
        obj              : bpy.types.Object,
        target           : bpy.types.Object,
        vertex_group_name: str = "",
        incl_z           : bool = False
    ) -> None:
        
        self.set_active_obj(obj)

        original_vertices = set(tuple(v.co) for v in obj.data.vertices)

        bpy.ops.object.modifier_add(type="BOOLEAN")
        bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
        bpy.context.object.modifiers["Boolean"].object = target
        self.apply_modifier(obj, "Boolean")

        if len(vertex_group_name):
            new_vertices = []
            for v in obj.data.vertices:
                if tuple(v.co) not in original_vertices and (v.co if incl_z else v.co.z != 0):
                    new_vertices.append(v.index)
            self.assign_vertices_to_group(obj, new_vertices, vertex_group_name)

    def apply_modifier(self, obj: bpy.types.Object, modifier_name: str) -> None:
        override                     = bpy.context.copy()
        override["object"]           = obj
        override["active_object"]    = obj
        override["selected_objects"] = [obj]
        bpy.ops.object.modifier_apply(modifier=modifier_name)

    def assign_vertices_to_group(self,
        obj           : bpy.types.Object,
        vertex_indices: list,
        group_name    : str
    ) -> None:
        if group_name not in obj.vertex_groups:
            vertex_group = obj.vertex_groups.new(name=group_name)
        else:
            vertex_group = obj.vertex_groups[group_name]

        vertex_group.add(vertex_indices, 1.0, "ADD")

    def add_subdivision_surface(self,
        obj          : bpy.types.Object,
        levels       : int,
        render_levels: int,
        subdiv_type  : str = "SIMPLE",
        apply        : bool = True,
    ) -> None:
        self.set_active_obj(obj)

        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].subdivision_type = subdiv_type
        bpy.context.object.modifiers["Subdivision"].levels           = levels
        bpy.context.object.modifiers["Subdivision"].render_levels    = render_levels
        
        if apply: self.apply_modifier(obj, "Subdivision")

    def delete_object(self, obj: bpy.types.Object) -> None:
        obj_name = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)

    def remove_collections(self) -> None:
        for collection in bpy.data.collections:
            if not collection.objects:
                bpy.data.collections.remove(collection)

    def hide_object(self, obj: bpy.types.Object) -> None:
        obj.hide_set(True)

    def add_holes(self, body: bpy.types.Object, holes: bpy.types.Object) -> bool:
        try:
            self.apply_boolean_modifier(body, holes, vertex_group_name="holes", incl_z=True)
            self.hide_object(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(self, body: bpy.types.Object, engraving: bpy.types.Object) -> bool:
        try:
            self.apply_boolean_modifier(body, engraving, vertex_group_name="engraving")
            self.hide_object(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
        return True

    def add_chain_comp(self, hole: bpy.types.Object, parent: bpy.types.Object) -> None:
        bpy.ops.mesh.primitive_torus_add(
            align          = 'WORLD',
            location       = hole.location,
            rotation       = (0, 0, 0),
            major_radius   = 0.56,
            minor_radius   = 0.1,
            major_segments = 48,
            minor_segments = 24
        )
        torus = bpy.context.object
        torus.parent = parent

    @staticmethod
    def rotate_object(
        object: bpy.types.Object,
        rx    : float,
        ry    : float,
        rz    : float,
    ) -> None:
        object.rotation_euler[0] = math.radians(rx)
        object.rotation_euler[1] = math.radians(ry)
        object.rotation_euler[2] = math.radians(rz)

    @staticmethod
    def point_object_to_position(obj: bpy.types.Object, target_position: Optional[Vector]):
        if not isinstance(target_position, Vector):
            target_position = Vector(target_position)
        
        direction = obj.location - target_position
        
        rot_quat = direction.to_track_quat('Z', 'Y')
        
        obj.rotation_euler = rot_quat.to_euler()


class Extruder:
    def __init__(self, manipulator: ObjectManipulator):
        self.manipulator = manipulator

    def extrude_object(self,
        obj   : bpy.types.Object,
        height: float,
        fill  : bool = True
    ) -> None:
        """Extrudes a given object by a specified height."""
        self.manipulator.set_active_obj(obj)

        if obj.type != "MESH":
            self.manipulator.convert_to_mesh(obj)
 
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, height)})

        if fill: self.fill_face()
        self.manipulator.clean_up_mesh(obj)

    def extrude(self, 
        obj        : bpy.types.Object,
        height     : float,
        bevel      : bool = False,
        subdivision: bool = False
    ) -> bool:
        """Extrudes a given object and optionally adds bevel and subdivision surface."""
        try:
            self.extrude_object(obj, height)
            
            if bevel:
                self.manipulator.add_bevel(
                    obj,
                    width=random.uniform(0.15, 0.25),
                    segments=random.randint(10, 20),
                )

            if subdivision:
                self.manipulator.add_subdivision_surface(obj, levels=1, render_levels=1, subdiv_type="SIMPLE")
        except Exception as e:
            print(f"Error while extruding the object: {e}")
            return False
        return True

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()


class BlenderWorker:
    def __init__(self):
        self.manipulator      = ObjectManipulator()
        self.extruder         = Extruder(self.manipulator)
        self.material_manager = MaterialManager()
        self.world_objects    = WorldObjects()

    def main(self, file_path: str):
        Importer().import_file(file_path)

        body = bpy.data.objects.get("body")
        holes = bpy.data.objects.get("handles")
        engraving = bpy.data.objects.get("engraving")

        self.change_settings()
        self.world_objects.add_lights(body)
        self.world_objects.create_backdrop_plane(body)

        self.extruder.extrude(body, height=0.8, bevel=True, subdivision=False)
        self.extruder.extrude(holes, height=1.3, subdivision=False)
        self.extruder.extrude(engraving, height=0.25)
        
        self.manipulator.add_chain_comp(holes, body)
        self.manipulator.apply_engraving(body, engraving)
        self.manipulator.add_holes(body, holes)

        self.material_manager.set_materials(body)
        self.manipulator.set_origin_to_geometry(body)
        self.manipulator.rotate_object(body, 110, 0, -75)

        # self.remove_unwanted(holes, engraving)
            
    # def remove_unwanted(self, holes, engraving):
    #     self.manipulator.delete_object(holes)
    #     self.manipulator.delete_object(engraving)
    #     self.manipulator.remove_collections()


    def change_settings(self):  
        Config().set_render_settings()
        Config().set_camera_settings()
        Config().set_world_settings()

file_path = r"C:\GitHub\vectoring\assets\testfile-necklace.dxf"
blender_worker = BlenderWorker()
blender_worker.main(file_path)