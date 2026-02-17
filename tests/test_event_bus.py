from trade_engine.core.event_bus import EventBus


def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    def listener(event):
        received.append((event.event_type, event.payload.get("x")))

    bus.subscribe("alpha", listener)
    bus.publish("alpha", {"x": 10})

    assert received == [("alpha", 10)]
