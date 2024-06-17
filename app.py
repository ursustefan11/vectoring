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
            bpy.data.objects.remove(obj, do_unlink=True)

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
            if isinstance(obj.data, bpy.types.Curve) and "engraving" not in obj.name:
                obj.data.resolution_u = 64


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
    def set_geometry_to_origin(obj):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
    
    @staticmethod
    def set_origin_to_geometry(obj):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

    def move_object(self, obj: bpy.types.Object, x: float, y: float, z: float) -> None:
        obj.location = (x, y, z)

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
        subdiv = bpy.context.object.modifiers["Subdivision"]
        subdiv.subdivision_type = subdiv_type
        subdiv.levels           = levels
        subdiv.render_levels    = render_levels
        
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
            # self.delete_object(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(self, body: bpy.types.Object, engraving: bpy.types.Object) -> bool:
        try:
            self.apply_boolean_modifier(body, engraving, vertex_group_name="engraving")
            self.delete_object(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
            
        return True

    def add_chain_comp(self, hole: bpy.types.Object, body: bpy.types.Object) -> None:
        chain_link = self.create_chain_link(hole, body)
        self.assign_parent_material_to_child(body, chain_link)

        necklace = self.create_necklace(chain_link)
        # self.assign_parent_material_to_child(chain_link, necklace)

    def create_chain_path(self, chain_link: bpy.types.Object) -> bpy.types.Object:
        r = 15
        bpy.ops.curve.primitive_bezier_circle_add(radius=r, location=chain_link.location)
        curve = bpy.context.object
        curve.name = "droplet_path"
        curve.parent = chain_link.parent
        spline = curve.data.splines[0]

        point = spline.bezier_points[3]
        point.co.y -= 10 * r
        point.handle_left_type = 'ALIGNED'
        point.handle_right_type = 'ALIGNED'
        point.handle_left = point.co + Vector((r/4, 0, 0))
        point.handle_right = point.co + Vector((-r/4, 0, 0))

        bpy.context.view_layer.objects.active = curve
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
        bbox_height = curve.dimensions[1]
        curve.location = chain_link.location + Vector((0, bbox_height/2, 0))

        return curve
    
    def create_necklace(self, chain_link: bpy.types.Object) -> bpy.types.Object:
        chain_path = self.create_chain_path(chain_link)
        chain = self.create_chain()

        # chain.parent = chain_path.parent
        print(f'chain parent after assignment: {chain.parent}') 

        self.set_active_obj(chain_path)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        self.set_active_obj(chain)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        bpy.ops.object.modifier_add(type='ARRAY')
        chain.modifiers["Array"].fit_type = 'FIT_CURVE'
        chain.modifiers["Array"].curve = chain_path

        bpy.ops.object.empty_add(type='PLAIN_AXES', location=chain.location)
        empty = bpy.context.object

        chain.modifiers["Array"].use_object_offset = True
        chain.modifiers["Array"].offset_object = empty
        chain.modifiers["Array"].relative_offset_displace = [0.75, 0, 0]

        self.set_active_obj(chain)
        bpy.ops.object.modifier_add(type='CURVE')
        curve_modifier = chain.modifiers["Curve"]
        curve_modifier.object = chain_path
        curve_modifier.deform_axis = 'NEG_X'

        bpy.ops.object.select_all(action='DESELECT')
        empty.select_set(True)
        bpy.ops.transform.rotate(value=3.14159/2, orient_axis='X')

        return chain
    
    def create_chain(self):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.32,
            minor_radius=0.09,
            major_segments=48,
            minor_segments=33)
        
        torus = bpy.context.object
        torus.name = "chain"
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(torus.data)
        
        for vertex in mesh.verts:
            if vertex.co.x > 0:
                vertex.co.x += 0.5
        
        bmesh.update_edit_mesh(torus.data)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return torus


    def create_chain_link(self, hole: bpy.types.Object, body: bpy.types.Object) -> bpy.types.Object:
        relative_location = body.location - hole.location

        if abs(relative_location.x) > abs(relative_location.y):
            axis = Vector((1, 0, 0))
        else:
            axis = Vector((0, 1, 0))
        
        fudge_factor = 0.56 * 1.77
        torus_location = (body.location - hole.location) - axis*fudge_factor

        bpy.ops.mesh.primitive_torus_add(
            align          = 'WORLD',
            location       = -torus_location,
            rotation       = (0, math.pi/2, 0),
            major_radius   = 0.7,
            minor_radius   = 0.14,
            major_segments = 48,
            minor_segments = 24
        )
        torus = bpy.context.object
        torus.parent = body
        bpy.ops.object.shade_smooth()
        self.delete_object(hole)
        return torus

    def assign_parent_material_to_child(self, parent: bpy.types.Object, child: bpy.types.Object) -> None:
        child.data.materials.clear()

        for material in parent.data.materials:
            child.data.materials.append(material)

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

        # self.change_settings()
        # self.world_objects.add_lights(body)
        # self.world_objects.create_backdrop_plane(body)

        self.extruder.extrude(body, height=0.8, bevel=True, subdivision=False)
        self.extruder.extrude(holes, height=0.8, subdivision=False)
        self.extruder.extrude(engraving, height=0.25)
        
        self.manipulator.apply_engraving(body, engraving)
        self.manipulator.add_holes(body, holes)
        self.manipulator.set_origin_to_geometry(holes)
        self.manipulator.set_origin_to_geometry(body)
        self.material_manager.set_materials(body)
        self.manipulator.add_chain_comp(holes, body)

        # self.manipulator.move_object(body, 0, 0, 0)
        # self.manipulator.rotate_object(body, 110, 0, -75)

    def change_settings(self):  
        Config().set_render_settings()
        Config().set_camera_settings()
        Config().set_world_settings()

file_path = r"C:\GitHub\vectoring\assets\testfile-necklace.dxf"
blender_worker = BlenderWorker()
blender_worker.main(file_path)