from django.apps import AppConfig
from django.db.models.signals import post_migrate

def criar_grupo_todos(sender, **kwargs):
    GrupoEspaco = sender.get_model("GrupoEspaco")

    # Cria o grupo "Espaço Geral" (padrão universal)
    GrupoEspaco.objects.update_or_create(
        nome="Espaço Geral",
        defaults={
            "descricao": "Espaço Geral para todos colaboradores.",
            "ativo": True,
            "grupo_sistema": True,
        },
    )

class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        post_migrate.connect(criar_grupo_todos, sender=self)