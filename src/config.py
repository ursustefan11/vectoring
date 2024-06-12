import bpy, math

class Config:
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
        bpy.context.scene.cycles.device = "GPU"
        bpy.context.scene.cycles.samples = 100
        bpy.context.scene.cycles.preview_samples = 50

    @staticmethod
    def set_camera_settings() -> None:
        bpy.ops.object.camera_add(
            enter_editmode=False, align="VIEW", location=(50, 0, 0)
        )
        camera = bpy.context.object
        camera.data.lens = 50
        camera.data.clip_start = 0.1
        camera.data.clip_end = 1000
        camera.rotation_euler[0] = math.radians(90)
        camera.rotation_euler[1] = 0
        camera.rotation_euler[2] = math.radians(90)
        bpy.context.scene.camera = camera

    @staticmethod
    def set_world_settings() -> None:
        bpy.context.scene.world.use_nodes = True
        world = bpy.context.scene.world
        world.use_nodes = True
        bg = world.node_tree.nodes["Background"]
        bg.inputs[0].default_value = (0, 0, 0, 1)