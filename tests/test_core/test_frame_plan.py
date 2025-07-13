import unittest
from sc2.ids.unit_typeid import UnitTypeId

from core.frame_plan import FramePlan, ArmyStance, ResourceBudget


class TestFramePlan(unittest.TestCase):
    """
    Tests the FramePlan class to ensure it correctly stores and updates
    strategic intentions for a single game step.
    """

    def setUp(self):
        """Create a new, clean FramePlan instance for each test."""
        self.plan = FramePlan()

    def test_initialization_sets_correct_defaults(self):
        """
        Verify that a new FramePlan is created with the expected default state.
        """
        # Assert default budget is correct
        self.assertIsInstance(self.plan.resource_budget, ResourceBudget)
        self.assertEqual(self.plan.resource_budget.infrastructure, 20)
        self.assertEqual(self.plan.resource_budget.capabilities, 80)
        self.assertEqual(self.plan.resource_budget.tactics, 0)

        # Assert default stance is correct
        self.assertEqual(self.plan.army_stance, ArmyStance.DEFENSIVE)

        # Assert production requests are empty
        self.assertIsInstance(self.plan.production_requests, set)
        self.assertEqual(len(self.plan.production_requests), 0)

    def test_set_budget_updates_resource_budget(self):
        """
        Verify that calling set_budget correctly modifies the resource_budget
        attribute with new values.
        """
        # Act
        self.plan.set_budget(infrastructure=60, capabilities=40, tactics=0)

        # Assert
        self.assertEqual(self.plan.resource_budget.infrastructure, 60)
        self.assertEqual(self.plan.resource_budget.capabilities, 40)
        self.assertEqual(self.plan.resource_budget.tactics, 0)

    def test_set_army_stance_updates_stance(self):
        """
        Verify that calling set_army_stance correctly modifies the army_stance
        attribute.
        """
        # Act
        self.plan.set_army_stance(ArmyStance.AGGRESSIVE)

        # Assert
        self.assertEqual(self.plan.army_stance, ArmyStance.AGGRESSIVE)

    def test_add_production_request_adds_item_to_set(self):
        """
        Verify that adding production requests populates the set correctly.
        """
        # Assert initial state
        self.assertEqual(len(self.plan.production_requests), 0)

        # Act
        request1 = UnitTypeId.MARINE
        request2 = UnitTypeId.MISSILETURRET
        self.plan.add_production_request(request1)
        self.plan.add_production_request(request2)

        # Assert
        self.assertEqual(len(self.plan.production_requests), 2)
        self.assertIn(request1, self.plan.production_requests)
        self.assertIn(request2, self.plan.production_requests)

    def test_add_production_request_handles_duplicates(self):
        """
        Verify that adding the same request multiple times only results
        in one entry, as expected for a set.
        """
        # Act
        request = UnitTypeId.SIEGETANK
        self.plan.add_production_request(request)
        self.plan.add_production_request(request)

        # Assert
        self.assertEqual(len(self.plan.production_requests), 1)
        self.assertIn(request, self.plan.production_requests)
