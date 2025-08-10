
# media_manager

**media_manager** is a software solution dedicated to real-time video stream management and analysis, featuring advanced capabilities such as object detection, object tracking, RealSense camera management, and configuration via text files. This project is designed for production environments requiring efficient and flexible video monitoring.

## Key Features

- Real-time object detection.
- Object tracking across successive frames.
- Integration with Intel RealSense cameras for video and depth capture.
- Flexible configuration via text and JSON files.
- Integration with `systemd` for easy service management.

## Repository Structure

- `Primary_Detector/`: Main object detection module.
- `realsense_examples/`: Examples using RealSense cameras.
- `systemd/`: Files for integration with systemd.
- Key Python scripts:
  - `color_depth.py`
  - `detect_camera.py`
  - `distance_objetc_finder.py`
  - `multi_rs.py`
  - `object_finder.py`
  - `realsense_plugin.py`
  - `rs_helpers.py`
  - `rs_pipeline.py`
  - `rs_track.py`
  - `tracker_finder.py`
- Configuration files:
  - `tracker_config.txt`
  - `tracker_perf.yml`
  - `test.json`
- `libuvc_installation.sh`: Script to install libuvc library.
- `media_manager.log`: Log file.

## Requirements

- Python 3.6 or higher
- NVIDIA GPU (recommended for accelerated processing)
- Compatible Intel RealSense camera
- Python libraries (install via pip):
  ```bash
  pip install pyrealsense2 opencv-python numpy pyyaml
  ```
- `libuvc` installed via provided script.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/toutia/media_manager.git
   cd media_manager
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install `libuvc`:
   ```bash
   ./libuvc_installation.sh
   ```

4. Reload udev rules to detect cameras:
   ```bash
   sudo udevadm control --reload-rules
   ```

## Usage

- Start the main manager:
  ```bash
  python3 media_manager.py
  ```

- To run a specific script, e.g., camera detection:
  ```bash
  python3 detect_camera.py
  ```

- To manage the service with systemd:
  ```bash
  sudo cp systemd/media_manager.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable media_manager
  sudo systemctl start media_manager
  ```

## Configuration

Customize configuration files before use:

- `tracker_config.txt`: tracker parameters.
- `tracker_perf.yml`: tracker performance settings.
- `test.json`: specific test parameters.

## Logs

Service logs are saved in `media_manager.log`. Check this file for diagnostics and monitoring.

## Contribution

Contributions are welcome. Please follow best practices for pull requests, documentation, and testing.

## License

This project is licensed under Apache-2.0. See the LICENSE file for details.
