import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Signal",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                    ),
                ),
                ("service_name", models.CharField(max_length=255, db_index=True)),
                ("environment", models.CharField(max_length=64)),
                ("signal_type", models.CharField(max_length=64)),
                ("severity", models.CharField(max_length=16)),
                ("observed_at", models.DateTimeField()),
                ("summary", models.TextField()),
            ],
            options={
                "db_table": "signals",
                "ordering": ["-observed_at"],
            },
        ),
    ]
