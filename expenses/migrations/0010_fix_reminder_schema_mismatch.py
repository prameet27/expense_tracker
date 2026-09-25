"""
A previous migration on this database was applied with different column
names than the ones in the current models.py / migration 0009 (it created
`reminder_1_days_before` / `reminder_2_days_before` / `reminder_number`
instead of `reminder1_days_before` / `reminder2_days_before` / `slot`, and
never added the `email` column). Django's migration history already
records 0009 as applied, so `migrate` won't touch it again - this migration
repairs the actual database table in place, without changing Django's
migration *state* (which is already correct) and without losing any
existing Reminder / ReminderLog rows.
"""
from django.db import migrations


def fix_schema(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(expenses_reminder)")
        reminder_columns = {row[1] for row in cursor.fetchall()}

        cursor.execute("PRAGMA table_info(expenses_reminderlog)")
        log_columns = {row[1] for row in cursor.fetchall()}

        # --- expenses_reminder -------------------------------------------------
        if "reminder_1_days_before" in reminder_columns and "reminder1_days_before" not in reminder_columns:
            cursor.execute(
                "ALTER TABLE expenses_reminder "
                "RENAME COLUMN reminder_1_days_before TO reminder1_days_before"
            )
        if "email" not in reminder_columns:
            cursor.execute(
                "ALTER TABLE expenses_reminder ADD COLUMN email varchar(254) NOT NULL DEFAULT ''"
            )

        # reminder2_days_before must be NULLable (optional second reminder).
        # SQLite can't alter a column's NOT NULL constraint in place, so the
        # table is rebuilt the same way Django's own SQLite backend would.
        if "reminder_2_days_before" in reminder_columns or "reminder2_days_before" in reminder_columns:
            old_col = "reminder_2_days_before" if "reminder_2_days_before" in reminder_columns else "reminder2_days_before"
            cursor.execute("PRAGMA table_info(expenses_reminder)")
            cols_after = {row[1]: row for row in cursor.fetchall()}
            needs_rebuild = cols_after[old_col][3] == 1  # notnull flag
            if needs_rebuild:
                cursor.execute("ALTER TABLE expenses_reminder RENAME TO expenses_reminder_old")
                cursor.execute(
                    """
                    CREATE TABLE expenses_reminder (
                        id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                        person_name varchar(100) NOT NULL,
                        email varchar(254) NOT NULL DEFAULT '',
                        reminder_type varchar(20) NOT NULL,
                        original_date date NOT NULL,
                        reminder1_days_before integer unsigned NOT NULL CHECK (reminder1_days_before >= 0),
                        reminder2_days_before integer unsigned NULL CHECK (reminder2_days_before IS NULL OR reminder2_days_before >= 0),
                        notes text NOT NULL,
                        created_by_id integer NOT NULL REFERENCES auth_user (id) DEFERRABLE INITIALLY DEFERRED
                    )
                    """
                )
                cursor.execute(
                    f"""
                    INSERT INTO expenses_reminder
                        (id, person_name, email, reminder_type, original_date,
                         reminder1_days_before, reminder2_days_before, notes, created_by_id)
                    SELECT
                        id, person_name, email, reminder_type, original_date,
                        reminder1_days_before,
                        CASE WHEN {old_col} = 0 THEN NULL ELSE {old_col} END,
                        notes, created_by_id
                    FROM expenses_reminder_old
                    """
                )
                cursor.execute("DROP TABLE expenses_reminder_old")
                cursor.execute(
                    "CREATE INDEX expenses_reminder_created_by_id ON expenses_reminder (created_by_id)"
                )

        # --- expenses_reminderlog ----------------------------------------------
        if "slot" not in log_columns:
            old_slot_col = "reminder_number" if "reminder_number" in log_columns else None
            cursor.execute(
                "ALTER TABLE expenses_reminderlog ADD COLUMN slot varchar(2) NOT NULL DEFAULT 'r1'"
            )
            if old_slot_col:
                cursor.execute(
                    f"UPDATE expenses_reminderlog SET slot = CASE WHEN {old_slot_col} = 0 THEN 'r1' ELSE 'r2' END"
                )
                # Any index referencing the old column must be dropped first,
                # or SQLite refuses to drop the column.
                cursor.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='expenses_reminderlog' "
                    f"AND sql LIKE '%{old_slot_col}%'"
                )
                for (index_name,) in cursor.fetchall():
                    cursor.execute(f'DROP INDEX "{index_name}"')
                cursor.execute(f"ALTER TABLE expenses_reminderlog DROP COLUMN {old_slot_col}")

        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS expenses_reminderlog_reminder_year_slot_uniq "
            "ON expenses_reminderlog (reminder_id, year, slot)"
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0009_alter_reminderlog_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_schema, noop_reverse),
    ]
