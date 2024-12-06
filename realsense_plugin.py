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
"""
curl -X POST http://localhost:5000/set_target -H "Content-Type: application/json" -d '{"target": "cell phone"}'
curl -X POST http://localhost:5000/start_pipelines
curl -X POST http://localhost:5000/stop_pipelines
"""


STREAM_TYPE = 2
ALIGN = 0
IMU_ON = True
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
    # Initialize object counter for all classes
    obj_counter = {class_id: 0 for class_id in range(len(class_labels))}
    num_rects = 0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return

    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        target_found = False
        timestamp= frame_meta.ntp_timestamp
        print(timestamp)
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

            # Adding bounding box and class name overlay to display
            display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
            display_meta.num_labels = 1
            py_nvosd_text_params = display_meta.text_params[0]
            # Use the class label from labels.txt
            class_name = class_labels[obj_meta.class_id]

            if class_name == target_object :
                    target_found = True
                    break
            py_nvosd_text_params.display_text = class_name
            pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        # Create summary display text with counts of all detected objects
        display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
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

        change_pitch(target_found, pitch)

    #past tracking meta data
    l_user=batch_meta.batch_user_meta_list
    while l_user is not None:
        try:
            # Note that l_user.data needs a cast to pyds.NvDsUserMeta
            # The casting is done by pyds.NvDsUserMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone
            user_meta=pyds.NvDsUserMeta.cast(l_user.data)
        except StopIteration:
            break
        if(user_meta and user_meta.base_meta.meta_type==pyds.NvDsMetaType.NVDS_TRACKER_PAST_FRAME_META):
            try:
                # Note that user_meta.user_meta_data needs a cast to pyds.NvDsTargetMiscDataBatch
                # The casting is done by pyds.NvDsTargetMiscDataBatch.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone
                pPastDataBatch = pyds.NvDsTargetMiscDataBatch.cast(user_meta.user_meta_data)
            except StopIteration:
                break
            for miscDataStream in pyds.NvDsTargetMiscDataBatch.list(pPastDataBatch):
                print("streamId=",miscDataStream.streamID)
                print("surfaceStreamID=",miscDataStream.surfaceStreamID)
                for miscDataObj in pyds.NvDsTargetMiscDataStream.list(miscDataStream):
                    print("numobj=",miscDataObj.numObj)
                    print("uniqueId=",miscDataObj.uniqueId)
                    print("classId=",miscDataObj.classId)
                    print("objLabel=",miscDataObj.objLabel)
                    for miscDataFrame in pyds.NvDsTargetMiscDataObject.list(miscDataObj):
                        print('frameNum:', miscDataFrame.frameNum)
                        print('tBbox.left:', miscDataFrame.tBbox.left)
                        print('tBbox.width:', miscDataFrame.tBbox.width)
                        print('tBbox.top:', miscDataFrame.tBbox.top)
                        print('tBbox.right:', miscDataFrame.tBbox.height)
                        print('confidence:', miscDataFrame.confidence)
                        print('age:', miscDataFrame.age)
        try:
            l_user=l_user.next
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
        pitch.set_property("pitch", 1.0)  # Higher pitch when object is found
    else:
        pitch.set_property("pitch", 0.3)  # Lower pitch while searching

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
    print(target_object )
    global pipeline, audio_pipeline
    print(pipeline)
    if pipeline is not None and audio_pipeline is not None:
        pipeline.set_state(Gst.State.PLAYING)
        audio_pipeline.set_state(Gst.State.PLAYING)
        return jsonify({"message": "Pipelines are already running."}), 200
    
    # Initialize GStreamer
    Gst.init(None)
    
    # Create audio pipeline
    audio_pipeline = Gst.parse_launch(
        "audiotestsrc wave=sine freq=440 volume=0.3 ! pitch name=pitch  pitch=0.3 ! autoaudiosink"
    )
    pitch = audio_pipeline.get_by_name("pitch")

   # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements


    def demuxer_callback(demuxer, pad):
        print(f'pad template: {pad.get_property("template").name_template}')
        if pad.get_property("template").name_template == "color":
            qc_pad = queue_color.get_static_pad("sink")
            linked = pad.link(qc_pad)
            if linked != Gst.PadLinkReturn.OK:
                print('failed to link demux to color queue')
        elif pad.get_property("template").name_template == "depth":
            qd_pad = queue_depth.get_static_pad("sink")
            linked = pad.link(qd_pad)
            if linked != Gst.PadLinkReturn.OK:
                print('failed to link demux to depth queue')
        elif IMU_ON and pad.get_property("template").name_template == "imu":
            qi_pad = queue_imu.get_static_pad("sink")
            linked = pad.link(qi_pad)
            if linked != Gst.PadLinkReturn.OK:
                print('failed to link demux to IMU queue')





    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")


    rssrc = Gst.ElementFactory.make('realsensesrc')
    rssrc.set_property('stream-type', STREAM_TYPE)
    rssrc.set_property('align', ALIGN)
    rssrc.set_property('imu_on', IMU_ON)

    rsdemux = Gst.ElementFactory.make('rsdemux', 'demux')
    rsdemux.connect('pad-added', demuxer_callback)

    vidconvert_depth = Gst.ElementFactory.make('videoconvert', 'convert-depth')
    vidsink_depth = Gst.ElementFactory.make('autovideosink', 'sink-depth')
    queue_color = Gst.ElementFactory.make('queue', 'queue_color')
    queue_depth = Gst.ElementFactory.make('queue', 'queue_depth')
    if IMU_ON:
        queue_imu = Gst.ElementFactory.make('queue', 'queue-imu')
        sink_imu = Gst.ElementFactory.make('fakesink', 'sink-imu')


    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "source_caps")
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

    # redirect to file locally 
  
    # nvvidconv_postosd = Gst.ElementFactory.make("nvvideoconvert", "convertor_postosd")
    # if not nvvidconv_postosd:
    #     sys.stderr.write(" Unable to create nvvidconv_postosd \n")
    
    # # Create a caps filter
    # caps = Gst.ElementFactory.make("capsfilter", "filter")
    # caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))
 
    

    # encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
    # if not encoder:
    #     sys.stderr.write(" Unable to create encoder")

    # file_sink = Gst.ElementFactory.make("filesink", "file-output")
    # if not file_sink:
    #     sys.stderr.write(" Unable to create file sink \n")
    # file_sink.set_property("location", output_file_path)
    # # Set sync = false to avoid late frame drops at the display-sink
    # file_sink.set_property("sync", False)


    print("Playing realsesnse")
    caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    nvvidconv.set_property('gpu-id', 0)

    streammux.set_property('width', 960)
    streammux.set_property('height', 960)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)
    pgie.set_property('config-file-path', "dstest1_pgie_config.txt")
    

    #Set properties of tracker
    config = configparser.ConfigParser()
    config.read('tracker_config.txt')
    config.sections()

    print( config)

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

    pipeline.add(rssrc)
    pipeline.add(rsdemux)
    pipeline.add(queue_color)
    pipeline.add(vidconvert_depth)
    pipeline.add(vidsink_depth)
    pipeline.add(queue_depth)
    if IMU_ON:
        pipeline.add(queue_imu)
        pipeline.add(sink_imu)
  
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    # here to default 
    pipeline.add(sink)
    # pipeline.add(nvvidconv_postosd)
    # pipeline.add(caps)
    # pipeline.add(encoder)
    # pipeline.add(file_sink)

    # we link the elements together
    # v4l2src -> nvvideoconvert -> mux -> 
    # nvinfer -> nvvideoconvert -> nvosd -> video-renderer
    print("Linking elements in the Pipeline \n")

    ret = rssrc.link(rsdemux)
    if not ret:
        print('failed to link source to demux')

    
    if IMU_ON:
        queue_imu.link(sink_imu)

    ret = queue_depth.link(vidconvert_depth)
    if not ret:
        print('failed to link queue_depth to vidconvert')

    ret = vidconvert_depth.link(vidsink_depth)
    if not ret:
        print('failed to link depth vidconvert to vidsink')




    ret= queue_color.link(vidconvsrc)
    print(ret)
    if not ret  :
        print('unable to link queue to vidconvsrc')


    # ret= caps_v4l2src.link(vidconvsrc)
    # if not ret  :
    #     print('unable to link caps_v4l2src to vidconvsrc')



    ret = vidconvsrc.link(nvvidconvsrc)
    if not ret  :
        print('unable to link videoconvert to nvvideoconvert')





    ret= nvvidconvsrc.link(caps_vidconvsrc)
    if not ret  :
        print('unable to link nvvideoconvert to caps_vidconvsrc')
    

    sinkpad = streammux.request_pad_simple("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    srcpad = caps_vidconvsrc.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of caps_vidconvsrc \n")
    ret = srcpad.link(sinkpad)
    if not ret:
        print(f"Failed to link srcpad to sinkpad: {ret}")

    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(nvvidconv)
    nvvidconv.link(nvosd)
    # here to default 
    nvosd.link(sink)
    # if not nvosd.link(nvvidconv_postosd):
    #     print('error linking nvvidconv_postosd')
    # if not nvvidconv_postosd.link(caps):
    #     print('error linking caps')
    # if not caps.link(encoder):
    #     print('error linking encoder')
    # if not encoder.link(file_sink):
    #     print('error linking  file sink')

    # create an event loop and feed gstreamer bus mesages to it
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
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe,pitch)
    
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
    
    return jsonify({"message": "Pipelines stopped."}), 200

def main():
    # Start Flask server
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    sys.exit(main())
