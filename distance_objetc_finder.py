#!/usr/bin/env python3

import sys
import os
import gi
from flask import Flask, request, jsonify
from threading import Thread
import pyds

gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
"""
curl -X POST http://localhost:5000/set_target -H "Content-Type: application/json" -d '{"target": "cell phone"}'
curl -X POST http://localhost:5000/start_pipelines
curl -X POST http://localhost:5000/stop_pipelines
"""
# Define constants and YOLO handling code
MUXER_BATCH_TIMEOUT_USEC = 10000
output_file_path ='output.mp4'
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

def osd_sink_pad_buffer_probe(pad, info, pitch):
    frame_number = 0
    obj_counter = {class_id: 0 for class_id in range(len(class_labels))}
    num_rects = 0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        target_found = False
        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            obj_counter[obj_meta.class_id] += 1
            class_name = class_labels[obj_meta.class_id]

            if class_name == target_object:
                # Extract depth information
                rect_params = obj_meta.rect_params
                depth_center_x = int(rect_params.left + rect_params.width / 2)
                depth_center_y = int(rect_params.top + rect_params.height / 2)

                # Use depth data to calculate distance
                depth_map = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                distance = depth_map[depth_center_y, depth_center_x] * 0.001  # Assuming depth in mm
                print(f"Detected {class_name} at distance: {distance:.2f} meters")

                target_found = True

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        change_pitch(target_found, pitch)

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK





# Load class labels from the labels.txt file
def load_labels(file_path="Primary_Detector/labels.txt"):
    with open(file_path, "r") as f:
        labels = [line.strip() for line in f.readlines()]
    return labels

class_labels = load_labels("Primary_Detector/labels.txt")
target_object = 'bottle'
pipeline = None
audio_pipeline = None
loop = GLib.MainLoop()

app = Flask(__name__)

# Function to change pitch dynamically based on detection status
def change_pitch(is_found, pitch):
    if is_found:
        pitch.set_property("pitch", 1.5)  # Higher pitch when object is found
    else:
        pitch.set_property("pitch", 0.8)  # Lower pitch while searching

# Define constants and other helper functions...
# (keep the bus_call, osd_sink_pad_buffer_probe functions unchanged)

# Additional modifications in the pipeline setup
@app.route('/start_pipelines', methods=['POST'])
def start_pipelines():
    global pipeline, audio_pipeline
    if pipeline is not None and audio_pipeline is not None:
        pipeline.set_state(Gst.State.PLAYING)
        audio_pipeline.set_state(Gst.State.PLAYING)
        return jsonify({"message": "Pipelines are already running."}), 200

    # Initialize GStreamer
    Gst.init(None)

    # Create audio pipeline
    audio_pipeline = Gst.parse_launch(
        "audiotestsrc wave=sine freq=440 volume=0.3 ! pitch name=pitch ! autoaudiosink"
    )
    pitch = audio_pipeline.get_by_name("pitch")

    # Create pipeline
    print("Creating Pipeline \n")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    # Source for RealSense camera
    print("Creating RealSense Source \n")
    realsense_src = Gst.ElementFactory.make("realsensesrc", "realsense-source")
    if not realsense_src:
        sys.stderr.write(" Unable to create RealSense source \n")

    # RealSense demux to separate color and depth
    rs_demux = Gst.ElementFactory.make("rsdemux", "realsense-demux")
    if not rs_demux:
        sys.stderr.write(" Unable to create RealSense demux \n")

    # Caps filter for color stream
    color_capsfilter = Gst.ElementFactory.make("capsfilter", "color-capsfilter")
    if not color_capsfilter:
        sys.stderr.write(" Unable to create color capsfilter \n")
    color_capsfilter.set_property(
        'caps', Gst.Caps.from_string("video/x-raw, format=RGB, framerate=30/1")
    )

    # Elements for color processing
    color_convert = Gst.ElementFactory.make("videoconvert", "color-convert")
    if not color_convert:
        sys.stderr.write(" Unable to create videoconvert for color \n")

    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvideoconvert \n")

    streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create nvstreammux \n")


    # Set necessary properties for streammux
    streammux.set_property("width", 1920)  # Example resolution: Full HD
    streammux.set_property("height", 1080)
    streammux.set_property("batch-size", 1)  # Adjust based on the number of input streams
    streammux.set_property("batched-push-timeout", 4000000)

    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")
    pgie.set_property("config-file-path", "dstest1_pgie_config.txt")

    # OSD and sink
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")
    sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
    if not sink:
        sys.stderr.write(" Unable to create sink \n")
    sink.set_property("sync", False)

    # Linking elements for color stream
    print("Adding and linking elements for the color stream \n")
    pipeline.add(realsense_src)
    pipeline.add(rs_demux)
    pipeline.add(color_capsfilter)
    pipeline.add(color_convert)
    pipeline.add(nvvidconv)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvosd)
    pipeline.add(sink)

    realsense_src.link(rs_demux)
    rs_demux.link(color_capsfilter)
    color_capsfilter.link(color_convert)
    color_convert.link(nvvidconv)
    nvvidconv.link(streammux)
    streammux.link(pgie)
    pgie.link(nvosd)
    nvosd.link(sink)

    # Depth pipeline handling
    depth_capsfilter = Gst.ElementFactory.make("capsfilter", "depth-capsfilter")
    if not depth_capsfilter:
        sys.stderr.write(" Unable to create depth capsfilter \n")
    depth_capsfilter.set_property(
        'caps', Gst.Caps.from_string("application/x-raw, format=GRAY16_LE")
    )

    depth_queue = Gst.ElementFactory.make("queue", "depth-queue")
    if not depth_queue:
        sys.stderr.write(" Unable to create depth queue \n")

    # Add depth elements
    print("Adding and linking depth elements \n")
    pipeline.add(depth_capsfilter)
    pipeline.add(depth_queue)

    rs_demux.link(depth_capsfilter)
    depth_capsfilter.link(depth_queue)

    # Start the pipelines
    pipeline.set_state(Gst.State.PLAYING)
    audio_pipeline.set_state(Gst.State.PLAYING)

    # Create a bus and attach the bus_call function
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Start the main loop in a separate thread
    Thread(target=loop.run, daemon=True).start()

    return jsonify({"message": "Pipelines started."}), 200



def main():
    # Start Flask server
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    sys.exit(main())
