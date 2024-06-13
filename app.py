import bpy, random, math, bmesh, os
from mathutils import Vector


class Config:
    def apply(self) -> None:
        # self.enable_addons()
        self.reset_scene()
        self.set_units_to_mm()
        # self.set_render_engine_to_gpu()

    def set_units_to_mm(self) -> None:
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"

    def reset_scene(self) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        for obj in bpy.context.scene.objects:
            obj.select_set(True)

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

    @staticmethod
    def set_render_settings() -> None:
        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.view_layer.update()
        bpy.context.scene.cycles.device = "GPU"
        bpy.context.scene.cycles.samples = 100
        bpy.context.scene.cycles.preview_samples = 50

    @staticmethod
    def set_camera_settings() -> None:
        bpy.ops.object.camera_add(
            enter_editmode=False, align="VIEW", location=(60, 0, 0)
        )
        camera = bpy.context.object
        camera.data.lens = 50
        ObjectManipulator.point_object_to_position(camera, (0, 0, 0))
        bpy.context.scene.camera = camera

    @staticmethod
    def set_world_settings() -> None:
        
        bpy.context.scene.world.use_nodes = True
        env_texture = bpy.context.scene.world.node_tree.nodes.new('ShaderNodeTexEnvironment')
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, 'assets', 'studio_small_01_4k.hdr')
        env_texture.image = bpy.data.images.load(image_path)
        


class Importer:
    def __init__(self, path):
        self.path = path

    def main(self) -> bool:
        return self.import_file()

    def import_file(self) -> bool:
        config = Config()
        config.apply()
        collections = config.create_collections()
        bpy.ops.import_scene.dxf(filepath=self.path)
        imported_svg = bpy.context.scene.objects

        if imported_svg:
            self.organize_imported_objects(imported_svg, collections)
            return True
        else:
            raise ValueError("No objects were imported. Check the DXF file.")

    def organize_imported_objects(
        self,
        imported_svg: bpy.types.Object,
        collections: bpy.types.Collection
    ) -> None:
        
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


class MaterialManager:
    @staticmethod
    def create_material(
        name: str,
        color: tuple,
        metallic: float = 0.5,
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
        obj: bpy.types.Object,
        material: bpy.types.Material
    ) -> None:
        
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    @staticmethod
    def assign_material_to_vertex_group(
        obj: bpy.types.Object,
        group_name: str,
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
        m = self.create_material(name="Silver", color=(0.8, 0.8, 0.8, 1), metallic=1.0, roughness=0.18)

        # noise_texture = m.node_tree.nodes.new('ShaderNodeTexNoise')
        # noise_texture.inputs['Scale'].default_value = 10.0
        # noise_texture.inputs['Detail'].default_value = 2.0
        # noise_texture.inputs['Distortion'].default_value = 0.0

        # color_ramp = m.node_tree.nodes.new('ShaderNodeValToRGB')
        # color_ramp.color_ramp.elements[0].position = 0.1
        # color_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        # color_ramp.color_ramp.elements[1].position = 0.9
        # color_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

        # m.node_tree.links.new(noise_texture.outputs['Color'], color_ramp.inputs['Fac'])

        # principled_bsdf = m.node_tree.nodes['Principled BSDF']
        # m.node_tree.links.new(color_ramp.outputs['Color'], principled_bsdf.inputs['Roughness'])

        return m

    def create_engraving(self):
        m = self.create_material(name="engraving", color=(0.0, 0.0, 0.0, 1), metallic=0.2, roughness=0.4)
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bump_node = m.node_tree.nodes.new('ShaderNodeBump')

        m.node_tree.links.new(bump_node.outputs['Normal'], bsdf.inputs['Normal'])
        return m

    def create_cutout(self):
        m = self.create_material(
            name="Cutout", color=(0.2, 0.2, 0.2, 1), metallic=0.0, roughness=1.0
        )
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
    def __init__(self):
        self.manipulator = ObjectManipulator()

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

        self.manipulator.rotate_object(plane, 0, 0, 90)
        plane_material = MaterialManager.create_material(name="BG", color=(0.974967, 0.5, 0.5, 1))
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

    def add_lights(self, facing_object: bpy.types.Object):
        s = 100

        # l = self.add_light("left", (150, -150, 0), type="AREA", energy=2e6, size=s)
        # ObjectManipulator.point_object_to_position(l, facing_object.location)

        up = self.add_light("up", (-10, 0, 100), type="AREA", energy=2e6, size=800)
        ObjectManipulator.point_object_to_position(up, ((facing_object.location)))

        # r = self.add_light("right", (-10, 0, 0), type="AREA", energy=1e6, size=10)
        # ObjectManipulator.point_object_to_position(r, -facing_object.location)

        back = self.add_light("back", (-100, 0, 250), type="AREA", energy=2e6, size=30)
        ObjectManipulator.point_object_to_position(back, (0, 0, 0))

        # f = self.add_light("f", (150, 150, 50), type="AREA", energy=1e6, size=s)
        # ObjectManipulator.point_object_to_position(f, facing_object.location)


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

    def add_bevel(
        self,
        obj: bpy.types.Object,
        width: float,
        segments: int
    ) -> None:
        
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
        incl_z: bool = False
    ) -> None:
        
        self.set_active_object(obj)

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
        override = bpy.context.copy()
        override["object"] = obj
        override["active_object"] = obj
        override["selected_objects"] = [obj]
        bpy.ops.object.modifier_apply(modifier=modifier_name)

    def assign_vertices_to_group(
        self,
        obj: bpy.types.Object,
        vertex_indices: list,
        group_name: str
    ) -> None:
        if group_name not in obj.vertex_groups:
            vertex_group = obj.vertex_groups.new(name=group_name)
        else:
            vertex_group = obj.vertex_groups[group_name]

        vertex_group.add(vertex_indices, 1.0, "ADD")

    def add_subdivision_surface(
        self,
        obj: bpy.types.Object,
        levels: int,
        render_levels: int,
        apply: bool = True
    ) -> None:
        self.set_active_object(obj)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels
        if apply:
            self.apply_modifier(obj, "Subdivision")
        bpy.ops.object.shade_flat()

    def delete_object_and_collection(self, obj: bpy.types.Object) -> None:
        obj_name = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)
        if obj_name in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections[obj_name])

    def hide_object(self, obj: bpy.types.Object) -> None:
        obj.hide_set(True)

    def add_holes(self, body, holes) -> bool:
        try:
            self.apply_boolean_modifier(body, holes, vertex_group_name="holes", incl_z=True)
            self.hide_object(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(
        self,
        body: bpy.types.Object,
        engraving: bpy.types.Object
    ) -> bool:
        try:
            self.apply_boolean_modifier(body, engraving, vertex_group_name="engraving")
            self.hide_object(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
        return True

    @staticmethod
    def rotate_object(
        object: bpy.types.Object,
        rx: float,
        ry: float,
        rz: float,
    ) -> None:
        object.rotation_euler[0] = math.radians(rx)
        object.rotation_euler[1] = math.radians(ry)
        object.rotation_euler[2] = math.radians(rz)

    @staticmethod
    def point_object_to_position(obj, target_position):
        if not isinstance(target_position, Vector):
            target_position = Vector(target_position)
        
        direction = obj.location - target_position
        
        rot_quat = direction.to_track_quat('Z', 'Y')
        
        obj.rotation_euler = rot_quat.to_euler()

class Extruder:
    def __init__(self, manipulator: ObjectManipulator):
        self.manipulator = manipulator

    def extrude_object(
        self,
        obj: bpy.types.Object,
        height: float,
        fill: bool = True
    ) -> None:
        
        if obj.type != "MESH":
            self.manipulator.convert_to_mesh(obj)
 
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, height)})

        if fill: self.fill_face()
        self.manipulator.clean_up_mesh(obj)

    def extrude_body(self, body: bpy.types.Object) -> bool:
        try:
            self.extrude_object(body, height=0.9)
            self.manipulator.add_bevel(
                body,
                width=random.uniform(0.15, 0.25),
                segments=random.randint(10, 20),
            )
            self.manipulator.add_subdivision_surface(body, levels=1, render_levels=1)
        except Exception as e:
            print(f"Error while extruding the body: {e}")
            return False
        return True

    def extrude_holes(self, hole: bpy.types.Object) -> bool:
        try:
            self.extrude_object(hole, height=1.3)
            self.manipulator.add_subdivision_surface(hole, levels=1, render_levels=1)
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


class BlenderWorker:
    def __init__(self, path):
        self.config = Config()
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
            self.manipulator.apply_engraving(body, engraving)
            self.manipulator.add_holes(body, holes)
            self.material_manager.set_materials(body)
            self.manipulator.rotate_object(body, 110, 0, -75)
            self.world_objects.create_backdrop_plane(body)
            self.world_objects.add_lights(body)

            self.manipulator.delete_object_and_collection(holes)
            self.manipulator.delete_object_and_collection(engraving)

            self.change_settings()

    def change_settings(self):  
        self.config.set_render_settings()
        self.config.set_camera_settings()
        self.config.set_world_settings()

file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
blender_worker = BlenderWorker(file_path)
blender_worker.main()