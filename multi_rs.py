#!/usr/bin/env python3

import sys
import os
import gi
from flask import Flask, request, jsonify
from threading import Thread
import pyds
import configparser
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import threading
from rs_pipeline import RsCamera, list_connected_devices
import numpy as np
import cv2

# Define constants and YOLO handling code
MUXER_BATCH_TIMEOUT_USEC = 10000
file_path="Primary_Detector/labels.txt"
with open(file_path, "r") as f:
        class_labels = [line.strip() for line in f.readlines()]
target_object = 'bottle'


#define pipelines 
pipeline = None
audio_pipeline = None
# camera initialization

devices= list_connected_devices()
cameras={}
for device in devices:
    print(device)
    camera = RsCamera(serial_number= device )
    cameras[device]=camera
    
# DEPTH_UNIT= downward_camera.get_depth_scale()

DEPTH_UNIT=0.0010000000474974513
# Global depth buffer shared across threads
depth_buffer = None
depth_lock = threading.Lock()
# flask app 
loop = GLib.MainLoop()
app = Flask(__name__)

import time
def push_rs_frames(appsrc, _):
    """
    Pushes RealSense frames into the GStreamer pipeline through appsrc.
    """
    
    
    color_image1, depth_image1 = cameras['042222071132'].fetch_rs_frames()
    
    color_image2, depth_image2 = cameras['036522072529'].fetch_rs_frames()    

    if  color_image1 is None  or  color_image2 is None  :
        return


     # Apply a slight rotation to color_frame2 and depth_frame2
    h, w, _ = color_image2.shape
    rotation_matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle=10, scale=1.0)
        
    # Rotate the second color frame with proper interpolation
    rotated_color2 = cv2.warpAffine(
        color_image2,
        rotation_matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)  # Black border
    )

    color_image1_rgb = cv2.cvtColor(color_image1, cv2.COLOR_BGR2RGB)

    rotated_color2_rgb = cv2.cvtColor(rotated_color2, cv2.COLOR_BGR2RGB)



    # Combine the color frames vertically
    combined_color_frame = np.vstack((color_image1_rgb, color_image2))

    # Combine the depth frames vertically
    rotated_depth2 = cv2.warpAffine(depth_image2, rotation_matrix, (w, h), flags=cv2.INTER_NEAREST)
    combined_depth_frame = np.vstack((depth_image1, rotated_depth2))


    # # # Debugging: Validate combined frame
    # cv2.imshow('Combined Color Frame', combined_color_frame)
    # time.sleep(1)

    # Convert combined color frame to GStreamer buffer
    gst_buffer = Gst.Buffer.new_allocate(None, combined_color_frame.nbytes, None)
    gst_buffer.fill(0, combined_color_frame.tobytes())

    # Debugging: Log buffer size
    print(f"Combined frame shape: {combined_color_frame.shape}")
    print(f"frame shape: {color_image1_rgb.shape}")
    print(f"frame shape: {color_image1.shape}")
    print(f"Buffer size: {gst_buffer.get_size()} bytes")

    # Lock the shared buffer and store depth data
    global depth_buffer
     # Embed depth data as metadata
    depth_data = combined_depth_frame.tobytes()
    with depth_lock:
        depth_buffer = combined_depth_frame  # Update the shared depth buffer with the latest depth data

    # Push buffer into the pipeline
    appsrc.emit("push-buffer", gst_buffer)
    return True

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write("Warning: %s: %s\n" % (err, debug))
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True

def osd_sink_pad_buffer_probe(pad, info, pitch, volume):
    global depth_buffer
    frame_number = 0
    # Initialize object counter for all classes
    obj_counter = {class_id: 0 for class_id in range(len(class_labels))}
    num_rects = 0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return
    

    # Fetch and process the latest depth frame corresponding to the current GStreamer pipeline's probe
    with depth_lock:
        current_depth = depth_buffer.copy() if depth_buffer is not None else None

    if current_depth is None:
        print("No depth data available yet.")
        return Gst.PadProbeReturn.OK

    # Here implement the logic to correlate depth data with the color frame/region of interest
    # For instance:
    # - Extract target object regions using object detection
    # - Map object detection bounding boxes (from osd probe) to pixel indices
    # - Extract depth at these indices from `current_depth`

    # Log debugging information or fetch depth statistics from a region of interest
    


    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))

    # Create summary display text with counts of all detected objects
    display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
    display_meta.num_labels = 1
    py_nvosd_text_params = display_meta.text_params[0]



    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        target_found = False
        average_depth= 6
        # timestamp= frame_meta.ntp_timestamp
        # print(timestamp)
        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            # Increment the object count for the detected class
            obj_counter[obj_meta.class_id] += 1
            # Use the class label from labels.txt
            class_name = class_labels[obj_meta.class_id]

            if class_name == target_object :
                    target_found = True
                    # Extract bounding box coordinates
                    left = int(obj_meta.rect_params.left)
                    top = int(obj_meta.rect_params.top)
                    width = int(obj_meta.rect_params.width)
                    height = int(obj_meta.rect_params.height)

                    if current_depth is not None:
                        # Define ROI based on bounding box and calculate average depth
                        target_depth_region = current_depth[top:top + height, left:left + width]
                        average_depth = np.mean(target_depth_region)* DEPTH_UNIT  # Average depth
                        print(f"Average depth for target object: {average_depth } meters")
                        # Calculate center coordinates
                        u = left + width // 2
                        v = top + height // 2
                        spatial_coordinates = cameras['042222071132'].get_spatial_coordinates(u, v, average_depth)
                        print(spatial_coordinates)
                        x,y,z= spatial_coordinates
                        description= cameras['042222071132'].generate_spatial_directive(x,y,z)
                        print(description)

                        

                    break  # Exit
            py_nvosd_text_params.display_text = class_name
            pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

       
        # Display detected class names and their counts
        detected_classes = [
            f"{class_labels[class_id]}: {count}" for class_id, count in obj_counter.items() if count > 0
        ]
        summary_text = f"Frame {frame_number}, Objects: {num_rects}\n" + ", ".join(detected_classes)
        py_nvosd_text_params.display_text = summary_text
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)
        py_nvosd_text_params.set_bg_clr = 1
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

        change_pitch(target_found, pitch, volume, average_depth)

    # #past tracking meta data
    # l_user=batch_meta.batch_user_meta_list
    # while l_user is not None:
    #     try:
    #         # Note that l_user.data needs a cast to pyds.NvDsUserMeta
    #         # The casting is done by pyds.NvDsUserMeta.cast()
    #         # The casting also keeps ownership of the underlying memory
    #         # in the C code, so the Python garbage collector will leave
    #         # it alone
    #         user_meta=pyds.NvDsUserMeta.cast(l_user.data)
    #     except StopIteration:
    #         break
    #     if(user_meta and user_meta.base_meta.meta_type==pyds.NvDsMetaType.NVDS_TRACKER_PAST_FRAME_META):
    #         try:
    #             # Note that user_meta.user_meta_data needs a cast to pyds.NvDsTargetMiscDataBatch
    #             # The casting is done by pyds.NvDsTargetMiscDataBatch.cast()
    #             # The casting also keeps ownership of the underlying memory
    #             # in the C code, so the Python garbage collector will leave
    #             # it alone
    #             pPastDataBatch = pyds.NvDsTargetMiscDataBatch.cast(user_meta.user_meta_data)
    #         except StopIteration:
    #             break
    #         for miscDataStream in pyds.NvDsTargetMiscDataBatch.list(pPastDataBatch):
    #             print("streamId=",miscDataStream.streamID)
    #             print("surfaceStreamID=",miscDataStream.surfaceStreamID)
    #             for miscDataObj in pyds.NvDsTargetMiscDataStream.list(miscDataStream):
    #                 print("numobj=",miscDataObj.numObj)
    #                 print("uniqueId=",miscDataObj.uniqueId)
    #                 print("classId=",miscDataObj.classId)
    #                 print("objLabel=",miscDataObj.objLabel)
    #                 for miscDataFrame in pyds.NvDsTargetMiscDataObject.list(miscDataObj):
    #                     print('frameNum:', miscDataFrame.frameNum)
    #                     print('tBbox.left:', miscDataFrame.tBbox.left)
    #                     print('tBbox.width:', miscDataFrame.tBbox.width)
    #                     print('tBbox.top:', miscDataFrame.tBbox.top)
    #                     print('tBbox.right:', miscDataFrame.tBbox.height)
    #                     print('confidence:', miscDataFrame.confidence)
    #                     print('age:', miscDataFrame.age)
    #     try:
    #         l_user=l_user.next
    #     except StopIteration:
    #         break


    return Gst.PadProbeReturn.OK

# Load class labels from the labels.txt file
def load_labels():
    with open(file_path, "r") as f:
        labels = [line.strip() for line in f.readlines()]
    return labels

def depth_to_volume(average_depth, max_depth=2.0, sensitivity=2.5, min_volume=0.1):
    """
    Transform average depth to volume, making it more sensitive to close distances.
    
    Args:
        average_depth (float): The average depth in meters.
        max_depth (float): The maximum depth in meters that corresponds to zero volume.
        sensitivity (float): A factor that increases reactivity to close distances.
        min_volume (float): The minimum volume value to ensure a baseline sound level.
        
    Returns:
        float: A volume value between min_volume and 1.0 (loud).
    """
    if average_depth < 0:
        return min_volume  # Handle invalid depths with minimum volume
    
    # Transform depth to a normalized value between 0 (close) and 1 (far)
    normalized_depth = min(average_depth / max_depth, 1.0)
    
    # Apply a sensitivity adjustment (quadratic fall-off)
    adjusted_depth = normalized_depth ** sensitivity
    
    # Invert the normalized depth to get volume
    volume = 1.0 - adjusted_depth
    
    # Ensure the volume is at least the minimum volume
    return max(min_volume, min(1.0, volume))  # Clamp the volume to [min_volume, 1.0]

# Function to change pitch dynamically based on detection status
def change_pitch(is_found, pitch, volume, average_depth):
    print(depth_to_volume(average_depth))
    if is_found:
        pitch.set_property("pitch", 1.0)  # Higher pitch when object is found
        volume.set_property('volume', depth_to_volume(average_depth))
    else:
        pitch.set_property("pitch", 0.3)  # Lower pitch while searching
        volume.set_property('volume', 0.3)
# Define constants and other helper functions...
# (keep the bus_call, osd_sink_pad_buffer_probe functions unchanged)

@app.route('/set_target', methods=['POST'])
def set_target():
    global target_object
    target_object = request.json.get('target', target_object)
    print(target_object)
    return jsonify({"message": f"Target object set to {target_object}"}), 200

@app.route('/start_pipelines', methods=['POST'])
def start_pipelines():
    global pipeline, audio_pipeline
    if pipeline is not None and audio_pipeline is not None:
        pipeline.set_state(Gst.State.PLAYING)
        audio_pipeline.set_state(Gst.State.PLAYING)
        return jsonify({"message": "Pipelines are already running."}), 200
    
    # start the cameras 
    for camera in cameras.values():
        camera.start()
    
    # Initialize GStreamer
    Gst.init(None)
    
    # Create audio pipeline
    audio_pipeline = Gst.parse_launch(
        "audiotestsrc  wave=sine freq=440  ! volume name=volume_control volume=0.3 ! pitch name=pitch  pitch=0.3 ! autoaudiosink"
    )
    pitch = audio_pipeline.get_by_name("pitch")
    volume= audio_pipeline.get_by_name("volume_control")
    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    source = Gst.ElementFactory.make("appsrc", "rs-source")



    if not source:
        sys.stderr.write(" Unable to create Source \n")

    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    if not caps_v4l2src:
        sys.stderr.write(" Unable to create v4l2src capsfilter \n")


    print("Creating Video Converter \n")

    # Adding videoconvert -> nvvideoconvert as not all
    # raw formats are supported by nvvideoconvert;
    # Say YUYV is unsupported - which is the common
    # raw format for many logi usb cams
    # In case we have a camera with raw format supported in
    # nvvideoconvert, GStreamer plugins' capability negotiation
    # shall be intelligent enough to reduce compute by
    # videoconvert doing passthrough (TODO we need to confirm this)


    # videoconvert to make sure a superset of raw formats are supported
    vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
    if not vidconvsrc:
        sys.stderr.write(" Unable to create videoconvert \n")

    # nvvideoconvert to convert incoming raw buffers to NVMM Mem (NvBufSurface API)
    nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
    if not nvvidconvsrc:
        sys.stderr.write(" Unable to create Nvvideoconvert \n")

    caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    if not caps_vidconvsrc:
        sys.stderr.write(" Unable to create capsfilter \n")

    # Create nvstreammux instance to form batches from one or more sources.
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")

    # Use nvinfer to run inferencing on camera's output,
    # behaviour of inferencing is set through config file
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")
    

    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        sys.stderr.write(" Unable to create tracker \n")

    # Use convertor to convert from NV12 to RGBA as required by nvosd
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")

    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")

    # redirect to defaulmt diplay 
    sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
    if not sink:
        sys.stderr.write(" Unable to create egl sink \n")
    sink.set_property("sync", False)

    # two  h=720 and w= 1280 vertically superposed give w 1280 and height 1440 
    caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1, width=1280, height=1440, format=BGR"))
    caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    source.set_property("is-live", True)
    source.set_property("format", Gst.Format.TIME)

    nvvidconvsrc.set_property('compute-hw',1)
    streammux.set_property('width', 1280)  # 1920 is a standard 16:9 full HD resolution
    streammux.set_property('height', 1440)  # Similarly, for 1080p
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)
    pgie.set_property('config-file-path', "dstest1_pgie_config.txt")
    #Set properties of tracker
    config = configparser.ConfigParser()
    config.read('tracker_config.txt')
    config.sections()
    for key in config['tracker']:
        if key == 'tracker-width' :
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        if key == 'tracker-height' :
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        if key == 'gpu-id' :
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        if key == 'll-lib-file' :
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        if key == 'll-config-file' :
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)
    

    print("Adding elements to Pipeline \n")
    pipeline.add(source)
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)



    print("Linking elements in the Pipeline \n")
    source.link(caps_v4l2src)
    caps_v4l2src.link(vidconvsrc)
    vidconvsrc.link(nvvidconvsrc)
    nvvidconvsrc.link(caps_vidconvsrc)
    sinkpad = streammux.request_pad_simple("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    srcpad = caps_vidconvsrc.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of caps_vidconvsrc \n")
    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(sink)



    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")
    # passing the pitch element here to be able to control it dynamically 
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe,pitch, volume)
    
    
    # Start feeding frames from RealSense
    source.connect("need-data", push_rs_frames)



    # Start the pipelines
    pipeline.set_state(Gst.State.PLAYING)
    audio_pipeline.set_state(Gst.State.PLAYING)
    
  
    
    # Start the main loop in a separate thread
    Thread(target=loop.run, daemon=True).start()
    
    return jsonify({"message": "Pipelines started."}), 200

@app.route('/stop_pipelines', methods=['POST'])
def stop_pipelines():
    global pipeline, audio_pipeline
    if pipeline is None or audio_pipeline is None:

        return jsonify({"message": "Pipelines are not running."}), 400
    
    # Stop the pipelines
    pipeline.set_state(Gst.State.NULL)
    audio_pipeline.set_state(Gst.State.NULL)
    loop.quit()
    pipeline=audio_pipeline=None
    for camera in cameras.values():
        camera.stop()
    return jsonify({"message": "Pipelines stopped."}), 200

def main():
    # Start Flask server
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    sys.exit(main())
