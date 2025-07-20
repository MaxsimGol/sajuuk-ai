import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Coroutine

from core.utilities.events import Event, EventType
from core.utilities.constants import (
    EVENT_PRIORITY_CRITICAL,
    EVENT_PRIORITY_HIGH,
    EVENT_PRIORITY_NORMAL,
)

if TYPE_CHECKING:
    from loguru import Logger

    # A handler is an async function that takes an Event and returns nothing.
    # Coroutine[None, None, None] is the precise way to say: "This is an async
    # function that I will await, but I don't expect it to return anything,
    # and I won't be sending data into it while it runs."
    EventHandler = Callable[[Event], Coroutine[None, None, None]]

# This map defines the priority for each event type.
# It is centrally located here to ensure all events are categorized.
EVENT_TYPE_PRIORITIES = {
    # Critical Events (Highest Priority)
    EventType.TACTICS_PROXY_DETECTED: EVENT_PRIORITY_CRITICAL,
    # High Priority Events
    EventType.TACTICS_UNIT_TOOK_DAMAGE: EVENT_PRIORITY_HIGH,
    # Normal Priority Events (Default)
    EventType.INFRA_BUILD_REQUEST: EVENT_PRIORITY_NORMAL,
    EventType.INFRA_BUILD_REQUEST_FAILED: EVENT_PRIORITY_NORMAL,
    EventType.TACTICS_ENEMY_TECH_SCOUTED: EVENT_PRIORITY_NORMAL,
}


class EventBus:
    """
    The bot's prioritized, asynchronous nervous system.

    This class implements a message queue that processes events based on a
    defined priority level. It decouples components, allowing a "scout" to
    report a threat without knowing who or what will handle it.

    Workflow:
    1. Components `subscribe` a handler function to a specific `EventType`.
    2. Components `publish` an `Event` object. This is a non-blocking call
    that adds the event to a priority queue.
    3. The `TerranGeneral` calls `process_events` once per frame. This method
    executes all queued handlers, starting with the highest priority,
    running them concurrently via asyncio.gather.
    """

    def __init__(self, logger: "Logger"):
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._queues: dict[int, list[Event]] = {
            EVENT_PRIORITY_CRITICAL: [],
            EVENT_PRIORITY_HIGH: [],
            EVENT_PRIORITY_NORMAL: [],
        }
        self.logger = logger

    def subscribe(self, event_type: EventType, handler: "EventHandler"):
        """
        Subscribes a handler coroutine to a specific event type.

        :param event_type: The EventType to listen for.
        :param handler: The async function to execute when the event is processed.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event):
        """
        Publishes an event by adding it to the appropriate priority queue.

        This is a non-blocking operation. The event will be processed later
        when process_events() is called.

        :param event: The Event object containing the event_type and payload.
        """
        priority = EVENT_TYPE_PRIORITIES.get(event.event_type, EVENT_PRIORITY_NORMAL)
        self._queues[priority].append(event)
        self.logger.debug(
            f"Event Published: {event.event_type.name} with priority {priority}. Payload: {event.payload}"
        )

    async def process_events(self):
        """
        Executes all queued event handlers, in order of priority.

        This should be called once per game step by the General. It ensures
        that all CRITICAL events are handled before all HIGH events, and so on.
        Handlers within the same priority level are executed concurrently.
        """
        # Iterate through priorities in ascending order (0=CRITICAL, 1=HIGH, etc.)
        for priority in sorted(self._queues.keys()):
            event_queue = self._queues[priority]
            if not event_queue:
                continue

            self.logger.debug(
                f"Processing {len(event_queue)} events with priority {priority}."
            )

            tasks = []
            for event in event_queue:
                if event.event_type in self._subscribers:
                    for handler in self._subscribers[event.event_type]:
                        tasks.append(handler(event))
            if tasks:
                await asyncio.gather(*tasks)

            # Clear the queue for this priority level after processing
            event_queue.clear()
