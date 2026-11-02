from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader
from api.replication.registry import TABLES


class Command(BaseCommand):
    help = "Offline migration-state table/key/relationship inventory; never connects to a database."

    def handle(self, *args, **options):
        state = MigrationLoader(None).project_state()
        models = {m._meta.db_table: m for m in state.apps.get_models(include_auto_created=True)}
        self.stdout.write("# Approved table inventory\n\nGenerated from migration state; verify physical catalogs before Stage B.\n")
        for table in TABLES:
            model = models[table]
            pk = model._meta.pk
            sequence = pk.get_internal_type() in {"AutoField", "BigAutoField", "SmallAutoField"}
            self.stdout.write(f"## {table}\n\nPrimary key: `{pk.column}` ({pk.get_internal_type()}); sequence-backed: {sequence}.\n")
            unique = [f.column for f in model._meta.local_fields if f.unique and not f.primary_key]
            self.stdout.write(f"Unique columns: {', '.join(unique) or 'none'}.\n")
            self.stdout.write(f"Unique groups: {model._meta.unique_together or 'none'}; constraints: {model._meta.constraints or 'none'}.\n")
            relations = [f"`{f.column}` -> `{f.related_model._meta.db_table}.{f.target_field.column}` (Django {f.remote_field.on_delete.__name__})"
                         for f in model._meta.local_fields if f.many_to_one]
            self.stdout.write("Foreign keys: " + ("; ".join(relations) or "none") + ".\n")
