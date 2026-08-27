from django.db import migrations, models


def copiar_centro_custo_atual(apps, schema_editor):
    Funcionario = apps.get_model("usuarios", "Funcionario")
    through_model = Funcionario.centros_custo.through
    for funcionario in Funcionario.objects.exclude(centro_custo_legado__isnull=True):
        through_model.objects.create(
            funcionario_id=funcionario.pk,
            centrocusto_id=funcionario.centro_custo_legado_id,
        )


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0001_initial")]

    operations = [
        migrations.RenameField(
            model_name="funcionario",
            old_name="centro_custo",
            new_name="centro_custo_legado",
        ),
        migrations.AddField(
            model_name="funcionario",
            name="centros_custo",
            field=models.ManyToManyField(
                blank=True,
                related_name="funcionarios",
                to="usuarios.centrocusto",
            ),
        ),
        migrations.RunPython(copiar_centro_custo_atual, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="funcionario",
            name="centro_custo_legado",
        ),
    ]