from build123d import *

# Create the wheel part
with BuildPart() as p:
    # Main wheel body: Diameter 10mm -> Radius 5mm, Width 4mm
    Cylinder(radius=5, height=4)
    
    # Axle hole: Diameter 3mm -> Radius 1.5mm
    Cylinder(radius=1.5, height=4, mode=Mode.SUBTRACT)
    
    # Robust Edge Selection:
    # 1. Filter for only circular edges (ignores vertical seam lines on cylinders)
    # 2. Separate into outer rim (radius ~5) and inner hole (radius ~1.5)
    circular_edges = p.edges().filter_by(GeomType.CIRCLE)
    
    # Select outer edges (radius > 4mm)
    outer_rim_edges = circular_edges.filter_by(lambda e: e.radius > 4.0)
    
    # Select inner hole edges (radius < 2mm)
    inner_hole_edges = circular_edges.filter_by(lambda e: e.radius < 2.0)
    
    # Apply operations if edges are found
    if outer_rim_edges:
        chamfer(outer_rim_edges, length=0.5)
        
    if inner_hole_edges:
        chamfer(inner_hole_edges, length=0.2)

# Assign to result_part
result_part = p.part

# Export to STL
export_stl(result_part, 'output.stl')