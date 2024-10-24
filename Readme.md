
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