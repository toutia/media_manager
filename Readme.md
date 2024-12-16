###################### detect realsense ############################################

./libuvc_installation.sh
sudo cp /home/touti/dev/librealsense/build/Release/pyrealsense2.cpython-310-aarch64-linux-gnu.so /home/touti/.local/lib/python3.10/site-packages/
"""
Python 3.10.12 (main, Nov  6 2024, 20:22:13) [GCC 11.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import pyrealsense2 as rs
>>> rs.pipeline()
<pyrealsense2.pipeline object at 0xffff8c354670>
>>> exit()


"""
####################################installing deepstream bindings ##########################"

https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/tree/master/bindings




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



