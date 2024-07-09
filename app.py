from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from dotenv import load_dotenv
import os, requests
from static.image_processing import DXFProcessor


app = Flask(__name__)
app.secret_key = 'pulapula'
app.debug = True

@app.route('/', methods=['GET', 'POST'])
def hello():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    data = request.form.to_dict()
    
    session['data'] = data
    return redirect(url_for('view_data'))

@app.route('/view-data')
def view_data():
    data = session.get('data', {})
    image_link = data.get('image_link', '')
    img_validity = get_image(image_link)

    response = {
        'data': data,
        'image_validity': img_validity
    }

    return jsonify(response)


def get_image(image_url: str):
    try:
        response = requests.head(image_url, allow_redirects=False)
        content_type = response.headers.get('Content-Type', '')

        if 'image/' in content_type:
            return True
        else:
            return False
    except requests.RequestException as e:
        return False, f"Error checking the URL: {e}"
    
def call_image_processing(data: dict):
    DXFProcessor(data)