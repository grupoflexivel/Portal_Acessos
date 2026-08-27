from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0004_ferramenta")]

    operations = [
        migrations.CreateModel(
            name="LinkUtil",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=255)),
                ("url", models.URLField(max_length=500)),
            ],
            options={
                "verbose_name": "Link útil",
                "verbose_name_plural": "Links úteis",
                "ordering": ("nome",),
            },
        ),
    ]