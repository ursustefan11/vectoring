from mathutils import Vector
import bpy, sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from config import Config

class Importer:
    def __init__(self, path):
        self.path = path

    def main(self) -> bool:
        return self.import_file()

    def import_file(self) -> bool:
        config = Config()
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