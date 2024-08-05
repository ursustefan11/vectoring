import ezdxf, os, ezdxf, requests, math, numpy as np, svgwrite
from ezdxf.math import Matrix44
from io import BytesIO
from skimage import io, transform, filters, measure


class ImageProcessor:
    @staticmethod
    def process_image(image_url, target: str):
        response = requests.get(image_url)
        response.raise_for_status()
        img = io.imread(BytesIO(response.content), as_gray=True)
        img = transform.resize(img, (img.shape[0] * 2, img.shape[1] * 2), anti_aliasing=True)
        img = filters.gaussian(img, sigma=1.5)
        if   target == 'dxf': img = np.fliplr(img)
        elif target == 'svg': img = np.rot90(img)
        threshold_value = filters.threshold_otsu(img)
        binary = img > threshold_value
        contours = measure.find_contours(binary, level=0.8, fully_connected='high')
        smoothed_contours = [measure.approximate_polygon(contour, tolerance=2.0) for contour in contours]
        return smoothed_contours

class SVGProcessor:
    def __init__(self, data):
        self.data = data

    def get_svg_file(self):
        image_url = self.data.get('image_url')
        contours = ImageProcessor.process_image(image_url, target='svg')
        svg_content = self.create_svg(contours)
        svg_file_path = self.save_svg(svg_content)
        return svg_file_path

    def create_svg(self, contours):
        dwg = svgwrite.Drawing()
        for contour in contours:
            points = [(x, y) for x, y in contour]
            dwg.add(dwg.polyline(points, stroke='black', fill='none'))
        return dwg

    def save_svg(self, svg_content):
        svg_file_path = os.path.join(self.data.get('cwd'), f"{self.data.get('obj_name')}.svg")
        svg_content.saveas(svg_file_path)
        return svg_file_path


class DXFProcessor:
    def __init__(self, data: dict):
        self.doc       = ezdxf.new(dxfversion='R2018', units=ezdxf.units.MM)
        self.msp       = self.doc.modelspace()
        self.data      = data
        self.body      = self.get_body()
        self.handles   = self.get_handles()
        self.engraving = self.get_engraving()

    def get_dxf(self):
        dxf_directory = os.path.join(self.data['cwd'], "blender_files")
        dxf_path = os.path.join(dxf_directory, str(self.data['sku']) + '.dxf')
        if not os.path.exists(dxf_directory): os.makedirs(dxf_directory)
        self.doc.saveas(dxf_path, encoding='utf-8')
        return dxf_path

    def get_body(self):
        layer_name = 'body'
        self.add_layer(layer_name)
        if 'from_svg' in self.data:
            return self.get_body_from_svg()
        return self.msp.add_circle(center=(0, 0), radius=self.data.get('obj_size', 12)/2, dxfattribs={'layer': layer_name})
    
    def get_body_from_svg(self):
        svg_file_path = os.path.join(self.data['cwd'], f"{self.data['from_svg']}.svg")
        svg = ezdxf.readfile(svg_file_path)
        msp = svg.modelspace()

        for entity in msp:
            if entity.dxftype() == 'LINE':
                msp.add_lwpolyline(entity.get_points(), dxfattribs={'layer': 'body'})
        
        return svg

    def get_handles(self):
        diameter: float = 1.1

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
        dxfattribs = {'layer': layer_name, 'flags': 1}
        self.add_layer(layer_name)
        elements = []
    
        for contour in ImageProcessor.process_image(self.data.get("image_url"), target='dxf'):
            transformed_contour = [(y, -x) for x, y in contour]
            element = self.msp.add_lwpolyline(transformed_contour, dxfattribs=dxfattribs, close=True)
            elements.append(element)
    
        self.fit_engraving(elements)
        return elements

    def fit_engraving(self, engraving: list):
        max_square = self.get_max_square()
        handles_bbox = self.get_handle_bbox()
        max_rect = self.get_max_rect(max_square, handles_bbox)
        engraving_bbox = self.get_engraving_bbox(engraving)
        scaled = self.scale_engraving(engraving, max_rect, engraving_bbox)

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
            element.transform(Matrix44.scale(scale, scale, 0))
            element.transform(Matrix44.translate(translation_x, translation_y, 0))

    def add_layer(self, layer_name: str):
        if layer_name not in self.doc.layers:
            self.doc.layers.new(name=layer_name)

    def create_debug_rect(self, coords):
        x_min, y_min, x_max, y_max = coords
        points = [(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)]
        self.msp.add_lwpolyline(points, dxfattribs={"layer": 'body'},close=True)