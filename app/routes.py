from flask import request, send_file
from app import app
from app.controllers import Controller
import os

@app.route('/', methods=['POST'])
def hello():
    expected_fields = {
        'image_url': None,
        'sku': '123456',
        'obj_type': 'necklace',
        'obj_size': 12,
    }
    
    data = {field: request.form.get(field, default) for field, default in expected_fields.items()}
    response = send_file(Controller(data)())

    # Stop the Docker container
    container_id = os.getenv('HOSTNAME')
    os.system(f'docker stop {container_id}')

    return response

# TODO 
# SKU needs to be integer
# obj_size needs to be integer


# @app.route('/view-data')
# def view_data():
#     response = {
#         'data': get_processed_image(session.get('data', {})),
#     }
#     return jsonify(response)