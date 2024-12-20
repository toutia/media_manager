import pyrealsense2 as rs 
import numpy as np

class RsCamera:

    def __init__(self, serial_number=None):

        self.rs_pipeline = rs.pipeline()
        self.config = rs.config()

        # If a serial number is provided, configure the pipeline to use the specific camera
        if serial_number:
            self.config.enable_device(serial_number)
        # Configure RealSense streams
        self.config.enable_stream(rs.stream.color, 1280, 720, rs.format.rgb8, 30)
        self.config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
        self.pipeline_profile=None

        self.align_to_color = rs.align(rs.stream.color)





    def start(self):
        
        # Start RealSense pipeline
        self.pipeline_profile = self.rs_pipeline.start(self.config)
        

    

    def get_intrinsics(self):
        """
        Retrieve camera intrinsics for the depth stream.
        
        Returns:
            dict: A dictionary with camera intrinsics: 'fx', 'fy', 'cx', 'cy'.
        """
        # Get stream intrinsics
        depth_stream = self.pipeline_profile.get_stream(rs.stream.depth)
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
        return  intrinsics_dict


    def get_depth_scale(self):
        """
        Retrieve camera depth scale for the depth stream.
        
        Returns:
            float : the scale unit.
        """
        # Get the depth stream intrinsics
        depth_sensor = self.pipeline_profile.get_device().first_depth_sensor()
        depth_scale = depth_sensor.get_depth_scale()  # Depth scale in meters
        print("Depth Scale is: ", depth_scale)

        return depth_scale



    def fetch_rs_frames(self):
        """
        Fetches color and depth frames from the RealSense camera.
        """

        frames = self.rs_pipeline.wait_for_frames()
        # Align depth frames to color frames
        # aligned_frames= self.align_to_color.process(frames)
        # aligned_frames= frames
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            return None, None

        # Convert frames to NumPy arrays
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        

        return color_image, depth_image

    
        
    def get_spatial_coordinates(self,u, v, depth_value):
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

        intrinsics = self.get_intrinsics()

        fx = intrinsics['fx']
        fy = intrinsics['fy']
        cx = intrinsics['cx']
        cy = intrinsics['cy']

        # Calculate real-world coordinates
        X = (u - cx) * depth_value / fx
        Y = (v - cy) * depth_value / fy
        Z = depth_value

        return X, Y, Z

    def stop(self):

        """
        stops the pipeline

        """

        self.rs_pipeline.stop()


                




def list_connected_devices():
    context = rs.context()
    devices = context.query_devices()
    device_list = []
    print(devices)
    for device in devices:
        device_list.append(device.get_info(rs.camera_info.serial_number))

    return device_list


# Example usage
if __name__ == "__main__":
    devices = list_connected_devices()
    print("Connected devices:", devices)

    if devices:
        # Initialize RsCamera with the first device's serial number
        camera = RsCamera(serial_number=devices[0])
        camera.start()
        print("Camera started.")
        camera.stop()
        print("Camera stopped.")
    else:
        print("No RealSense devices connected.")