from build123d import *

# Dimensions
# The request is for a 2-inch sphere.
# Diameter = 2 inches -> Radius = 1 inch.
# CAD and STL files typically interpret 1 unit as 1 millimeter.
# To ensure the physical size is correct (2 inches), we convert to mm.
radius_mm = 1.0 * 25.4

with BuildPart() as p:
    # Create a sphere centered at (0,0,0)
    Sphere(radius=radius_mm)

result_part = p.part

# Export to STL
export_stl(result_part, 'output.stl')