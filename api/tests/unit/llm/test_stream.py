from src.llm.stream import SseMeter

STREAM = (
    b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_1",'
    b'"usage":{"input_tokens":100,"output_tokens":1}}}\n\n'
    b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":20,'
    b'"cost":0.0042}}\n\n'
    b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
    b"event: data\ndata: [DONE]\n\n"
)


def test_events_split_across_chunks_are_relayed_whole_without_done():
    meter = SseMeter()
    out = b"".join(meter.feed(STREAM[i : i + 7]) for i in range(0, len(STREAM), 7))
    out += meter.flush()
    assert out == STREAM.split(b"event: data")[0]
    usage = meter.usage
    assert (usage.generation_id, usage.input_tokens, usage.output_tokens) == ("msg_1", 100, 20)
    assert usage.cost_micros == 4200
    assert usage.stopped


def test_an_error_event_is_kept_and_recorded():
    meter = SseMeter()
    frame = b'event: error\ndata: {"type":"error","error":{"message":"overloaded"}}\n\n'
    assert meter.feed(frame) == frame
    assert meter.usage.error == "overloaded"
