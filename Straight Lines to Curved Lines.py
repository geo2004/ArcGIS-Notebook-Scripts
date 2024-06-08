import arcpy
import numpy as np

# Set environment settings
arcpy.env.workspace = "CURRENT"

# Input and output feature class names
input_fc = "KHM_Origin_GenerateOriginDestinationLinks"  # Replace with your input feature class name
output_fc = "KHM_Origin_GenerateOriginDestinationLinks_curved"  # Replace with your desired output feature class name

# Check if the output feature class exists and delete it if it does
if arcpy.Exists(output_fc):
    arcpy.Delete_management(output_fc)

# Copy the input feature class to a new feature class to avoid modifying the original
arcpy.CopyFeatures_management(input_fc, output_fc)

# Function to create a curved line from a straight line using a quadratic Bezier curve
def create_curved_line(geometry, num_points=20):
    points = [point for point in geometry.getPart(0)]
    if len(points) < 2:
        return geometry
    
    start_point = points[0]
    end_point = points[-1]
    
    # Midpoint calculation
    mid_x = (start_point.X + end_point.X) / 2
    mid_y = (start_point.Y + end_point.Y) / 2
    control_point = arcpy.Point(mid_x, mid_y + abs(start_point.Y - end_point.Y) / 2)  # Raise the midpoint to create a curve
    
    # Generate points along the quadratic Bezier curve
    bezier_points = []
    for t in np.linspace(0, 1, num_points):
        x = (1-t)**2 * start_point.X + 2*(1-t)*t * control_point.X + t**2 * end_point.X
        y = (1-t)**2 * start_point.Y + 2*(1-t)*t * control_point.Y + t**2 * end_point.Y
        bezier_points.append(arcpy.Point(x, y))
    
    curved_geometry = arcpy.Polyline(arcpy.Array(bezier_points), geometry.spatialReference)
    return curved_geometry

# Start an editing session
with arcpy.da.UpdateCursor(output_fc, ["SHAPE@"]) as cursor:
    for row in cursor:
        new_geometry = create_curved_line(row[0])
        row[0] = new_geometry
        cursor.updateRow(row)

print("Curved lines created successfully.")
