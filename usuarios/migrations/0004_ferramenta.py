from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0003_funcionario_centro_custo_unico")]

    operations = [
        migrations.CreateModel(
            name="Ferramenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=255)),
                ("url", models.URLField(max_length=500)),
                (
                    "centro_custo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ferramentas",
                        to="usuarios.centrocusto",
                    ),
                ),
            ],
            options={
                "verbose_name": "Link de acesso",
                "verbose_name_plural": "Links de acesso",
                "ordering": ("nome",),
            },
        ),
    ]