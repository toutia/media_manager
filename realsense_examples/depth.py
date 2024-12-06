import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GLib

def on_new_sample(sink):
    sample = sink.emit('pull-sample')
    if sample:
        buf = sample.get_buffer()
        caps = sample.get_caps()
        timestamp = buf.pts # / Gst.SECOND  # Convert PTS (nanoseconds) to seconds
        print(f"Depth frame timestamp: {timestamp:.2f} seconds")
        # Process buffer data here (e.g., convert to numpy array)
    return Gst.FlowReturn.OK

def main():
    Gst.init(None)

    pipeline_str = (
        "realsensesrc ! "
        "rsdemux name=demux "
        "demux.depth ! videoconvert ! appsink name=depth_sink"
    )
    pipeline = Gst.parse_launch(pipeline_str)

    depth_sink = pipeline.get_by_name("depth_sink")
    depth_sink.set_property("emit-signals", True)
    depth_sink.connect("new-sample", on_new_sample)

    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        print("Shutting down...")
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()
