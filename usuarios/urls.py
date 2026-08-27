from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.raiz, name="raiz"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("home/", views.home, name="home"),
    path("cadastro/", views.cadastrar_usuario, name="cadastro_usuario"),
    path("primeiro-acesso/mudar-senha/", views.PrimeiroAcessoTrocarSenha.as_view(), name="primeiro_acesso_mudar_senha"),
    path("mudar-senha/", views.PasswordChangeView.as_view(), name="mudar_senha"),
    path('cadastrar-recurso/', views.cadastrar_recurso_admin, name='cadastrar_recurso'),
    path("usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("usuarios/<int:usuario_id>/editar/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:usuario_id>/excluir/", views.excluir_usuario, name="excluir_usuario",),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)