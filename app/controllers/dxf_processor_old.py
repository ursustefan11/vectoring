import cv2, ezdxf, os, ezdxf, numpy as np, requests, math
from ezdxf.math import Matrix44
from ezdxf import math as dxf_math


class DXFProcessor:
    def __init__(self, data: dict):
        self.doc       = ezdxf.new(dxfversion='R2010')
        self.doc.units = ezdxf.units.MM
        self.msp       = self.doc.modelspace()
        self.data      = data
        self.body      = self.get_body()
        self.handles   = self.get_handles()
        self.engraving = self.get_engraving()

    def __call__(self):
        dxf_directory = os.path.join(self.data['cwd'], "blender_files")
        dxf_path = os.path.join(dxf_directory, str(self.data['sku']) + '.dxf')
        if not os.path.exists(dxf_directory): os.makedirs(dxf_directory)
        
        return self.save_dxf(dxf_path)
    
    # def process_image(self):
    #     if not self.data.get('image_url') and 'input' in self.data:
    #         img = cv2.imread(os.path.join(os.getcwd(), self.data['input']), cv2.IMREAD_GRAYSCALE)
    #     else:
    #         response = requests.get(self.data.get('image_url'))
    #         image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    #         img = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
    #     img = cv2.flip(img, 0)
    #     img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    #     img = cv2.GaussianBlur(img, (5, 5), 0)
    #     _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    #     contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    #     filled_contours = [cnt for cnt in contours if cv2.contourArea(cnt) != 0]

    #     return filled_contours

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

    def get_body(self):
        layer_name = 'body'
        self.add_layer(layer_name)
        
        return self.msp.add_circle(center=(0, 0), radius=self.data.get('obj_size', 12)/2, dxfattribs={'layer': layer_name})

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

    def is_smooth_curve(self, points, angle_threshold=0.1, curvature_threshold=0.1):
        if len(points) < 4:
            return False

        def calculate_curvature(p1, p2, p3):
            # Calculate the curvature using the circumscribed circle's radius
            a = math.dist(p1, p2)
            b = math.dist(p2, p3)
            c = math.dist(p3, p1)
            s = (a + b + c) / 2
            try:
                radius = (a * b * c) / (4 * math.sqrt(s * (s - a) * (s - b) * (s - c)))
                return 1 / radius
            except ZeroDivisionError:
                return float('inf')

        total_angle = 0
        total_curvature = 0
        valid_segments = 0

        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            p3 = points[(i + 2) % len(points)]
            v1 = dxf_math.Vec2(p2[0] - p1[0], p2[1] - p1[1])
            v2 = dxf_math.Vec2(p3[0] - p2[0], p3[1] - p2[1])

            if v1.magnitude == 0 or v2.magnitude == 0: continue

            try:
                angle = v1.angle_between(v2)
                curvature = calculate_curvature(p1, p2, p3)
                total_angle += abs(angle)
                total_curvature += curvature
                valid_segments += 1
            except ZeroDivisionError: continue

        if valid_segments == 0: return False

        average_angle = total_angle / valid_segments
        average_curvature = total_curvature / valid_segments

        return average_angle < angle_threshold and average_curvature < curvature_threshold
    
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
            
            if self.is_smooth_curve(points):
                element = self.msp.add_spline(points, dxfattribs=dxfattribs)
            else:
                element = self.msp.add_lwpolyline(points, dxfattribs=dxfattribs, close=True)
            elements.append(element)
        
        self.fit_engraving(elements)
        return elements

    def fit_engraving(self, engraving: list):
        max_square = self.get_max_square()
        handles_bbox = self.get_handle_bbox()
        max_rect = self.get_max_rect(max_square, handles_bbox)
        engraving_bbox = self.get_engraving_bbox(engraving)
        scaled = self.scale_engraving(engraving, max_rect, engraving_bbox)

    def create_debug_rect(self, coords):
        x_min, y_min, x_max, y_max = coords
        points = [(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)]
        self.msp.add_lwpolyline(points, dxfattribs={"layer": 'body'},close=True)

    def get_max_square(self):
        square_side_length = self.body.dxf.radius * math.sqrt(2)
        x_c, y_c, _ = self.body.dxf.center
        half_side_length = square_side_length / 2
        bounding_box = (x_c - half_side_length, y_c - half_side_length,
                        x_c + half_side_length, y_c + half_side_length)

        return bounding_box

    def get_engraving_bbox(self, elements):
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for element in elements:
            if hasattr(element, 'vertices') and callable(element.vertices):
                for point in element.vertices():
                    min_x, min_y = min(min_x, point[0]), min(min_y, point[1])
                    max_x, max_y = max(max_x, point[0]), max(max_y, point[1])

        return (min_x, min_y, max_x, max_y)
    
    def get_handle_bbox(self):
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        bbox = []
        for handle in self.handles:
            min_x, min_y = min(min_x, handle.dxf.center.x - handle.dxf.radius), min(min_y, handle.dxf.center.y - handle.dxf.radius)
            max_x, max_y = max(max_x, handle.dxf.center.x + handle.dxf.radius), max(max_y, handle.dxf.center.y + handle.dxf.radius)
            bbox.append((min_x, min_y, max_x, max_y))

        return bbox
    
    def get_max_rect(self, max_square, handles_bbox):
        min_x, min_y, max_x, max_y = max_square

        for handle_bbox in handles_bbox:
            h_min_x, h_min_y, h_max_x, h_max_y = handle_bbox

            if h_max_x > min_x and h_min_x < max_x:
                if h_min_y < max_y and h_max_y > max_y:
                    max_y = h_min_y
                elif h_max_y > min_y and h_min_y < min_y:
                    min_y = h_max_y

            if h_max_y > min_y and h_min_y < max_y:
                if h_min_x < max_x and h_max_x > max_x:
                    max_x = h_min_x
                elif h_max_x > min_x and h_min_x < min_x:
                    min_x = h_max_x

        return (min_x, min_y, max_x, max_y)
    
    def scale_engraving(self, elements, max_rect, engraving_bbox):
        scale_x = (max_rect[2] - max_rect[0]) / (engraving_bbox[2] - engraving_bbox[0])
        scale_y = (max_rect[3] - max_rect[1]) / (engraving_bbox[3] - engraving_bbox[1])
        scale = 0.95 * min(scale_x, scale_y)
    
        center_max_rect_x = (max_rect[2] + max_rect[0]) / 2
        center_max_rect_y = (max_rect[3] + max_rect[1]) / 2
    
        center_engraving_scaled_x = ((engraving_bbox[2] + engraving_bbox[0]) / 2) * scale
        center_engraving_scaled_y = ((engraving_bbox[3] + engraving_bbox[1]) / 2) * scale
    
        translation_x = center_max_rect_x - center_engraving_scaled_x
        translation_y = center_max_rect_y - center_engraving_scaled_y
    
        for element in elements:
            element.transform(Matrix44.scale(scale, scale, scale))
            element.transform(Matrix44.translate(translation_x, translation_y, 0))

    def add_layer(self, layer_name: str):
        if layer_name not in self.doc.layers:
            self.doc.layers.new(name=layer_name)

    def save_dxf(self, file_path: str):
        self.doc.audit()
        self.doc.saveas(file_path, encoding='utf-8')
        return file_path


# def main(data):
#     processor = DXFProcessor(data)
#     processor.save_dxf()

# if __name__ == "__main__":
#     cwd = os.path.join(os.getcwd(), "assets")
#     obj_data = {
#         "obj_type": "necklace",
#         "obj_size": 12,
#         "sku": "123456",
#         "input": f"{os.path.join(cwd, "cook.jpg")}",
#         "output": "assets/cook.dxf"
#     }
#     main(obj_data)