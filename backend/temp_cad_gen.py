from build123d import *

# Create a 2 inch cube
# build123d works in millimeters by default, so we use the IN constant (25.4) 
# to ensure the dimensions are physically 2 inches.
side_length = 2 * IN

with BuildPart() as p:
    # Box creates a centered cube by default
    Box(side_length, side_length, side_length)

result_part = p.part

# Export the final part to STL
export_stl(result_part, 'output.stl')