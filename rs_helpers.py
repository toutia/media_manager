import pyrealsense2 as rs
import numpy as np
import math

def get_intrinsics(pipeline_profile):
    """
    Retrieve camera intrinsics for the depth stream.
    
    Returns:
        dict: A dictionary with camera intrinsics: 'fx', 'fy', 'cx', 'cy'.
    """


    # Get the depth stream intrinsics
    depth_sensor = pipeline_profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()  # Depth scale in meters
    print("Depth Scale is: ", depth_scale)

    # Get stream intrinsics
    depth_stream = pipeline_profile.get_stream(rs.stream.depth)
    intrinsics = depth_stream.as_video_stream_profile().get_intrinsics()

 

    # Convert intrinsics to a dictionary
    intrinsics_dict = {
        'fx': intrinsics.fx,
        'fy': intrinsics.fy,
        'cx': intrinsics.ppx,
        'cy': intrinsics.ppy,
        'width': intrinsics.width,
        'height': intrinsics.height,
    }
    return intrinsics_dict



def get_spatial_coordinates(u, v, depth_value, intrinsics):
    """
    Calculate spatial coordinates of an object in the camera's coordinate system.
    
    Args:
        u (int): Pixel x-coordinate (horizontal position).
        v (int): Pixel y-coordinate (vertical position).
        depth_value (float): Depth value (Z) at pixel (u, v).
        intrinsics (dict): Camera intrinsics with keys 'fx', 'fy', 'cx', 'cy'.
        
    Returns:
        tuple: (X, Y, Z) coordinates in meters.
    """
    if depth_value <= 0:
        raise ValueError("Invalid depth value. Depth must be greater than 0.")

    fx = intrinsics['fx']
    fy = intrinsics['fy']
    cx = intrinsics['cx']
    cy = intrinsics['cy']

    # Calculate real-world coordinates
    X = (u - cx) * depth_value / fx
    Y = (v - cy) * depth_value / fy
    Z = depth_value

    return X, Y, Z


    
def generate_spatial_directive(x, y, z):
    """
    Generates a directive describing the location of an object based on its coordinates.
    Adjusted for OpenCV coordinates where `y` increases downward.
    
    Parameters:
        x (float): Horizontal position (meters).
        y (float): Vertical position (meters).
        z (float): Depth position (meters).
    
    Returns:
        str: A descriptive spatial directive for the object.
    """
    # Determine horizontal position
    if x < -0.5:
        horizontal = f"{abs(x):.1f} meters to your left"
    elif x > 0.5:
        horizontal = f"{x:.1f} meters to your right"
    else:
        horizontal = "directly in front of you"

    # Determine vertical position
    if y > 1.5:  # y > 1.5 means the object is near the floor
        vertical = "on the floor"
    elif y > 0.5:  # y between 0.5 and 1.5 means it's at arm level
        vertical = "at arm level"
    else:  # y <= 0.5 means it's above eye level
        vertical = "above eye level"

    # Determine depth position
    if z < 0.5:
        depth = "very close to you"
    elif z < 2.0:
        depth = f"{z:.1f} meters in front of you"
    else:
        depth = f"about {z:.1f} meters away"

    # Combine directives
    return f"The object is {horizontal}, {vertical}, and {depth}."


def example_usage():
    # Example coordinates for different objects
    objects = [
        {"x": -2.0, "y": 1.6, "z": 3.5},  # Left, on the floor, far away
        {"x": 0.5, "y": 0.6, "z": 1.2},  # Right, at arm level, medium distance
        {"x": 0.0, "y": 0.3, "z": 0.4},  # Front, above eye level, very close
    ]

    for obj in objects:
        directive = generate_spatial_directive(obj["x"], obj["y"], obj["z"])
        print(directive)


if __name__ == "__main__":
    example_usage()


if __name__=="__main__":


    # Start the pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

    # Start streaming
    pipeline_profile = pipeline.start(config)


    camera_intrinsics = get_intrinsics(pipeline_profile)

    # Detected object pixel coordinates and depth value
    u, v = 640, 720  # Example pixel coordinates
    depth_value = 2.0  # Example depth value in meters

    spatial_coordinates = get_spatial_coordinates(u, v, depth_value, camera_intrinsics)
    print("Spatial Coordinates (X, Y, Z):", spatial_coordinates)

    # Stop the pipeline
    pipeline.stop()





