import unittest
from sc2.ids.unit_typeid import UnitTypeId

from core.frame_plan import FramePlan, ArmyStance, ResourceBudget


class TestFramePlan(unittest.TestCase):
    """
    Tests the functionality of the FramePlan class, ensuring it correctly
    manages the strategic intentions for a single game frame.
    """

    def setUp(self):
        """
        This method is called before each test function, ensuring a fresh
        FramePlan instance for every test case.
        """
        self.plan = FramePlan()

    def test_init_sets_default_values(self):
        """
        Tests if a newly instantiated FramePlan has the correct default state.
        This is crucial for ensuring predictable behavior at the start of each frame.
        """
        # Arrange: The FramePlan is created in setUp().

        # Act: (No action needed, we are testing the initial state).

        # Assert
        # The default budget should prioritize capabilities over infrastructure.
        self.assertIsInstance(self.plan.resource_budget, ResourceBudget)
        self.assertEqual(self.plan.resource_budget.infrastructure, 20)
        self.assertEqual(self.plan.resource_budget.capabilities, 80)
        self.assertEqual(self.plan.resource_budget.tactics, 0)

        # The default army stance should be defensive.
        self.assertEqual(self.plan.army_stance, ArmyStance.DEFENSIVE)

        # The production request list should start empty.
        self.assertIsInstance(self.plan.production_requests, set)
        self.assertEqual(len(self.plan.production_requests), 0)

    def test_set_budget_updates_budget_correctly(self):
        """
        Tests if the set_budget method correctly updates the resource allocation.
        """
        # Arrange
        new_infra_budget = 50
        new_capa_budget = 50

        # Act
        self.plan.set_budget(
            infrastructure=new_infra_budget, capabilities=new_capa_budget
        )

        # Assert
        self.assertEqual(self.plan.resource_budget.infrastructure, new_infra_budget)
        self.assertEqual(self.plan.resource_budget.capabilities, new_capa_budget)
        self.assertEqual(self.plan.resource_budget.tactics, 0)

    def test_set_budget_with_tactics_updates_all_values(self):
        """
        Tests if the set_budget method correctly updates all three budget components.
        """
        # Arrange
        new_infra_budget = 10
        new_capa_budget = 80
        new_tactics_budget = 10

        # Act
        self.plan.set_budget(
            infrastructure=new_infra_budget,
            capabilities=new_capa_budget,
            tactics=new_tactics_budget,
        )

        # Assert
        self.assertEqual(self.plan.resource_budget.infrastructure, new_infra_budget)
        self.assertEqual(self.plan.resource_budget.capabilities, new_capa_budget)
        self.assertEqual(self.plan.resource_budget.tactics, new_tactics_budget)

    def test_set_army_stance_updates_stance(self):
        """
        Tests if the set_army_stance method correctly changes the army's tactical posture.
        """
        # Arrange
        new_stance = ArmyStance.AGGRESSIVE

        # Act
        self.plan.set_army_stance(new_stance)

        # Assert
        self.assertEqual(self.plan.army_stance, new_stance)

        # Act again with another stance to ensure it can be changed multiple times
        another_stance = ArmyStance.HARASS
        self.plan.set_army_stance(another_stance)
        self.assertEqual(self.plan.army_stance, another_stance)

    def test_add_production_request_adds_item_to_set(self):
        """
        Tests if production requests can be successfully added to the plan.
        """
        # Arrange
        request_one = UnitTypeId.SUPPLYDEPOT
        request_two = UnitTypeId.BARRACKS

        # Act
        self.plan.add_production_request(request_one)

        # Assert
        self.assertEqual(len(self.plan.production_requests), 1)
        self.assertIn(request_one, self.plan.production_requests)

        # Act again to ensure a second item can be added
        self.plan.add_production_request(request_two)
        self.assertEqual(len(self.plan.production_requests), 2)
        self.assertIn(request_two, self.plan.production_requests)

    def test_add_production_request_handles_duplicates(self):
        """
        Tests that adding the same production request multiple times does not
        create duplicate entries, as it's managed by a set.
        """
        # Arrange
        request = UnitTypeId.MARINE

        # Act
        self.plan.add_production_request(request)
        self.plan.add_production_request(request)
        self.plan.add_production_request(request)

        # Assert
        self.assertEqual(len(self.plan.production_requests), 1)
        self.assertIn(request, self.plan.production_requests)


if __name__ == "__main__":
    unittest.main()
