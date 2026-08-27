from django.db import migrations, models


def manter_primeiro_centro(apps, schema_editor):
    Funcionario = apps.get_model("usuarios", "Funcionario")
    for funcionario in Funcionario.objects.all():
        centro = funcionario.centros_custo.order_by("pk").first()
        if centro is not None:
            funcionario.centro_custo_id = centro.pk
            funcionario.save(update_fields=["centro_custo"])


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0002_funcionario_centros_custo")]

    operations = [
        migrations.AddField(
            model_name="funcionario",
            name="centro_custo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="funcionarios_legado",
                to="usuarios.centrocusto",
            ),
        ),
        migrations.RunPython(manter_primeiro_centro, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="funcionario",
            name="centros_custo",
        ),
        migrations.AlterField(
            model_name="funcionario",
            name="centro_custo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="funcionarios",
                to="usuarios.centrocusto",
            ),
        ),
    ]