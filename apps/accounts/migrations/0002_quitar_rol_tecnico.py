from django.db import migrations, models


def tecnicos_a_admin(apps, schema_editor):
    """El rol Técnico se eliminó: administrador y técnico son lo mismo."""
    Usuario = apps.get_model("accounts", "Usuario")
    Usuario.objects.filter(rol="TECNICO").update(rol="ADMIN")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(tecnicos_a_admin, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usuario",
            name="rol",
            field=models.CharField(
                choices=[("ADMIN", "Administrador"), ("USUARIO", "Usuario")],
                default="USUARIO",
                max_length=10,
            ),
        ),
    ]
