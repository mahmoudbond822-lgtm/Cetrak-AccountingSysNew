from django.db import migrations


def apply_check_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION check_entry_balanced(entry_uuid UUID)
        RETURNS BOOLEAN AS $$
            SELECT ABS(
                COALESCE((SELECT SUM(debit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0) -
                COALESCE((SELECT SUM(credit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0)
            ) < 0.01;
        $$ LANGUAGE SQL IMMUTABLE;
    """)
    schema_editor.execute("""
        ALTER TABLE accounting_journalentry
        ADD CONSTRAINT balanced_entry_check
        CHECK (check_entry_balanced(id));
    """)


def reverse_check_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        ALTER TABLE accounting_journalentry
        DROP CONSTRAINT IF EXISTS balanced_entry_check;
    """)
    schema_editor.execute("""
        DROP FUNCTION IF EXISTS check_entry_balanced(UUID);
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial_accounting_models'),
    ]

    operations = [
        migrations.RunPython(
            apply_check_constraint,
            reverse_check_constraint,
            atomic=False,
        ),
    ]
