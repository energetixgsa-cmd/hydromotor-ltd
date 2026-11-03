"""Executable policy tests; no Odoo/SQL/ACL simulation or installation claim."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'hydromotor_parts_kits/models/sale_machine_policy.py'


class TestMachinePolicy(unittest.TestCase):
    def policy(self):
        self.assertTrue(POLICY.is_file(), 'Sale-line machine defaulting policy is missing')
        spec = importlib.util.spec_from_file_location('sale_machine_policy', POLICY)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_new_line_inherits_order_machine_and_tracks_origin(self):
        values = {'product_id': 7}
        result = self.policy().prepare_line_values(values, 41)
        self.assertEqual(result['x_hm_parts_machine_id'], 41)
        self.assertTrue(result['x_hm_use_order_machine'])
        self.assertEqual(values, {'product_id': 7}, 'must not mutate caller values')
    def test_explicit_line_machine_including_false_is_never_overwritten(self):
        for explicit in (99, False):
            with self.subTest(explicit=explicit):
                result = self.policy().prepare_line_values({'x_hm_parts_machine_id': explicit}, 41)
                self.assertEqual(result['x_hm_parts_machine_id'], explicit)
                self.assertFalse(result['x_hm_use_order_machine'])
        self.assertEqual(self.policy().prepare_line_values({
            'x_hm_use_order_machine': True, 'x_hm_parts_machine_id': 99}, 41)
            ['x_hm_parts_machine_id'], 41)
        self.assertFalse(self.policy().prepare_line_values({'display_type': 'line_note'}, 41)
                         ['x_hm_parts_machine_id'])
    def test_company_customer_and_retired_validation(self):
        policy = self.policy()
        self.assertTrue(hasattr(policy, 'machine_link_error'), 'Server validation policy is missing')
        self.assertIsNone(policy.machine_link_error(1, 10, 1, 10, False))
        self.assertEqual(policy.machine_link_error(1, 10, 2, 10, False), 'company')
        self.assertEqual(policy.machine_link_error(1, 10, 1, 20, False), 'customer')
        self.assertEqual(policy.machine_link_error(1, 10, 1, 10, True), 'retired')
        self.assertEqual(policy.machine_link_error(1, False, 1, False, False), 'customer')
    def test_parts_history_distinguishes_offer_sale_delivery_and_return(self):
        policy = self.policy()
        self.assertTrue(hasattr(policy, 'parts_history_state'), 'Parts history status is missing')
        cases = [('draft', 2, 0, 'offered'), ('sent', 2, 0, 'offered'),
                 ('cancel', 2, 1, 'cancelled'), ('sale', 2, 0, 'sold'),
                 ('sale', 2, 1, 'part_delivered'), ('sale', 2, 2, 'delivered'),
                 ('sale', 2, -1, 'returned')]
        for state, ordered, delivered, expected in cases:
            with self.subTest(state=state, delivered=delivered):
                self.assertEqual(policy.parts_history_state(state, ordered, delivered), expected)


if __name__ == '__main__':
    unittest.main()
