from build123d import *

# Create a sphere with a diameter of 2 inches (50.8 mm)
result_part = Sphere(50.8/2)

# Export the part to an STL file
export_stl(result_part, 'output.stl')