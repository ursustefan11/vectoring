import bpy


class SVGImporter:
    def __init__(self, svg_path, extrude_depth=0.1):
        self.svg_path = svg_path
        self.obj_name = "Object"
        self.extrude_depth = extrude_depth

        self.run()

    def run(self):
        self.import_svg()
        self.extrude_object()

    def import_svg(self):
        bpy.ops.import_curve.svg(filepath=self.svg_path)

    def extrude_object(self):
        if self.obj_name in bpy.data.objects:
            obj = bpy.data.objects[self.obj_name]
            bpy.context.view_layer.objects.active = obj
            if obj.type == 'CURVE':
                obj.data.extrude = self.extrude_depth
            else:
                print(f"Object {self.obj_name} is not a curve object.")
        else:
            print(f"No object named {self.obj_name} found in the scene.")

svg_file_path = r"C:\GitHub\Auto Vectoring DXF\assets\testfile.svg"

svg_importer = SVGImporter(svg_file_path)

print("SVG Import and Processing Complete")