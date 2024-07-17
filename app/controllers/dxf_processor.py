import cv2, ezdxf, os, ezdxf, numpy as np, requests, math
from ezdxf.math import Matrix44
from ezdxf import math as dxf_math


class DXFProcessor:
    def __init__(self, data: dict):
        self.doc       = ezdxf.new(dxfversion='R2010')
        self.doc.units = ezdxf.units.MM
        self.msp       = self.doc.modelspace()
        self.data      = data
        self.engraving = self.get_engraving()
    
    def process_image(self):
        if not self.data.get('image_url') and 'input' in self.data:
            img = cv2.imread(os.path.join(os.getcwd(), self.data['input']), cv2.IMREAD_GRAYSCALE)
        else:
            response = requests.get(self.data.get('image_url'))
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
        img = cv2.flip(img, 0)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        img = cv2.GaussianBlur(img, (3, 3), 0)  # Increased kernel size for smoother effect

        kernel = np.ones((1, 1), np.uint8)
        img = cv2.erode(img, kernel, iterations=1)
        img = cv2.dilate(img, kernel, iterations=1)

        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        smoothed_contours = []
        for cnt in contours:
            epsilon = 0.000125 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if cv2.contourArea(approx) != 0:
                smoothed_contours.append(approx)

        return smoothed_contours
    
    def get_engraving(self):
        layer_name = 'engraving'
        dxfattribs={'layer': layer_name, 'flags': 1}
        self.add_layer(layer_name)
        elements = []
        
        for contour in self.process_image():
            points = contour.reshape(-1, 2).tolist()
            points = [(point[0][0], point[0][1]) for point in contour]
            if points[0] != points[-1]:
                points.append(points[0])
            
            element = self.msp.add_lwpolyline(points, dxfattribs=dxfattribs, close=True)
            elements.append(element)
        
        return elements

    def __call__(self):
        dxf_directory = os.path.join(self.data['cwd'], "blender_files")
        dxf_path = os.path.join(dxf_directory, str(self.data['sku']) + '.dxf')
        if not os.path.exists(dxf_directory): os.makedirs(dxf_directory)
        
        return self.save_dxf(dxf_path)

    def add_layer(self, layer_name: str):
        if layer_name not in self.doc.layers:
            self.doc.layers.new(name=layer_name)

    def save_dxf(self, file_path: str):
        self.doc.audit()
        self.doc.saveas(file_path, encoding='utf-8')
        return file_path