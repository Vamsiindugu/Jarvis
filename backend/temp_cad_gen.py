from build123d import *
import numpy as np

# Create the main part
with BuildPart() as p:
    # 1. Chassis Body
    # Lifted up so wheels can touch the ground (Z=0)
    # Chassis dimensions: 60mm long, 30mm wide, 12mm tall
    with Locations((0, 0, 14)): 
        Box(60, 30, 12)
        # Fillet the vertical corners for a smoother look
        fillet(p.edges().filter_by(Axis.Z), radius=5)

    # 2. Cabin / Upper Deck
    # Placed on top of the chassis
    with Locations((0, 0, 20 + 2)): # 14 (center of chassis) + 6 (half chassis) + ~height
        # Adjusting Z: Chassis top is at 14 + 6 = 20. 
        # Cabin height 10, so center is at 20 + 5 = 25.
        pass
    
    with Locations((-5, 0, 24)):
        Box(30, 20, 8)
        # Chamfer the top edges of the cabin
        chamfer(p.edges(Select.LAST).filter_by(Axis.Z), length=2)

    # 3. Wheels
    # Wheel Specs
    wheel_radius = 8
    wheel_width = 6
    wheel_x_offset = 20
    wheel_y_offset = 19  # 15 (half chassis) + 4 (clearance/half wheel)
    axle_height = 8      # Radius of wheel is 8, so center is at Z=8
    
    wheel_locations = [
        (wheel_x_offset, wheel_y_offset, axle_height),
        (wheel_x_offset, -wheel_y_offset, axle_height),
        (-wheel_x_offset, wheel_y_offset, axle_height),
        (-wheel_x_offset, -wheel_y_offset, axle_height),
    ]

    with Locations(wheel_locations):
        # Rotate cylinders to align with Y axis (Wheels rolling along X)
        with Locations(Rotation(90, 0, 0)):
            Cylinder(radius=wheel_radius, height=wheel_width)

    # 4. Axles
    # Simple cylinders running through the chassis to connect wheels
    with Locations([(wheel_x_offset, 0, axle_height), (-wheel_x_offset, 0, axle_height)]):
        with Locations(Rotation(90, 0, 0)):
            Cylinder(radius=2, height=wheel_y_offset * 2)

    # 5. Front Sensor (Robotic Eye)
    # Placed on the front face of the chassis
    # Chassis X extends to +30
    with Locations((30, 0, 14)):
        # Sensor mounting block
        Box(2, 12, 6)
        # Lens
        with Locations((1, 0, 0)):
            with Locations(Rotation(0, 90, 0)):
                Cylinder(radius=2.5, height=2)

# Assign the final part to the variable 'result_part'
result_part = p.part

# Export to STL
export_stl(result_part, 'output.stl')