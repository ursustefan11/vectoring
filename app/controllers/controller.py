import os, subprocess, json, zipfile
from flask import current_app
from . import DXFProcessor


class Controller:
    def __init__(self, data) -> None:
        self.data = data

    def __call__(self):
        return self.get_archive()

    def get_archive(self):
        data = self.get_processed_image(self.data)
        dxf_file = data.get('dxf_file')
        output = data.get('output')
        sku = data.get('sku')

        if current_app.debug:
            return output

        archive_dir = os.path.join(self.data.get('cwd'), 'archive')
        if not os.path.exists(archive_dir): os.makedirs(archive_dir)

        archive_path = os.path.join(archive_dir, f"{sku}.zip")

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(dxf_file, arcname=os.path.basename(dxf_file))
            archive.write(output, arcname=os.path.basename(output))
        return archive_path

    def get_processed_image(self, data: dict):
        data['cwd'] = os.path.join(os.getcwd(), "app", "static")
        data['output'] = os.path.join(data['cwd'], 'blender_files', f'{data["sku"]}.png')
        data['dxf_file'] = DXFProcessor(data)()

        self.write_json(data)
        self.start_blender(data)

        return data

    def start_blender(self, data):
        script_path = os.path.join(data["cwd"], "blenderworker.py")
        
        if os.getenv('BLENDER_URL'):
            command = ["blender", "-b", "-P", script_path, "--log-level", "0"]
        else:
            blender_path = os.getenv('blender', r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe")
            command = [blender_path, "--background", "--python", script_path]
        
        subprocess.run(command)

    def write_json(self, data):
        json_path = os.path.join(data['cwd'], 'blender_files', 'temp.json')
        with open(json_path, 'w') as f:
            json.dump(self.data, f)