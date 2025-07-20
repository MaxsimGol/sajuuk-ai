import unittest
from unittest.mock import AsyncMock

from core.event_bus import (
    EventBus,
    EVENT_PRIORITY_CRITICAL,
    EVENT_PRIORITY_HIGH,
    EVENT_PRIORITY_NORMAL,
)
from core.utilities.events import Event, EventType, BuildRequestPayload


class TestEventBus(unittest.IsolatedAsyncioTestCase):
    """
    Tests the functionality of the EventBus, ensuring it correctly handles
    subscribing, publishing, and prioritized processing of events.
    """

    def setUp(self):
        """
        This method is called before each test function, ensuring a fresh
        EventBus instance for every test case.
        """
        self.bus = EventBus()

    def test_subscribe_adds_handler_to_subscribers(self):
        """
        Tests if the subscribe method correctly registers a handler for an event type.
        """
        # Arrange
        mock_handler = AsyncMock()
        event_type = EventType.INFRA_BUILD_REQUEST

        # Act
        self.bus.subscribe(event_type, mock_handler)

        # Assert
        self.assertIn(event_type, self.bus._subscribers)
        self.assertIn(mock_handler, self.bus._subscribers[event_type])
        self.assertEqual(len(self.bus._subscribers[event_type]), 1)

    def test_publish_adds_event_to_correct_priority_queue(self):
        """
        Tests if the publish method places events into the correct internal queues
        based on their defined priority.
        """
        # Arrange
        # Note: We need to use EventTypes that are explicitly defined in EVENT_TYPE_PRIORITIES
        # for this test to be meaningful.
        critical_event = Event(EventType.TACTICS_PROXY_DETECTED)
        high_event = Event(EventType.TACTICS_UNIT_TOOK_DAMAGE)
        normal_event = Event(EventType.INFRA_BUILD_REQUEST)

        # Act
        self.bus.publish(critical_event)
        self.bus.publish(high_event)
        self.bus.publish(normal_event)

        # Assert
        self.assertEqual(len(self.bus._queues[EVENT_PRIORITY_CRITICAL]), 1)
        self.assertIn(critical_event, self.bus._queues[EVENT_PRIORITY_CRITICAL])

        self.assertEqual(len(self.bus._queues[EVENT_PRIORITY_HIGH]), 1)
        self.assertIn(high_event, self.bus._queues[EVENT_PRIORITY_HIGH])

        self.assertEqual(len(self.bus._queues[EVENT_PRIORITY_NORMAL]), 1)
        self.assertIn(normal_event, self.bus._queues[EVENT_PRIORITY_NORMAL])

    async def test_process_events_executes_subscribed_handler(self):
        """
        Tests the core functionality: a published event triggers its subscribed handler.
        """
        # Arrange
        mock_handler = AsyncMock()
        event_type = EventType.INFRA_BUILD_REQUEST
        event_payload = BuildRequestPayload(item_id=1)
        event = Event(event_type, event_payload)

        self.bus.subscribe(event_type, mock_handler)
        self.bus.publish(event)

        # Act
        await self.bus.process_events()

        # Assert
        mock_handler.assert_awaited_once_with(event)

    async def test_process_events_respects_priority_order(self):
        """
        Verifies that events are processed in strict priority order (CRITICAL -> HIGH -> NORMAL).
        """
        # Arrange
        call_order = []

        async def critical_handler(event):
            call_order.append("CRITICAL")

        async def high_handler(event):
            call_order.append("HIGH")

        async def normal_handler(event):
            call_order.append("NORMAL")

        self.bus.subscribe(EventType.TACTICS_PROXY_DETECTED, critical_handler)
        self.bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, high_handler)
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, normal_handler)

        # Publish in a jumbled order to test the sorting
        self.bus.publish(Event(EventType.INFRA_BUILD_REQUEST))
        self.bus.publish(Event(EventType.TACTICS_PROXY_DETECTED))
        self.bus.publish(Event(EventType.TACTICS_UNIT_TOOK_DAMAGE))

        # Act
        await self.bus.process_events()

        # Assert
        self.assertEqual(call_order, ["CRITICAL", "HIGH", "NORMAL"])

    async def test_process_events_clears_queues_after_processing(self):
        """
        Ensures that the event queues are empty after processing, ready for the next frame.
        """
        # Arrange
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, AsyncMock())
        self.bus.publish(Event(EventType.INFRA_BUILD_REQUEST))
        self.assertFalse(
            not self.bus._queues[EVENT_PRIORITY_NORMAL]
        )  # Queue should not be empty

        # Act
        await self.bus.process_events()

        # Assert
        self.assertTrue(not self.bus._queues[EVENT_PRIORITY_CRITICAL])
        self.assertTrue(not self.bus._queues[EVENT_PRIORITY_HIGH])
        self.assertTrue(not self.bus._queues[EVENT_PRIORITY_NORMAL])

    async def test_process_events_handles_no_subscribers_gracefully(self):
        """
        Tests that publishing an event with no subscribers does not cause an error.
        """
        # Arrange
        event = Event(EventType.TACTICS_ENEMY_TECH_SCOUTED)
        self.bus.publish(event)

        # Act & Assert
        try:
            await self.bus.process_events()
            # If we get here without an exception, the test has passed.
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"process_events raised an exception with no subscribers: {e}")

    async def test_process_events_calls_multiple_subscribers_for_one_event(self):
        """
        Tests if all handlers subscribed to a single event type are executed.
        """
        # Arrange
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        event_type = EventType.INFRA_BUILD_REQUEST
        event = Event(event_type)

        self.bus.subscribe(event_type, handler1)
        self.bus.subscribe(event_type, handler2)
        self.bus.publish(event)

        # Act
        await self.bus.process_events()

        # Assert
        handler1.assert_awaited_once_with(event)
        handler2.assert_awaited_once_with(event)


if __name__ == "__main__":
    unittest.main()
