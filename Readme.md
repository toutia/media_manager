
###########################"" deepstream-app fix  rtsp lib not found ######################################""
touti@ubuntu:/opt/nvidia/deepstream/deepstream$ deepstream-app
deepstream-app: error while loading shared libraries: libgstrtspserver-1.0.so.0: cannot open shared object file: No such file or directory


touti@ubuntu:/opt/nvidia/deepstream/deepstream$ ldconfig -p | grep libgstrtspserver-1.0.so.0
touti@ubuntu:/opt/nvidia/deepstream/deepstream$ sudo apt update

touti@ubuntu:/opt/nvidia/deepstream/deepstream$ sudo apt install libgstrtspserver-1.0-0

touti@ubuntu:/opt/nvidia/deepstream/deepstream$ ldconfig -p | grep libgstrtspserver-1.0.so.0
	libgstrtspserver-1.0.so.0 (libc6,AArch64) => /lib/aarch64-linux-gnu/libgstrtspserver-1.0.so.0
touti@ubuntu:/opt/nvidia/deepstream/deepstream$ deepstream-app
** ERROR: <main:655>: Specify config file with -c option
Quitting
App run failed


####################################permission issues ####################################

touti@ubuntu:/opt/nvidia/deepstream/deepstream/sources$ sudo chown -R touti:touti  deepstream_python_apps


####################################installing deepstream bindings ##########################"

https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/tree/master/bindings


##########################   inetract with server ###################################################""

curl -X POST http://localhost:5000/set_target -H "Content-Type: application/json" -d '{"target": "cell phone"}'
curl -X POST http://localhost:5000/start_pipelines
curl -X POST http://localhost:5000/stop_pipelines


#######################################"" realsense d435i############################################
firmware 5.12   need to be installed 
jetpack 6.1 
cuda 12.6


######################### to buid gstreamer relasense plugin #####################################

change relasense_meta.cpp remove volatile ...
https://github.com/WKDSMRT/realsense-gstreamer

##############################


#########################""" install pyrealsesnse2 python bindings ###################################


sudo apt update
sudo apt install git cmake python3 python3-dev python3-pip build-essential libusb-1.0-0-dev libssl-dev libudev-dev pkg-config



pip install numpy pybind11



git clone https://github.com/IntelRealSense/librealsense.git
cd librealsense
git checkout v2.56.2  # Replace with the desired version

mkdir build && cd build
cmake .. -DBUILD_PYTHON_BINDINGS=ON -DPYTHON_EXECUTABLE=$(which python3)


make -j$(nproc)

sudo cp /home/touti/dev/librealsense/build/Release/pyrealsense2.cpython-310-aarch64-linux-gnu.so /home/touti/.local/lib/python3.10/site-packages/


#If you encounter device access issues, add a udev rule:


sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
