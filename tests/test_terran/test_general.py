# tests/test_terran/test_general.py

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, Mock, call, AsyncMock

from generals.terran_general import TerranGeneral
from core.global_cache import GlobalCache
from core.event_bus import EventBus


class TestTerranGeneral(IsolatedAsyncioTestCase):
    """
    Tests the orchestration logic of the TerranGeneral.
    """

    # We do not need to patch the classes here, as we can assign mock instances directly.
    async def test_execute_step_orchestrates_managers_in_order(self):
        """
        Verify that execute_step calls each manager's execute() method
        once and in the correct sequence: Economy -> Production -> Military.
        """
        # Arrange: Instantiate the General with a mock BotAI object.
        mock_bot = Mock()
        general = TerranGeneral(mock_bot)

        # Arrange: Replace the real manager instances with AsyncMocks.
        # This is the key change to handle the 'await' keyword.
        general.economy_manager.execute = AsyncMock(return_value=[])
        general.production_manager.execute = AsyncMock(return_value=[])
        general.military_manager.execute = AsyncMock(return_value=[])

        # Arrange: Create mock objects for the cache and bus.
        mock_cache = Mock(GlobalCache)
        mock_bus = Mock(EventBus)

        # Arrange: Use a parent mock to track the call order.
        mock_tracker = Mock()
        mock_tracker.attach_mock(general.economy_manager.execute, "economy")
        mock_tracker.attach_mock(general.production_manager.execute, "production")
        mock_tracker.attach_mock(general.military_manager.execute, "military")

        # Act: Call the method under test.
        await general.execute_step(mock_cache, mock_bus)

        # Assert: Verify that each async manager was awaited exactly once.
        general.economy_manager.execute.assert_awaited_once_with(mock_cache, mock_bus)
        general.production_manager.execute.assert_awaited_once_with(
            mock_cache, mock_bus
        )
        general.military_manager.execute.assert_awaited_once_with(mock_cache, mock_bus)

        # Assert: Verify the specific order of the calls.
        expected_call_order = [
            call.economy(mock_cache, mock_bus),
            call.production(mock_cache, mock_bus),
            call.military(mock_cache, mock_bus),
        ]
        mock_tracker.assert_has_calls(expected_call_order)
