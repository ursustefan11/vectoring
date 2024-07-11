from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import os, requests, subprocess, json
from static.image_processing import DXFProcessor


app = Flask(__name__)
app.secret_key = 'pulapula'
app.debug = True

@app.route('/', methods=['GET', 'POST'])
def hello():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    expected_fields = {
        'image_url': None,
        'sku': '123456',
    }
    
    data = {field: request.form.get(field, default) for field, default in expected_fields.items()}
    
    session['data'] = data
    return redirect(url_for('view_data'))

@app.route('/view-data')
def view_data():
    response = {
        'data': get_processed_image(session.get('data', {})),
    }
    return jsonify(response)

def get_processed_image(data: dict):
    data['obj_type'] = 'necklace'
    data['obj_size'] = 12
    data['cwd'] = os.path.join(os.getcwd(), "static")
    data['output'] = os.path.join(data['cwd'], 'blender_files', f'{data["sku"]}.png')
    data['dxf_file'] = DXFProcessor(data)()

    write_json(data)
    start_blender(data)

    return data

def start_blender(data):
    script_path = os.path.join(data["cwd"], "blenderworker.py")
    blender_path = os.getenv('BLENDER_PATH', r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")

    subprocess.run([blender_path, "--background", "--python", script_path])

def write_json(data: dict):
    json_path = os.path.join(data['cwd'], 'blender_files', 'temp.json')
    with open(json_path, 'w') as f:
        json.dump(data, f)