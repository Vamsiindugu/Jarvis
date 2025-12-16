from build123d import *

# Create a part context
with BuildPart() as p:
    # Create a 10x10x10 cube centered at (0,0,0)
    Box(10, 10, 10)
    
    # Create a hole (cylinder) with 5mm diameter (2.5mm radius)
    # The cylinder is aligned with the Z-axis by default
    # Mode.SUBTRACT removes the cylinder geometry from the existing cube
    Cylinder(radius=2.5, height=10, mode=Mode.SUBTRACT)

# Assign the final object to result_part
result_part = p.part

# Export the result to an STL file
export_stl(result_part, 'output.stl')