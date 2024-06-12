import bpy, os, sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import Config
from importer import Importer
from object import ObjectManipulator, Extruder
from world import WorldObjects
from material import MaterialManager

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
            self.manipulator.add_holes(body, holes)
            self.manipulator.apply_engraving(body, engraving)
            # self.material_manager.set_materials(body)
            # self.manipulator.rotate_object(body, 90, 0, -90)
            self.world_objects.create_backdrop_plane()
            self.world_objects.add_lights()

            self.change_settings()

    def change_settings(self):
        self.config.set_render_settings()
        self.config.set_camera_settings()
        self.config.set_world_settings()