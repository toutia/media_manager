import pyrealsense2 as rs
import numpy as np
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
MUXER_BATCH_TIMEOUT_USEC = 10000
# Initialize GStreamer
Gst.init(None)
import pyds
# Initialize RealSense pipeline
rs_pipeline = rs.pipeline()
config = rs.config()

# Configure RealSense streams
config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

# Start RealSense pipeline
rs_pipeline.start(config)

def fetch_rs_frames():
    """
    Fetches color and depth frames from the RealSense camera.
    """
    frames = rs_pipeline.wait_for_frames()
    color_frame = frames.get_color_frame()
    depth_frame = frames.get_depth_frame()

    if not color_frame or not depth_frame:
        return None, None

    # Convert frames to NumPy arrays
    color_image = np.asanyarray(color_frame.get_data())
    depth_image = np.asanyarray(depth_frame.get_data())

    return color_image, depth_image

def push_rs_frames(appsrc, _):
    """
    Pushes RealSense frames into the GStreamer pipeline through appsrc.
    """
    color_image, depth_image = fetch_rs_frames()
    if color_image is None:
        return

    # Embed depth data as metadata
    depth_data = depth_image.tobytes()

    # Convert color image to GStreamer buffer
    gst_buffer = Gst.Buffer.new_allocate(None, color_image.nbytes, None)
    gst_buffer.fill(0, color_image.tobytes())

    # # Attach depth data as custom metadata
    # gst_buffer.add_meta("depth_data", depth_data)

    # Push buffer into the pipeline
    appsrc.emit("push-buffer", gst_buffer)
    return True

def osd_sink_pad_buffer_probe(pad, info):
    """
    Probe function to extract depth data and perform object-specific depth analysis.
    """
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return Gst.PadProbeReturn.OK
    print(gst_buffer)
    # # Retrieve the depth data from metadata
    # meta_data = gst_buffer.get_meta("depth_data")
    # if meta_data is not None:
    #     depth_data = np.frombuffer(meta_data, dtype=np.uint16).reshape((720, 1280))

    # Retrieve batch metadata for inference
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            # Object bounding box
            bbox = obj_meta.rect_params
            left, top, width, height = (
                int(bbox.left),
                int(bbox.top),
                int(bbox.width),
                int(bbox.height),
            )

            # Extract depth data for object's region
            depth_roi = depth_data[top:top + height, left:left + width]
            average_depth = np.mean(depth_roi)
            print(f"Object: {obj_meta.class_id}, Depth: {average_depth:.2f} mm")

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK

# Create pipeline elements
pipeline = Gst.Pipeline.new("rs-pipeline")

# Appsrc for RealSense data
source = Gst.ElementFactory.make("appsrc", "rs-source")
source.set_property("is-live", True)
source.set_property("format", Gst.Format.TIME)
# source.set_property("caps", Gst.Caps.from_string("video/x-raw,format=RGB,width=1280,height=720,framerate=30/1"))

caps_filter = Gst.ElementFactory.make("capsfilter", "caps_filter")
if not caps_filter:
        sys.stderr.write(" Unable to create  capsfilter \n")



# videoconvert to make sure a superset of raw formats are supported
vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
if not vidconvsrc:
    sys.stderr.write(" Unable to create videoconvert \n")
color_queue = Gst.ElementFactory.make('queue', 'color_queue')
video_sink= Gst.ElementFactory.make("autovideosink", "vid_sink")

# nvvideoconvert to convert incoming raw buffers to NVMM Mem (NvBufSurface API)
nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
if not nvvidconvsrc:
    sys.stderr.write(" Unable to create Nvvideoconvert \n")

# caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
# if not caps_vidconvsrc:
#     sys.stderr.write(" Unable to create capsfilter \n")

# # Create nvstreammux instance to form batches from one or more sources.
# streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
# if not streammux:
#     sys.stderr.write(" Unable to create NvStreamMux \n")

# # Use nvinfer to run inferencing on camera's output,
# # behaviour of inferencing is set through config file
# pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
# if not pgie:
#     sys.stderr.write(" Unable to create pgie \n")

# # Use convertor to convert from NV12 to RGBA as required by nvosd
# nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
# if not nvvidconv:
#     sys.stderr.write(" Unable to create nvvidconv \n")

# # Create OSD to draw on the converted RGBA buffer
# nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
# if not nvosd:
#     sys.stderr.write(" Unable to create nvosd \n")

# # redirect to defaulmt diplay 
# sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
# if not sink:
#     sys.stderr.write(" Unable to create egl sink \n")
# sink.set_property("sync", False)



# print("Playing cam %s " %"/dev/video0")
# # caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
# caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
# streammux.set_property('width', 1920)
# streammux.set_property('height', 1080)
# streammux.set_property('batch-size', 1)
# streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)
# pgie.set_property('config-file-path', "dstest1_pgie_config.txt")

caps_filter.set_property('caps', Gst.Caps.from_string("video/x-raw,format=RGB,width=1080,height=640,framerate=30/1"))
"""
0:00:00.854077909 53850 0xaaaafb120120 WARN              capsfilter gstcapsfilter.c:458:gst_capsfilter_prepare_buf:<caps_filter> error: Output caps are unfixed: video/x-raw, framerate=(fraction)30/1, width=(int)[ 1, 32768 ], height=(int)[ 1, 32768 ], 
format=(string){ ABGR64_LE, BGRA64_LE, AYUV64, ARGB64_LE, ARGB64, RGBA64_LE, ABGR64_BE, 
BGRA64_BE, ARGB64_BE, RGBA64_BE, GBRA_12LE, GBRA_12BE, # not tested 
Y412_LE, Y412_BE, A444_10LE, GBRA_10LE, A444_10BE, GBRA_10BE, A422_10LE, A422_10BE, A420_10LE, A420_10BE, RGB10A2_LE, BGR10A2_LE, Y410, GBRA, 
ABGR, VUYA, BGRA, AYUV, ARGB, RGBA, A420, AV12, Y444_16LE, Y444_16BE, v216, P016_LE, P016_BE, Y444_12LE, GBR_12LE, Y444_12BE, GBR_12BE, I422_12LE, 
I422_12BE, Y212_LE, Y212_BE, I420_12LE, I420_12BE, P012_LE, P012_BE, Y444_10LE, GBR_10LE, Y444_10BE, GBR_10BE, r210, I422_10LE, I422_10BE, NV16_10LE32, 
Y210, v210, UYVP, I420_10LE, I420_10BE, P010_10LE, NV12_10LE32, NV12_10LE40, P010_10BE, Y444, RGBP, GBR, BGRP, NV24, xBGR, BGRx, xRGB, RGBx, BGR, IYU2,
 v308, RGB, Y42B, NV61, NV16, VYUY, YVYU, NV21, NV12, NV12_64Z32, NV12_4L4, NV12_32L32, Y41B, IYU1, YVU9, YUV9, RGB16, BGR16, RGB15, BGR15, RGB8P, GRAY16_LE,
  GRAY16_BE, GRAY10_LE32, GRAY8, I420, UYVY, YV12, YUY2 }


"""


print("Adding elements to Pipeline \n")
pipeline.add(source)
pipeline.add(caps_filter)
pipeline.add(vidconvsrc)
pipeline.add(color_queue)
pipeline.add(video_sink)
pipeline.add(nvvidconvsrc)
# pipeline.add(caps_vidconvsrc)
# pipeline.add(streammux)
# pipeline.add(pgie)
# pipeline.add(nvvidconv)
# pipeline.add(nvosd)
# here to default 
# pipeline.add(sink)

print("Linking elements in the Pipeline \n")
source.link(caps_filter)
caps_filter.link(vidconvsrc)
vidconvsrc.link(color_queue)
color_queue.link(nvvidconvsrc)
nvvidconvsrc.link(video_sink)

# sinkpad = streammux.request_pad_simple("sink_0")
# if not sinkpad:
#     sys.stderr.write(" Unable to get the sink pad of streammux \n")
# srcpad = caps_vidconvsrc.get_static_pad("src")
# if not srcpad:
#     sys.stderr.write(" Unable to get source pad of caps_vidconvsrc \n")
# srcpad.link(sinkpad)
# streammux.link(pgie)
# pgie.link(nvvidconv)
# nvvidconv.link(nvosd)
# # here to default 
# nvosd.link(sink)


# Use CUDA unified memory in the pipeline so frames
# can be easily accessed on CPU in Python.
# mem_type = int(pyds.NVBUF_MEM_CUDA_PINNED)
# # streammux.set_property("nvbuf-memory-type", mem_type)
# nvvidconvsrc.set_property("nvbuf-memory-type", mem_type)
# if platform_info.is_wsl():
#     #opencv functions like cv2.line and cv2.putText is not able to access NVBUF_MEM_CUDA_UNIFIED memory
#     #in WSL systems due to some reason and gives SEGFAULT. Use NVBUF_MEM_CUDA_PINNED memory for such
#     #usecases in WSL. Here, nvvidconv1's buffer is used in tiler sink pad probe and cv2 operations are
#     #done on that.
#     print("using nvbuf_mem_cuda_pinned memory for nvvidconv1\n")
#     vc_mem_type = int(pyds.NVBUF_MEM_CUDA_PINNED)
#     nvvidconv1.set_property("nvbuf-memory-type", vc_mem_type)
# else:
#     nvvidconv1.set_property("nvbuf-memory-type", mem_type)       




# osdsinkpad = nvosd.get_static_pad("sink")
# if not osdsinkpad:
#     sys.stderr.write(" Unable to get sink pad of nvosd \n")
# # passing the pitch element here to be able to control it dynamically 
# osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe)

# Start feeding frames from RealSense
source.connect("need-data", push_rs_frames)

# Start the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Run the main loop
try:
    loop = GLib.MainLoop()
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    pipeline.set_state(Gst.State.NULL)
    rs_pipeline.stop()
