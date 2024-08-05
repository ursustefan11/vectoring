from flask import request, send_file
from app import app
from app.controllers import Controller
import os

# TODO 
# SKU needs to be integer
# obj_size needs to be integer
@app.route('/', methods=['POST'])
def hello():
    expected_fields = {
        'image_url': None,
        'sku': '123456',
        'obj_type': 'necklace',
        'obj_size': 12,
        'from_svg': 'bone'
    }
    
    data = {field: request.form.get(field, default) for field, default in expected_fields.items()}
    controller = Controller(data)
    response = send_file(controller.get_archive())

    return response

@app.route('/register-shape', methods=['POST'])
def register_shape():
    expected_fields = {
        'image_url': None,
        'obj_name': 'bone',
    }
    data = {field: request.form.get(field, default) for field, default in expected_fields.items()}
    controller = Controller(data)
    response = controller.create_svg()

    return response