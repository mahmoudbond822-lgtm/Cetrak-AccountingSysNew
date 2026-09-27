"""AUD-030 guard for the PostgreSQL-only balance constraint.

The exact-equality CHECK constraint is installed by a RunPython migration that
is a no-op on SQLite, so the test database never executes it. These tests pin
the shipped SQL so a tolerance cannot creep back in unnoticed.
"""

import importlib

from django.test import SimpleTestCase


MIGRATION = importlib.import_module(
    "apps.accounting.migrations.0005_decimal_exact_balance_check"
)


class DecimalExactBalanceConstraintTests(SimpleTestCase):
    def test_exact_function_uses_equality_not_a_tolerance(self):
        sql = MIGRATION.EXACT_CHECK_FUNCTION
        self.assertIn("=", sql)
        self.assertNotIn("0.01", sql)
        self.assertNotIn("ABS(", sql)

    def test_precheck_detects_non_zero_imbalance(self):
        self.assertIn("<>", MIGRATION.COUNT_UNBALANCED)
        self.assertIn("accounting_journalentryline", MIGRATION.COUNT_UNBALANCED)

    def test_reverse_restores_the_previous_tolerant_function(self):
        self.assertIn("0.01", MIGRATION.TOLERANT_CHECK_FUNCTION)
        self.assertIn("ABS(", MIGRATION.TOLERANT_CHECK_FUNCTION)
