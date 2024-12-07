import os
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import configparser
# GStreamer Properties Documentation:
#
# 1. **align**: Controls the alignment between the color and depth frames.
#    - Value 0 (Default): No alignment.
#    - Value 1: Align to color frame.
#    - Value 2: Align to depth frame.
#
# 2. **imu_on**: Toggles IMU (Inertial Measurement Unit) streaming.
#    - Value True: IMU streaming is enabled.
#    - Value False: IMU streaming is disabled.
#
# 3. **stream-type**: Controls the type of video feed created by the source.
#    - Value 0: Color frames only.
#    - Value 1 (Default): Depth frames only.
#    - Value 2: Multiplexed color and depth frames.


STREAM_TYPE = 2
ALIGN = 1
IMU_ON = True
# Define constants and YOLO handling code
MUXER_BATCH_TIMEOUT_USEC = 10000

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write(f"Warning: {err}: {debug}\n")
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write(f"Error: {err}: {debug}\n")
        loop.quit()
    return True


def demuxer_callback(demuxer, pad):
    name_template = pad.get_property("template").name_template
    print(f'Pad template: {name_template}')
    
    if name_template == "color":
        qc_pad = queue_color.get_static_pad("sink")
        if qc_pad.is_linked():
            print("Color pad already linked.")
            return
        linked = pad.link(qc_pad)
        if linked != Gst.PadLinkReturn.OK:
            print('Failed to link demux to color queue')
    
    elif name_template == "depth":
        qd_pad = queue_depth.get_static_pad("sink")
        if qd_pad.is_linked():
            print("Depth pad already linked.")
            return
        linked = pad.link(qd_pad)
        if linked != Gst.PadLinkReturn.OK:
            print('Failed to link demux to depth queue')
    
    elif IMU_ON and name_template == "imu":
        qi_pad = queue_imu.get_static_pad("sink")
        if qi_pad.is_linked():
            print("IMU pad already linked.")
            return
        linked = pad.link(qi_pad)
        if linked != Gst.PadLinkReturn.OK:
            print('Failed to link demux to IMU queue')


Gst.init(None)
pipeline = Gst.Pipeline.new('realsense-stream')

rssrc = Gst.ElementFactory.make('realsensesrc')
rssrc.set_property('stream-type', STREAM_TYPE)
rssrc.set_property('align', ALIGN)
rssrc.set_property('imu_on', IMU_ON)

rsdemux = Gst.ElementFactory.make('rsdemux', 'demux')
rsdemux.connect('pad-added',demuxer_callback)
vidconvert_color = Gst.ElementFactory.make('videoconvert', 'convert-color')
vidsink_color = Gst.ElementFactory.make('autovideosink', 'sink-color')
vidconvert_depth = Gst.ElementFactory.make('videoconvert', 'convert-depth')
vidsink_depth = Gst.ElementFactory.make('autovideosink', 'sink-depth')
queue_color = Gst.ElementFactory.make('queue', 'queue_color')
queue_depth = Gst.ElementFactory.make('queue', 'queue_depth')
if IMU_ON:
    queue_imu = Gst.ElementFactory.make('queue', 'queue-imu')
    sink_imu = Gst.ElementFactory.make('fakesink', 'sink-imu')

pipeline.add(rssrc)
pipeline.add(rsdemux)
pipeline.add(vidconvert_color)
pipeline.add(vidconvert_depth)
pipeline.add(vidsink_color)
pipeline.add(vidsink_depth)
pipeline.add(queue_color)
pipeline.add(queue_depth)
if IMU_ON:
    pipeline.add(queue_imu)
    pipeline.add(sink_imu)

ret = rssrc.link(rsdemux)
if not ret:
    print('failed to link source to demux')

ret =queue_color.link(vidconvert_color)
if not ret:
    print('failed to link queue_color to vidconvert')

ret = vidconvert_color.link(vidsink_color)
if not ret:
    print('failed to link vidconvert to vidsink')

if IMU_ON:
    queue_imu.link(sink_imu)

ret =queue_depth.link(vidconvert_depth)
if not ret:
    print('failed to link queue_depth to vidconvert')

ret = vidconvert_depth.link(vidsink_depth)
if not ret:
    print('failed to link depth vidconvert to vidsink')

# Start pipeline and listen for messages
loop = GLib.MainLoop()
bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect("message", bus_call, loop)

pipeline.set_state(Gst.State.PLAYING)

try:
    print("Running pipeline...")
    loop.run()
except KeyboardInterrupt:
    print("Interrupt received, stopping pipeline...")

pipeline.set_state(Gst.State.NULL)
