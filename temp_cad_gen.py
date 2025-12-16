from build123d import *

# --- Gear Parameters ---
num_teeth = 24
module = 2              # Scales the size of the gear
pressure_angle = 20     # Standard pressure angle in degrees
gear_thickness = 10     # Thickness of the toothed section
hub_diameter = 20       # Diameter of the central hub
hub_height = 14         # Total height of the hub (must be >= gear_thickness)
bore_diameter = 8       # Diameter of the shaft hole

with BuildPart() as p:
    # 1. Create the 2D Gear Profile
    with BuildSketch() as gear_sketch:
        InvoluteGear(
            tooth_count=num_teeth,
            module=module,
            pressure_angle=pressure_angle
        )
    
    # 2. Extrude the Gear Teeth
    # We extrude symmetrically (both=True) to keep (0,0,0) as the center
    extrude(amount=gear_thickness, both=True)

    # 3. Create and Extrude the Hub
    # The hub reinforces the center of the gear
    with BuildSketch() as hub_sketch:
        Circle(radius=hub_diameter / 2)
    
    # Extrude the hub (Union is default mode)
    extrude(amount=hub_height, both=True)

    # 4. Cut the Bore (Shaft Hole)
    with BuildSketch() as bore_sketch:
        Circle(radius=bore_diameter / 2)
    
    # Subtract material for the hole
    extrude(amount=hub_height + 1, both=True, mode=Mode.SUBTRACT)

    # 5. Finishing Touches (Chamfer the bore)
    # We find the circular edges that match our bore radius
    bore_edges = p.edges().filter_by(GeomType.CIRCLE).filter_by(
        lambda e: abs(e.radius - bore_diameter / 2) < 0.001
    )
    
    # Apply a small chamfer to allow easy shaft insertion
    chamfer(bore_edges, length=0.5)

# Assign the final part to the required variable
result_part = p.part

# Export to STL
export_stl(result_part, 'output.stl')