import cv2
import numpy as np
import ezdxf
import os
from scipy.interpolate import splprep, splev
from ezdxf import units

def process_image(png_path: str):
    cwd = os.getcwd()
    img = cv2.imread(os.path.join(cwd, png_path), cv2.IMREAD_GRAYSCALE)
    img = cv2.flip(img, 0)
    
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    smooth = cv2.addWeighted(blur, 1.5, img, -0.5, 0)
    
    _, binary = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    filled_contours = [cnt for cnt in contours if cv2.contourArea(cnt) != 0]

    return filled_contours

def contours_to_dxf(png_path: str):
    layer_name = 'engraving'
    doc = ezdxf.new(dxfversion='R2018')
    doc.units = units.MM
    msp = doc.modelspace()
    layer = doc.layers.new(name=layer_name)
    contours = process_image(png_path)

    for contour in contours:
        points = [(point[0][0], point[0][1]) for point in contour]
        if points[0] != points[-1]:
            points.append(points[0])

        hatch = msp.add_hatch(color=7, dxfattribs={'layer': layer_name})
        hatch.paths.add_polyline_path(points)

    return doc

def add_body(doc, diameter: int = 12,):
    layer_name = 'body'
    msp = doc.modelspace()
    layer = doc.layers.new(name=layer_name)
    msp.add_circle(center=(0, 0), radius=diameter/2, dxfattribs={'layer': layer_name})

    return doc

def save_dxf(dxf_file: str):
    doc = contours_to_dxf(dxf_file)
    doc = add_body(doc)
    doc.saveas(filename="assets/output.dxf")

save_dxf('assets/coffee-cup.png')