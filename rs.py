import pyrealsense2 as rs
import numpy as np
import math

def get_intrinsics():
    """
    Retrieve camera intrinsics for the depth stream.
    
    Returns:
        dict: A dictionary with camera intrinsics: 'fx', 'fy', 'cx', 'cy'.
    """
    # Start the pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

    # Start streaming
    pipeline_profile = pipeline.start(config)

    # Get the depth stream intrinsics
    depth_sensor = pipeline_profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()  # Depth scale in meters
    print("Depth Scale is: ", depth_scale)

    # Get stream intrinsics
    depth_stream = pipeline_profile.get_stream(rs.stream.depth)
    intrinsics = depth_stream.as_video_stream_profile().get_intrinsics()

    # Stop the pipeline
    pipeline.stop()

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

# Example usage
camera_intrinsics = get_intrinsics()

# Detected object pixel coordinates and depth value
u, v = 640, 720  # Example pixel coordinates
depth_value = 2.0  # Example depth value in meters

spatial_coordinates = get_spatial_coordinates(u, v, depth_value, camera_intrinsics)
print("Spatial Coordinates (X, Y, Z):", spatial_coordinates)





