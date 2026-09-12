from django.db import migrations

MANAGERS_GROUP = "Managers"
EMPLOYEES_GROUP = "Employees"


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=MANAGERS_GROUP)
    Group.objects.get_or_create(name=EMPLOYEES_GROUP)


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=[MANAGERS_GROUP, EMPLOYEES_GROUP]).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]