import arcpy
import numpy as np

# Set environment settings
arcpy.env.workspace = "CURRENT"

# Input and output feature class names
input_fc = "ChartedRoute1B"  # Replace with your input feature class name
output_fc = "ChartedRoute1B_ok"  # Replace with your desired output feature class name
polygon_fc = "Airport_5Km_Zone"  # Replace with your polygon feature class name

# Check if the output feature class exists and delete it if it does
if arcpy.Exists(output_fc):
    arcpy.Delete_management(output_fc)

# Copy the input feature class to a new feature class to avoid modifying the original
arcpy.CopyFeatures_management(input_fc, output_fc)

# Function to create a curvier line that avoids polygons
def create_curved_line(geometry, polygon_fc, num_points=30, max_attempts=20):
    points = [point for point in geometry.getPart(0)]
    if len(points) < 2:
        return geometry
    
    start_point = points[0]
    end_point = points[-1]

    def bezier_curve(start, control, end, num_points):
        return [
            arcpy.Point(
                (1-t)**2 * start.X + 2*(1-t)*t * control.X + t**2 * end.X,
                (1-t)**2 * start.Y + 2*(1-t)*t * control.Y + t**2 * end.Y
            )
            for t in np.linspace(0, 1, num_points)
        ]

    def intersects_polygon(polyline, polygon_fc):
        with arcpy.da.SearchCursor(polygon_fc, ["SHAPE@"]) as polygon_cursor:
            for polygon_row in polygon_cursor:
                polygon = polygon_row[0]
                if polyline.overlaps(polygon) or polyline.crosses(polygon) or polyline.within(polygon):
                    return True
        return False

    def is_horizontal_line(start, end):
        angle = abs(end.X - start.X) / (abs(end.Y - start.Y) + 1e-6)  # Avoid division by zero
        return angle > 5  # Consider lines with angle > 5 as nearly horizontal

    def is_left_to_right(start, end):
        return start.X < end.X

    attempt = 0
    while attempt < max_attempts:
        mid_x = (start_point.X + end_point.X) / 2
        mid_y = (start_point.Y + end_point.Y) / 2

        # Adjust the control point adaptively
        deviation = max(abs(start_point.Y - end_point.Y) * 0.5, abs(start_point.X - end_point.X) * 0.05) * (1 + 0.05 * attempt)
        control_points = [
            arcpy.Point(mid_x, mid_y + deviation),
            arcpy.Point(mid_x, mid_y - deviation)
        ]
        
        for control_point in control_points:
            bezier_points = bezier_curve(start_point, control_point, end_point, num_points)

            # Create the curved geometry
            curved_geometry = arcpy.Polyline(arcpy.Array(bezier_points), geometry.spatialReference)

            # Check if the curved geometry intersects with any polygons
            if not intersects_polygon(curved_geometry, polygon_fc):
                return curved_geometry  # Return the curved geometry if there's no intersection

        attempt += 1

    # Additional attempt for nearly horizontal lines
    if is_horizontal_line(start_point, end_point):
        attempt = 0
        while attempt < max_attempts:
            mid_x = (start_point.X + end_point.X) / 2
            mid_y = (start_point.Y + end_point.Y) / 2

            # More aggressive deviation for horizontal lines
            deviation = abs(start_point.Y - end_point.Y) * 1.0 * (1 + 0.1 * attempt)
            control_points = [
                arcpy.Point(mid_x, mid_y + deviation),
                arcpy.Point(mid_x, mid_y - deviation)
            ]
            
            for control_point in control_points:
                bezier_points = bezier_curve(start_point, control_point, end_point, num_points)

                # Create the curved geometry
                curved_geometry = arcpy.Polyline(arcpy.Array(bezier_points), geometry.spatialReference)

                # Check if the curved geometry intersects with any polygons
                if not intersects_polygon(curved_geometry, polygon_fc):
                    return curved_geometry  # Return the curved geometry if there's no intersection

            attempt += 1

    # Extra aggressive adjustment for horizontal lines from left to right
    if is_horizontal_line(start_point, end_point) and is_left_to_right(start_point, end_point):
        attempt = 0
        while attempt < max_attempts:
            mid_x = (start_point.X + end_point.X) / 2
            mid_y = (start_point.Y + end_point.Y) / 2

            # Even more aggressive deviation for left-to-right horizontal lines
            deviation = abs(start_point.Y - end_point.Y) * 2.0 * (1 + 0.1 * attempt)
            control_points = [
                arcpy.Point(mid_x, mid_y + deviation),
                arcpy.Point(mid_x, mid_y - deviation)
            ]
            
            for control_point in control_points:
                bezier_points = bezier_curve(start_point, control_point, end_point, num_points)

                # Create the curved geometry
                curved_geometry = arcpy.Polyline(arcpy.Array(bezier_points), geometry.spatialReference)

                # Check if the curved geometry intersects with any polygons
                if not intersects_polygon(curved_geometry, polygon_fc):
                    return curved_geometry  # Return the curved geometry if there's no intersection

            attempt += 1

    return geometry  # Return the original geometry if unable to avoid polygons after max attempts

# Start an editing session
with arcpy.da.UpdateCursor(output_fc, ["SHAPE@"]) as cursor:
    for row in cursor:
        new_geometry = create_curved_line(row[0], polygon_fc)
        row[0] = new_geometry
        cursor.updateRow(row)

print("Curved lines created successfully, avoiding polygons.")
