from django.apps import AppConfig
from django.db.models.signals import post_migrate

def criar_grupo_todos(sender, **kwargs):
    GrupoEspaco = sender.get_model("GrupoEspaco")

    GrupoEspaco.objects.get_or_create(
        nome="Todos",
        defaults={
            "descricao": "Grupo padrão com acesso a todos os Grupos/Espaços.",
            "ativo": True,
            "grupo_sistema": True,
        },
    )

class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        post_migrate.connect(criar_grupo_todos, sender=self)