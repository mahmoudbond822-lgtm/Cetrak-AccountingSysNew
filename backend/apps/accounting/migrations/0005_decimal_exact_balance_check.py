# AUD-030: make the database balance invariant Decimal-exact.
#
# The original check tolerated any imbalance below 0.01, so a journal entry
# that was out of balance by up to one cent passed the constraint. The sums
# are NUMERIC(19,4) in PostgreSQL, so exact equality is the correct invariant
# and needs no tolerance.

from django.db import migrations


EXACT_CHECK_FUNCTION = """
    CREATE OR REPLACE FUNCTION check_entry_balanced(entry_uuid UUID)
    RETURNS BOOLEAN AS $$
        SELECT COALESCE((SELECT SUM(debit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0) =
               COALESCE((SELECT SUM(credit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0);
    $$ LANGUAGE SQL IMMUTABLE;
"""

TOLERANT_CHECK_FUNCTION = """
    CREATE OR REPLACE FUNCTION check_entry_balanced(entry_uuid UUID)
    RETURNS BOOLEAN AS $$
        SELECT ABS(
            COALESCE((SELECT SUM(debit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0) -
            COALESCE((SELECT SUM(credit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0)
        ) < 0.01;
    $$ LANGUAGE SQL IMMUTABLE;
"""

COUNT_UNBALANCED = """
    SELECT COUNT(*) FROM accounting_journalentry j
    WHERE COALESCE((SELECT SUM(debit) FROM accounting_journalentryline l WHERE l.entry_id = j.id), 0) <>
          COALESCE((SELECT SUM(credit) FROM accounting_journalentryline l WHERE l.entry_id = j.id), 0);
"""


def count_unbalanced_entries(schema_editor):
    """Number of journal entries that the Decimal-exact constraint would reject.

    The count is read from an explicit cursor on purpose:
    ``schema_editor.execute()`` returns ``None`` (it executes inside its own
    ``with connection.cursor()`` and never returns the cursor), so calling
    ``.fetchone()`` on its result raises ``AttributeError`` and the migration
    dies on every PostgreSQL database.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(COUNT_UNBALANCED)
        return cursor.fetchone()[0]


def apply_exact_check(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    unbalanced = count_unbalanced_entries(schema_editor)
    if unbalanced:
        raise RuntimeError(
            f"{unbalanced} journal entr(ies) are not exactly balanced and would "
            "fail the Decimal-exact balance constraint. Correct those entries "
            "before migrating; nothing has been modified."
        )
    schema_editor.execute(
        "ALTER TABLE accounting_journalentry "
        "DROP CONSTRAINT IF EXISTS balanced_entry_check;"
    )
    schema_editor.execute(EXACT_CHECK_FUNCTION)
    schema_editor.execute("""
        ALTER TABLE accounting_journalentry
        ADD CONSTRAINT balanced_entry_check
        CHECK (check_entry_balanced(id));
    """)


def restore_tolerant_check(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE accounting_journalentry "
        "DROP CONSTRAINT IF EXISTS balanced_entry_check;"
    )
    schema_editor.execute(TOLERANT_CHECK_FUNCTION)
    schema_editor.execute("""
        ALTER TABLE accounting_journalentry
        ADD CONSTRAINT balanced_entry_check
        CHECK (check_entry_balanced(id));
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_journalentryline_tenant_and_more'),
    ]

    operations = [
        migrations.RunPython(
            apply_exact_check,
            restore_tolerant_check,
            atomic=False,
        ),
    ]
