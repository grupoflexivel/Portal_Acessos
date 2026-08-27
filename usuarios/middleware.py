from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

class ExigeTrocaSenhaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Se o usuário precisa trocar a senha obrigatoriamente:
            if getattr(request.user, 'deve_trocar_senha', False):
                url_mudar_senha = reverse('usuarios:primeiro_acesso_mudar_senha')
                url_logout = reverse('usuarios:logout')
                url_login = reverse('usuarios:login')
                
                # Se ele tentar acessar qualquer página que não seja a de troca de senha ou logout:
                if request.path not in [url_mudar_senha, url_logout, url_login]:
                    # Encerra a sessão atual e manda para o login
                    logout(request)
                    return redirect('usuarios:login')

        response = self.get_response(request)
        return response