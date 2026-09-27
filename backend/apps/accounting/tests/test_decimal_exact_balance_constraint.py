"""AUD-030 guard for the PostgreSQL-only balance constraint.

The exact-equality CHECK constraint is installed by a RunPython migration that
is a no-op on SQLite, so the test database never executes it. These tests pin
the shipped SQL so a tolerance cannot creep back in unnoticed, and *call* the
migration functions with a stand-in schema editor so the PostgreSQL branch is
covered even when the suite runs on SQLite.
"""

import importlib

from django.test import SimpleTestCase


MIGRATION = importlib.import_module(
    "apps.accounting.migrations.0005_decimal_exact_balance_check"
)


class FakeCursor:
    """Minimal DB-API cursor: records SQL, returns a canned single-row result."""

    def __init__(self, unbalanced):
        self.unbalanced = unbalanced
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchone(self):
        return (self.unbalanced,)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeConnection:
    def __init__(self, vendor, cursor):
        self.vendor = vendor
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class FakeSchemaEditor:
    """Mirrors Django 6, where ``execute()`` runs SQL and returns ``None``."""

    def __init__(self, vendor="postgresql", unbalanced=0):
        self.cursor = FakeCursor(unbalanced)
        self.connection = FakeConnection(vendor, self.cursor)
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append(sql)
        return None


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


class ApplyExactCheckTests(SimpleTestCase):
    """The migration must run, not just read well.

    Regression: the pre-check used ``schema_editor.execute(...).fetchone()``,
    which raises ``AttributeError`` on Django 6 because ``execute()`` returns
    ``None`` there. Only PostgreSQL reaches that code, and the suite runs on
    SQLite by default, so nothing executed it until a real ``migrate`` did.
    """

    def test_it_reads_the_imbalance_count_and_installs_the_constraint(self):
        editor = FakeSchemaEditor(unbalanced=0)

        MIGRATION.apply_exact_check(None, editor)

        self.assertEqual(
            editor.cursor.executed, [MIGRATION.COUNT_UNBALANCED]
        )
        self.assertEqual(len(editor.statements), 3)
        self.assertIn("DROP CONSTRAINT IF EXISTS", editor.statements[0])
        self.assertIn("CREATE OR REPLACE FUNCTION", editor.statements[1])
        self.assertIn("ADD CONSTRAINT balanced_entry_check", editor.statements[2])

    def test_it_refuses_and_changes_nothing_when_entries_are_unbalanced(self):
        editor = FakeSchemaEditor(unbalanced=2)

        with self.assertRaises(RuntimeError) as caught:
            MIGRATION.apply_exact_check(None, editor)

        self.assertIn("2 journal entr", str(caught.exception))
        self.assertIn("nothing has been modified", str(caught.exception))
        self.assertEqual(editor.statements, [])

    def test_it_is_a_noop_off_postgres(self):
        editor = FakeSchemaEditor(vendor="sqlite")

        MIGRATION.apply_exact_check(None, editor)

        self.assertEqual(editor.cursor.executed, [])
        self.assertEqual(editor.statements, [])

    def test_reverse_reinstalls_the_tolerant_constraint(self):
        editor = FakeSchemaEditor()

        MIGRATION.restore_tolerant_check(None, editor)

        self.assertEqual(editor.cursor.executed, [])
        self.assertIn("CREATE OR REPLACE FUNCTION", editor.statements[1])
        self.assertIn("ABS(", editor.statements[1])
