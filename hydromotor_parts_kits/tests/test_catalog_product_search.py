"""Odoo 19 integration regressions. Run on an isolated, neutralized test DB.

These are real ORM/SQL/registry tests, NOT part of tests_local's mock suite.
"""
from uuid import uuid4

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from ..models.quotation_service import search_catalog_product


@tagged('post_install', '-at_install')
class TestCatalogProductSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Kit = cls.env['x_hm_parts_kit']
        cls.Product = cls.env['product.product']
        cls.service = cls.env['hydromotor.parts.quotation.service']
        cls.code = '000' + str(uuid4().int)
        cls.other_company = cls.env['res.company'].create({'name': 'Catalog search company B'})
        cls.product = cls.Product.create({
            'name': 'Catalog Search Motor Alpha', 'default_code': cls.code,
            'sale_ok': True, 'company_id': False,
        })
        cls.override = cls.Product.create({
            'name': 'Catalog Search Override', 'default_code': cls.code + '9',
            'sale_ok': False, 'company_id': False,
        })
        cls.implicit = cls.Kit.create({
            'x_name': 'Implicit catalog test', 'x_company_id': cls.env.company.id,
            'x_active': True, 'x_note': 'Възел %s, чертеж 01' % cls.code,
        })
        cls.explicit = cls.Kit.create({
            'x_name': 'Explicit catalog test', 'x_company_id': cls.env.company.id,
            'x_active': True, 'x_note': cls.implicit.x_note,
            'x_assembly_product_id': cls.override.id,
        })
        cls.empty = cls.Kit.create({
            'x_name': 'No catalog test', 'x_company_id': cls.env.company.id,
            'x_active': True, 'x_note': 'No assembly marker',
        })
        cls.malformed = cls.Kit.create({
            'x_name': 'Malformed catalog test', 'x_company_id': cls.env.company.id,
            'x_active': True, 'x_note': 'възел %s, чертеж 01' % cls.code,
        })
        cls.fixtures = cls.implicit | cls.explicit | cls.empty | cls.malformed
        cls.reader = new_test_user(
            cls.env, login='catalog_search_' + uuid4().hex,
            groups='base.group_user,hydromotor_service.group_service_user',
            company_id=cls.env.company.id,
            company_ids=[Command.set([cls.env.company.id])],
        )

    def _assert_computed_search(self, operator, value, kits=None):
        kits = self.fixtures if kits is None else kits
        service = kits.env['hydromotor.parts.quotation.service']
        # Use the existing stored explicit many2one as the native operator oracle.
        # Virtual records are in-memory only; never write the computed result.
        expected = set()
        for kit in kits:
            product = service._assembly_product(kit)
            kit.invalidate_recordset(['x_catalog_product_id'])
            self.assertEqual(kit.x_catalog_product_id, product)
            probe = kits.new({'x_assembly_product_id': product.id})
            if probe.filtered_domain([('x_assembly_product_id', operator, value)]):
                expected.add(kit.id)
        actual = kits.search([
            ('id', 'in', kits.ids), ('x_catalog_product_id', operator, value),
        ])
        self.assertEqual(set(actual.ids), expected, (operator, value))
        return actual

    def test_manual_field_is_searchable_after_registry_load(self):
        field = self.Kit._fields['x_catalog_product_id']
        self.assertTrue(field.manual)
        self.assertFalse(field.store)
        self.assertIs(field.search, search_catalog_product)
        metadata = self.Kit.fields_get(['x_catalog_product_id'])['x_catalog_product_id']
        self.assertTrue(metadata['searchable'])
        self.assertEqual(set(self._assert_computed_search('!=', False).ids),
                         {self.implicit.id, self.explicit.id})

    def test_false_ids_negative_and_in_operators(self):
        for operator, value in [
            ('=', False), ('!=', False), ('=', self.product.id),
            ('!=', self.product.id), ('in', [self.product.id]),
            ('not in', [self.product.id]), ('in', [False, self.product.id]),
            ('not in', [False, self.product.id]), ('in', []), ('not in', []),
            ('=', 2147483647), ('=?', False),
        ]:
            with self.subTest(operator=operator, value=value):
                self._assert_computed_search(operator, value)

    def test_name_operators_use_native_product_name_search(self):
        for operator, value in [
            ('=', self.product.name), ('!=', self.product.name),
            ('in', [False, self.product.name, self.override.id]),
            ('not in', [self.product.name]),
            ('like', 'Motor'), ('ilike', 'motor'), ('not ilike', 'motor'),
            ('not like', 'Motor'), ('=like', 'Catalog Search Motor%'),
            ('=ilike', 'catalog search motor%'), ('like', ''), ('ilike', ''),
            ('=like', ''), ('=ilike', ''), ('not ilike', ''),
        ]:
            with self.subTest(operator=operator, value=value):
                self._assert_computed_search(operator, value)

    def test_product_edits_and_ambiguity_are_dynamic(self):
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))
        duplicate = self.product.copy({'default_code': self.code})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        duplicate.write({'sale_ok': False})
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))
        self.product.write({'sale_ok': False})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        self.product.write({'sale_ok': True, 'default_code': self.code + '8'})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        self.product.write({'default_code': self.code})
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))

    def test_archive_context_and_explicit_precedence(self):
        self.product.write({'active': False})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        self.assertIn(self.implicit, self._assert_computed_search(
            '=', self.product.id, self.fixtures.with_context(active_test=False)))
        self.explicit.write({'x_assembly_product_id': self.product.id})
        self.assertIn(self.explicit, self._assert_computed_search('=', self.product.id))
        self._assert_computed_search('ilike', 'Motor')
        self._assert_computed_search('not ilike', 'Motor')

    def test_exact_regex_leading_zero_and_note_edits(self):
        self.assertEqual(self.service._catalog_code(self.implicit), self.code)
        self.implicit.write({'x_note': 'Възел\u00a0%s\t,\nчертеж X' % self.code})
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))
        self.implicit.write({'x_note': 'Възел %s, друга дума' % self.code})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        self.implicit.write({'x_note': False})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))

    def test_company_eligibility_uses_kit_company(self):
        self.product.write({'company_id': self.other_company.id})
        self.assertIn(self.implicit, self._assert_computed_search('=', False))
        self.implicit.write({'x_company_id': self.other_company.id})
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))
        self.product.write({'company_id': False})
        self.assertIn(self.implicit, self._assert_computed_search('=', self.product.id))

    def test_product_and_kit_record_rules_are_not_bypassed(self):
        duplicate = self.product.copy({'default_code': self.code})
        self.env['ir.rule'].create({
            'name': 'Catalog hide duplicate',
            'model_id': self.env['ir.model']._get_id('product.product'),
            'domain_force': repr([('id', '!=', duplicate.id)]),
        })
        self.env['ir.rule'].create({
            'name': 'Catalog hide explicit kit',
            'model_id': self.env['ir.model']._get_id('x_hm_parts_kit'),
            'domain_force': repr([('id', '!=', self.explicit.id)]),
        })
        visible = self.fixtures.with_user(self.reader).search([('id', 'in', self.fixtures.ids)])
        self.assertNotIn(self.explicit.id, visible.ids)
        self.assertIn(self.implicit.id, self._assert_computed_search('=', self.product.id, visible).ids)
        self.assertNotIn(self.explicit.id, visible.search([
            ('id', 'in', self.fixtures.ids), ('x_catalog_product_id', '!=', False),
        ]).ids)
        self._assert_computed_search('=', False, visible)
        self._assert_computed_search('not ilike', 'motor', visible)

    def test_hidden_company_product_is_not_inferred(self):
        self.product.write({'company_id': self.other_company.id})
        self.implicit.write({'x_company_id': self.other_company.id})
        kits = self.fixtures.with_user(self.reader).with_context(allowed_company_ids=[self.env.company.id])
        self.assertIn(self.implicit.id, self._assert_computed_search('=', False, kits).ids)

    def test_missing_kit_acl_still_raises(self):
        outsider = new_test_user(self.env, login='catalog_outsider_' + uuid4().hex,
                                 groups='base.group_portal')
        with self.assertRaises(AccessError):
            self.Kit.with_user(outsider).search([('x_catalog_product_id', '!=', False)])

    def test_order_limit_offset_and_boolean_composition(self):
        domain = [('id', 'in', self.fixtures.ids), ('x_catalog_product_id', '!=', False)]
        expected = sorted([self.implicit.id, self.explicit.id])
        self.assertEqual(self.Kit.search(domain, order='id', limit=1).ids, expected[:1])
        self.assertEqual(self.Kit.search(domain, order='id', limit=1, offset=1).ids, expected[1:])
        self.assertEqual(self.Kit.search_count(domain), len(expected))
        result = self.Kit.search([
            ('id', 'in', self.fixtures.ids), '|',
            ('x_catalog_product_id', '=', self.product.id), ('id', '=', self.empty.id),
        ])
        self.assertEqual(set(result.ids), {self.implicit.id, self.empty.id})

    def test_more_than_one_implicit_batch(self):
        kits = self.Kit.create([{
            'x_name': 'Batch catalog %s' % index,
            'x_company_id': self.env.company.id, 'x_active': True,
            'x_note': self.implicit.x_note,
        } for index in range(205)])
        self.assertEqual(set(self._assert_computed_search('=', self.product.id, kits).ids),
                         set(kits.ids))
        self.assertEqual(self.Kit.search([
            ('id', 'in', kits.ids), ('x_catalog_product_id', '!=', False),
        ], order='id desc', limit=1).ids, [max(kits.ids)])

    def test_z_callback_survives_manual_registry_re_setup(self):
        fixture_ids = self.fixtures.ids
        self.registry._setup_models__(self.cr, [])
        self.assertIs(self.env['x_hm_parts_kit']._fields['x_catalog_product_id'].search,
                      search_catalog_product)
        # Odoo recreates manual model classes: never reuse pre-setup recordsets.
        self._assert_computed_search('!=', False, self.env['x_hm_parts_kit'].browse(fixture_ids))
