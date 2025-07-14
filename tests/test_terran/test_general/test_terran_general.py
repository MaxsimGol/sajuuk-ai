from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock, call

# The class we are testing
from terran.general.terran_general import TerranGeneral

# Mock the dependencies
from core.global_cache import GlobalCache
from core.event_bus import EventBus
from core.frame_plan import FramePlan


class TestTerranGeneral(IsolatedAsyncioTestCase):
    """
    Tests the TerranGeneral to ensure it correctly orchestrates its Directors.
    """

    def setUp(self):
        """
        Set up a TerranGeneral instance and mock all its dependencies.
        """
        # The General requires a BotAI instance in its constructor. A simple
        # Mock is sufficient as we are not testing BotAI functionality here.
        mock_bot = Mock()
        self.general = TerranGeneral(mock_bot)

        # Replace the real Director instances with AsyncMocks.
        # This allows us to track calls and control return values without
        # executing the real directors' complex logic.
        self.general.infrastructure_director.execute = AsyncMock(return_value=[])
        self.general.capability_director.execute = AsyncMock(return_value=[])
        self.general.tactical_director.execute = AsyncMock(return_value=[])

        # Create mock objects for the arguments passed to execute_step
        self.mock_cache = Mock(spec=GlobalCache)
        self.mock_plan = Mock(spec=FramePlan)
        self.mock_bus = Mock(spec=EventBus)

    async def test_execute_step_calls_directors_in_correct_order(self):
        """
        Verify that execute_step calls each Director exactly once and in the
        strategically-defined order: Infrastructure -> Capabilities -> Tactics.
        """
        # Arrange: Use a parent mock to track the sequence of calls.
        call_tracker = Mock()
        call_tracker.attach_mock(self.general.infrastructure_director.execute, "infra")
        call_tracker.attach_mock(self.general.capability_director.execute, "capa")
        call_tracker.attach_mock(self.general.tactical_director.execute, "tact")

        # Act: Execute the method under test.
        await self.general.execute_step(self.mock_cache, self.mock_plan, self.mock_bus)

        # Assert: Check that the calls were made in the expected sequence.
        expected_call_order = [
            call.infra(self.mock_cache, self.mock_plan, self.mock_bus),
            call.capa(self.mock_cache, self.mock_plan, self.mock_bus),
            call.tact(self.mock_cache, self.mock_plan, self.mock_bus),
        ]
        self.assertEqual(call_tracker.mock_calls, expected_call_order)

    async def test_execute_step_aggregates_actions_from_all_directors(self):
        """
        Verify that the returned list of command functors is a correct
        aggregation of the lists returned by each director.
        """
        # Arrange: Define unique return values for each mocked director.
        # These are dummy functors for testing aggregation.
        infra_action = lambda: "infra_action"
        capa_action = lambda: "capa_action"
        tact_action = lambda: "tact_action"

        self.general.infrastructure_director.execute.return_value = [infra_action]
        self.general.capability_director.execute.return_value = [capa_action]
        self.general.tactical_director.execute.return_value = [tact_action]

        # Act: Execute the method and get the aggregated list.
        final_actions = await self.general.execute_step(
            self.mock_cache, self.mock_plan, self.mock_bus
        )

        # Assert: Check that the final list contains all actions.
        self.assertEqual(len(final_actions), 3)
        self.assertIn(infra_action, final_actions)
        self.assertIn(capa_action, final_actions)
        self.assertIn(tact_action, final_actions)
