import os
import subprocess
"""

Not working need to fix this 
/dev/video0 is hardcoded in the server code 
"""
def list_video_devices():
    return [os.path.join('/dev', device) for device in os.listdir('/dev') if device.startswith('video')]

def get_device_info(device):
    try:
        output = subprocess.check_output(['v4l2-ctl', '--get-ctrl', 'device_name', '--device', device], stderr=subprocess.STDOUT)
        return output.decode().strip()
    except subprocess.CalledProcessError as e :
        print(e)
        return "Error retrieving device info."
    except FileNotFoundError:
        return "v4l2-ctl not found."

def find_logitech_camera():
    video_devices = list_video_devices()
    for device in video_devices:
        device_name = get_device_info(device)
        print(device_name)
        if 'Logitech'.lower() in device_name.lower():
            print(f"Found Logitech camera at {device}: {device_name}")
            return device
    print("No Logitech camera found.")
    return None

if __name__ == "__main__":
    camera_device = find_logitech_camera()
    if camera_device:
        print(f"Using camera device: {camera_device}")
    else:
        print("Camera device not found.")
