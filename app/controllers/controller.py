import os, subprocess, json, zipfile
from flask import current_app
from . import DXFProcessor, SVGProcessor


class Controller:
    def __init__(self, data):
        data['cwd'] = os.path.join(os.getcwd(), "app", "static")
        self.data = data

    def get_archive(self):
        self.get_dxf_and_image()
        return self.create_archive()

    def get_dxf_and_image(self):
        self.data['output'] = os.path.join(self.data['cwd'], 'blender_files', f'{self.data["sku"]}.png')
        self.data['dxf_file'] = DXFProcessor(self.data).get_dxf()

    def create_archive(self):
        dxf_file = self.data.get('dxf_file')
        output   = self.data.get('output')
        sku      = self.data.get('sku')

        if current_app.debug:
            return output
        self.start_blender()
        archive_dir = os.path.join(self.data.get('cwd'), 'archive')
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        archive_path = os.path.join(archive_dir, f"{sku}.zip")

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(dxf_file, arcname=os.path.basename(dxf_file))
            archive.write(output, arcname=os.path.basename(output))
        return archive_path

    def create_svg(self):
        svg = SVGProcessor(self.data)
        response = svg.get_svg_file()
        return response

    def start_blender(self):
        self.write_json()
        script_path = os.path.join(self.data["cwd"], "blenderworker.py")

        if os.getenv('BLENDER_URL'):
            command = ["blender", "-b", "-P", script_path, "--log-level", "0"]
        else:
            blender_path = os.getenv('blender', r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe")
            command = [blender_path, "--background", "--python", script_path]
        subprocess.run(command)

    def write_json(self):
        json_path = os.path.join(self.data['cwd'], 'blender_files', 'temp.json')
        with open(json_path, 'w') as f:
            json.dump(self.data, f)