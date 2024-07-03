import cv2, numpy as np, ezdxf, math, os
import ezdxf
from scipy.interpolate import splprep, splev
from ezdxf.math import Matrix44


class DXFProcessor:
    def __init__(self, data: dict):
        self.doc = ezdxf.new(dxfversion='R2018')
        self.doc.units = ezdxf.units.MM
        self.msp = self.doc.modelspace()
        self.data = data

        self.body = self.get_body()
        self.handles = self.get_handles()
        self.engraving = self.get_engraving()

    def process_image(self):
        img = cv2.imread(os.path.join(os.getcwd(), self.data['input']), cv2.IMREAD_GRAYSCALE)
        img = cv2.flip(img, 0)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        blur = cv2.GaussianBlur(img, (9, 9), 0)
        smooth = cv2.addWeighted(blur, 1.5, img, -0.5, 0)
        _, binary = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        filled_contours = [cnt for cnt in contours if cv2.contourArea(cnt) != 0]
        return filled_contours
    
    def simplify_contour(self):
        contours = self.process_image()
        simplified_contours = []
        epsilon_factor = 0.00025

        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            epsilon = epsilon_factor * perimeter
            simplified_contour = cv2.approxPolyDP(contour, epsilon, True)
            simplified_contours.append(simplified_contour)

        return simplified_contours

    def add_layer(self, layer_name: str):
        if layer_name not in self.doc.layers:
            self.doc.layers.new(name=layer_name)

    def get_body(self):
        layer_name = 'body'
        self.add_layer(layer_name)
        return self.msp.add_circle(center=(0, 0), radius=self.data['obj_size']/2, dxfattribs={'layer': layer_name})

    def get_handles(self):
        diameter: float = 1.3

        if not self.body:
            print("No entities found in the 'body' layer.")
            return
        
        layer_name = 'handles'
        self.add_layer(layer_name)
        center = self.body.dxf.center
        radius = self.body.dxf.radius
        handle_y_position = center.y + radius - diameter

        if self.data['obj_type'] == "necklace":
            return [self.msp.add_circle(center=(center.x, handle_y_position), radius=diameter/2, dxfattribs={'layer': layer_name})]
        elif self.data['obj_type'] == "bracelet":
            return [self.msp.add_circle(center=(center.x - radius + diameter, center.y), radius=diameter/2, dxfattribs={'layer': layer_name}),
            self.msp.add_circle(center=(center.x + radius - diameter, center.y), radius=diameter/2, dxfattribs={'layer': layer_name})]

    def get_engraving(self):
        layer_name = 'engraving'
        self.add_layer(layer_name)
        contours = self.simplify_contour()
        elements = []
        for contour in contours:
            points = [(point[0][0], point[0][1]) for point in contour]
            if points[0] != points[-1]:
                points.append(points[0])
            line = self.msp.add_lwpolyline(points, dxfattribs={'layer': layer_name})
            elements.append(line)

        return elements
    
    def fit_engraving_inside_body(self):
        body_center = self.body.dxf.center
        body_radius = self.body.dxf.radius

        square_side_length = body_radius * (2 ** 0.5)

        square_bbox = (body_center.x - square_side_length / 2, body_center.y - square_side_length / 2,
                    body_center.x + square_side_length / 2, body_center.y + square_side_length / 2)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for element in self.engraving:
            if hasattr(element, 'vertices') and callable(element.vertices):
                for point in element.vertices():
                    min_x, min_y = min(min_x, point[0]), min(min_y, point[1])
                    max_x, max_y = max(max_x, point[0]), max(max_y, point[1])

        engraving_bbox = (min_x, min_y, max_x, max_y)

        scale_x = (square_bbox[2] - square_bbox[0]) / (engraving_bbox[2] - engraving_bbox[0])
        scale_y = (square_bbox[3] - square_bbox[1]) / (engraving_bbox[3] - engraving_bbox[1])
        scale = min(scale_x, scale_y)

        translation_x = body_center.x - ((engraving_bbox[2] + engraving_bbox[0]) / 2) * scale
        translation_y = body_center.y - ((engraving_bbox[3] + engraving_bbox[1]) / 2) * scale

        for element in self.engraving:
            element.transform(Matrix44.scale(scale, scale, scale))
            element.transform(Matrix44.translate(translation_x, translation_y, 0))

    def save_dxf(self):
        self.doc.saveas(self.data['output'])


def main(data):
    processor = DXFProcessor(data)
    processor.fit_engraving_inside_body()
    processor.save_dxf()

if __name__ == "__main__":
    obj_data = {
        "obj_type": "necklace",
        "obj_size": 12,
        "input": "assets/squirrel.jpg",
        "output": "assets/squirrel.dxf"
    }
    main(obj_data)