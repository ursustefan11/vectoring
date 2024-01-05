import cv2
import svgwrite

def image_to_svg(input_path, output_path):
    # Read the image
    image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)

    # Threshold the image
    _, thresh = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY_INV)

    # Find contours. Use cv2.findContours(...)[-2] to work with different OpenCV versions
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    # Create a new SVG file
    dwg = svgwrite.Drawing(output_path, profile='full')

    # Convert contours to SVG
    for contour in contours:
        # Ensure contour is of the right shape for svgwrite
        if len(contour) > 1:
            points = [(int(x), int(y)) for [x, y] in contour.squeeze()]
            dwg.add(dwg.polygon(points))

    # Save SVG file
    dwg.save()

# Replace 'input.jpg' and 'output.svg' with your file paths
image_to_svg('C:/Users/ursus/Downloads/test.png', 'output1.svg')
