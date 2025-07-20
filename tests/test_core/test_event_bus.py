import asyncio
import unittest
from unittest.mock import Mock

from core.event_bus import EventBus
from core.utilities.events import Event, EventType
from core.logger import logger


class TestEventBus(unittest.TestCase):
    """
    Test suite for the EventBus to ensure its core functionalities:
    - Subscribing handlers to event types.
    - Publishing events to the correct priority queues.
    - Processing events in the correct priority order.
    - Ensuring handlers are called and queues are cleared after processing.
    """

    def setUp(self):
        """
        Initializes a fresh EventBus instance before each test.
        """
        # --- FIX: Pass the imported logger to the EventBus constructor ---
        self.bus = EventBus(logger)

    def test_subscribe_adds_handler_to_subscribers(self):
        """
        Tests if the subscribe method correctly registers a handler for an event type.
        """

        async def dummy_handler(event: Event):
            pass

        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, dummy_handler)
        self.assertIn(EventType.INFRA_BUILD_REQUEST, self.bus._subscribers)
        self.assertEqual(len(self.bus._subscribers[EventType.INFRA_BUILD_REQUEST]), 1)
        self.assertIs(
            self.bus._subscribers[EventType.INFRA_BUILD_REQUEST][0], dummy_handler
        )

    def test_publish_adds_event_to_correct_priority_queue(self):
        """
        Tests if the publish method places events into the correct internal queues
        based on their predefined priority.
        """
        high_prio_event = Event(EventType.TACTICS_UNIT_TOOK_DAMAGE)
        normal_prio_event = Event(EventType.INFRA_BUILD_REQUEST)

        self.bus.publish(high_prio_event)
        self.bus.publish(normal_prio_event)

        # Check if events are in the correct priority queues
        self.assertIn(high_prio_event, self.bus._queues[1])  # HIGH priority
        self.assertIn(normal_prio_event, self.bus._queues[2])  # NORMAL priority
        self.assertEqual(len(self.bus._queues[1]), 1)
        self.assertEqual(len(self.bus._queues[2]), 1)

    def test_process_events_executes_subscribed_handler(self):
        """
        Tests the core functionality: a published event triggers its subscribed handler.
        """
        mock_handler = Mock()

        async def async_handler(event: Event):
            mock_handler(event)

        event = Event(EventType.INFRA_BUILD_REQUEST, "payload")
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, async_handler)
        self.bus.publish(event)

        asyncio.run(self.bus.process_events())

        mock_handler.assert_called_once_with(event)

    def test_process_events_respects_priority_order(self):
        """
        Verifies that events are processed in strict priority order (CRITICAL -> HIGH -> NORMAL).
        """
        call_order = []

        async def critical_handler(event: Event):
            call_order.append("CRITICAL")

        async def high_handler(event: Event):
            # Introduce a tiny delay to ensure this doesn't accidentally run first
            await asyncio.sleep(0.001)
            call_order.append("HIGH")

        async def normal_handler(event: Event):
            call_order.append("NORMAL")

        # Subscribe handlers
        self.bus.subscribe(EventType.TACTICS_PROXY_DETECTED, critical_handler)
        self.bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, high_handler)
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, normal_handler)

        # Publish in reverse order of priority
        self.bus.publish(Event(EventType.INFRA_BUILD_REQUEST))
        self.bus.publish(Event(EventType.TACTICS_UNIT_TOOK_DAMAGE))
        self.bus.publish(Event(EventType.TACTICS_PROXY_DETECTED))

        asyncio.run(self.bus.process_events())

        # Assert the execution order was correct
        self.assertEqual(call_order, ["CRITICAL", "HIGH", "NORMAL"])

    def test_process_events_calls_multiple_subscribers_for_one_event(self):
        """
        Tests if all handlers subscribed to a single event type are executed.
        """
        mock_handler1 = Mock()
        mock_handler2 = Mock()

        async def async_handler1(event: Event):
            mock_handler1()

        async def async_handler2(event: Event):
            mock_handler2()

        event = Event(EventType.INFRA_BUILD_REQUEST)
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, async_handler1)
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, async_handler2)
        self.bus.publish(event)

        asyncio.run(self.bus.process_events())

        mock_handler1.assert_called_once()
        mock_handler2.assert_called_once()

    def test_process_events_handles_no_subscribers_gracefully(self):
        """
        Tests that publishing an event with no subscribers does not cause an error.
        """
        event = Event(EventType.INFRA_BUILD_REQUEST)
        self.bus.publish(event)

        try:
            asyncio.run(self.bus.process_events())
        except Exception as e:
            self.fail(f"process_events raised an exception with no subscribers: {e}")

    def test_process_events_clears_queues_after_processing(self):
        """
        Ensures that the event queues are empty after processing, ready for the next frame.
        """

        async def dummy_handler(event: Event):
            pass

        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, dummy_handler)
        self.bus.publish(Event(EventType.INFRA_BUILD_REQUEST))
        self.assertGreater(len(self.bus._queues[2]), 0)

        asyncio.run(self.bus.process_events())

        self.assertEqual(len(self.bus._queues[2]), 0)


if __name__ == "__main__":
    unittest.main()
