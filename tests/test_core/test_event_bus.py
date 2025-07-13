# tests/test_core/test_event_bus.py

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call

from core.event_bus import EventBus
from core.utilities.events import Event, EventType, BuildRequestPayload


class TestEventBus(IsolatedAsyncioTestCase):
    """
    Tests the core functionality of the EventBus, including subscription,
    publishing, and prioritized processing.
    """

    def setUp(self):
        """Set up a new EventBus instance for each test."""
        self.bus = EventBus()

    async def test_subscribe_and_process_single_event(self):
        """Verify a handler is called when its subscribed event is processed."""
        # Arrange
        mock_handler = AsyncMock()
        event_to_publish = Event(
            EventType.INFRA_BUILD_REQUEST, payload=BuildRequestPayload(item_id=1)
        )
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, mock_handler)

        # Act
        self.bus.publish(event_to_publish)
        await self.bus.process_events()

        # Assert
        mock_handler.assert_awaited_once_with(event_to_publish)

    async def test_process_events_respects_priority(self):
        """
        Verify that CRITICAL events are processed before NORMAL events,
        regardless of the order they were published.
        """
        # Arrange
        call_tracker = Mock()
        normal_handler = AsyncMock()
        critical_handler = AsyncMock()

        call_tracker.attach_mock(normal_handler, "normal_handler_call")
        call_tracker.attach_mock(critical_handler, "critical_handler_call")

        normal_event = Event(EventType.INFRA_BUILD_REQUEST)
        critical_event = Event(EventType.TACTICS_PROXY_DETECTED)

        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, normal_handler)
        self.bus.subscribe(EventType.TACTICS_PROXY_DETECTED, critical_handler)

        # Act: Publish normal event first, then critical
        self.bus.publish(normal_event)
        self.bus.publish(critical_event)
        await self.bus.process_events()

        # Assert
        # The critical handler must be called before the normal handler.
        expected_call_order = [
            call.critical_handler_call(critical_event),
            call.normal_handler_call(normal_event),
        ]
        self.assertEqual(call_tracker.mock_calls, expected_call_order)

    async def test_queue_is_cleared_after_processing(self):
        """Verify that an event is not processed twice."""
        # Arrange
        mock_handler = AsyncMock()
        event = Event(EventType.INFRA_BUILD_REQUEST)
        self.bus.subscribe(EventType.INFRA_BUILD_REQUEST, mock_handler)
        self.bus.publish(event)

        # Act & Assert 1
        await self.bus.process_events()
        mock_handler.assert_awaited_once()

        # Act & Assert 2: Process again
        mock_handler.reset_mock()
        await self.bus.process_events()
        mock_handler.assert_not_awaited()

    async def test_multiple_subscribers_are_called(self):
        """Verify that all handlers subscribed to an event are called."""
        # Arrange
        handler_one = AsyncMock()
        handler_two = AsyncMock()
        event = Event(EventType.TACTICS_UNIT_TOOK_DAMAGE)

        self.bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, handler_one)
        self.bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, handler_two)

        # Act
        self.bus.publish(event)
        await self.bus.process_events()

        # Assert
        handler_one.assert_awaited_once_with(event)
        handler_two.assert_awaited_once_with(event)

    async def test_no_error_if_no_subscribers_for_event(self):
        """
        Verify that publishing an event with no subscribers does not
        cause an error.
        """
        # Arrange
        event = Event(EventType.TACTICS_ENEMY_TECH_SCOUTED)

        # Act
        self.bus.publish(event)
        try:
            await self.bus.process_events()
        except Exception as e:
            self.fail(f"process_events() raised an exception unexpectedly: {e}")
