from build123d import *

with BuildPart() as p:
    Box(10, 10, 10)
    with BuildSketch(Plane.XY) as hole_sketch:
        Circle(2.5)
    extrude(amount=-10)

result_part = p.part
export_stl(result_part, 'output.stl')