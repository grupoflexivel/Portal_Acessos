from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    AlterarSenhaForm,
    CadastroRecursoForm,
    FuncionarioCadastroForm,
    FuncionarioEdicaoForm,
)
from .models import CentroCusto, Ferramenta, Funcionario, LinkUtil


class LoginView(auth_views.LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        username_informado = request.POST.get("username", "").strip()

        try:
            usuario = Funcionario.objects.get(username=username_informado)
        except Funcionario.DoesNotExist:
            usuario = None

        if usuario:

            # Conta desativada definitivamente
            if not usuario.is_active or not usuario.ativo:
                form.errors.clear()
                form.add_error(
                    None,
                    ValidationError(
                        "Conta desativada por segurança após 5 tentativas "
                        "incorretas. Apenas o administrador pode reativá-la."
                    ),
                )
                return self.form_invalid(form)

            agora = timezone.now()

            if usuario.bloqueado_ate and usuario.bloqueado_ate > agora:
                diferenca = usuario.bloqueado_ate - agora
                segundos = max(int(diferenca.total_seconds()), 1)

                form.errors.clear()
                form.add_error(
                    None,
                    ValidationError(
                        f"Muitas tentativas incorretas. "
                        f"Aguarde {segundos} segundos para tentar novamente."
                    ),
                )

                return self.form_invalid(form)

            if usuario.bloqueado_ate and usuario.bloqueado_ate <= agora:
                usuario.bloqueado_ate = None

                if usuario.tentativas_falhas < 3:
                    usuario.tentativas_falhas = 3

                usuario.save(
                    update_fields=[
                        "bloqueado_ate",
                        "tentativas_falhas",
                    ]
                )

        if form.is_valid():
            user = form.get_user()

            user.tentativas_falhas = 0
            user.bloqueado_ate = None

            user.save(
                update_fields=[
                    "tentativas_falhas",
                    "bloqueado_ate",
                ]
            )

            response = super().form_valid(form)

            self.request.session.set_expiry(0)

            if getattr(user, "deve_trocar_senha", False):
                return redirect(
                    "usuarios:primeiro_acesso_mudar_senha"
                )

            return response

        if usuario:

            usuario.tentativas_falhas += 1
            form.errors.clear()

            if usuario.tentativas_falhas >= 5:
                usuario.tentativas_falhas = 5
                usuario.is_active = False
                usuario.ativo = False
                usuario.bloqueado_ate = None

                usuario.save(
                    update_fields=[
                        "tentativas_falhas",
                        "is_active",
                        "ativo",
                        "bloqueado_ate",
                    ]
                )

                form.add_error(
                    None,
                    ValidationError(
                        "Conta desativada por segurança após 5 tentativas "
                        "incorretas. Apenas o administrador pode reativá-la."
                    ),
                )

            elif usuario.tentativas_falhas == 3:
                usuario.bloqueado_ate = (
                    timezone.now() + timedelta(minutes=1)
                )

                usuario.save(
                    update_fields=[
                        "tentativas_falhas",
                        "bloqueado_ate",
                    ]
                )

                diferenca = usuario.bloqueado_ate - timezone.now()
                segundos = max(int(diferenca.total_seconds()), 1)

                form.add_error(
                    None,
                    ValidationError(
                        f"Muitas tentativas incorretas. "
                        f"Aguarde {segundos} segundos para tentar novamente."
                    ),
                )

            elif usuario.tentativas_falhas < 3:
                usuario.save(
                    update_fields=[
                        "tentativas_falhas",
                    ]
                )

                restantes = 3 - usuario.tentativas_falhas

                form.add_error(
                    None,
                    ValidationError(
                        f"Senha incorreta. Você tem mais {restantes} "
                        f"{'tentativa' if restantes == 1 else 'tentativas'} "
                        "antes do bloqueio temporário."
                    ),
                )

            else:
                usuario.save(
                    update_fields=[
                        "tentativas_falhas",
                    ]
                )

                restantes = 5 - usuario.tentativas_falhas

                form.add_error(
                    None,
                    ValidationError(
                        f"Senha incorreta. Você tem mais {restantes} "
                        f"{'tentativa' if restantes == 1 else 'tentativas'} "
                        "antes da desativação definitiva."
                    ),
                )

        return self.form_invalid(form)
        
def logout_view(request):
    return auth_views.LogoutView.as_view(
        next_page=reverse_lazy("usuarios:login")
    )(request)


def _ferramentas_para_usuario(user):
    if user.is_superuser:
        centros = CentroCusto.objects.all()
    else:
        centros = CentroCusto.objects.filter(
            pk=user.centro_custo_id
        )

    grupos = [
        {
            "centro_custo_codigo": centro.codigo,
            "centro_custo_descricao": centro.descricao,
            "itens": centro.ferramentas.all(),
        }
        for centro in centros
    ]

    return grupos, user.is_superuser


def _contexto_sidebar(user):
    centros_custo, administrador = _ferramentas_para_usuario(user)

    ferramentas = [
        grupo
        for grupo in centros_custo
        if grupo["itens"]
    ]

    return {
        "centros_custo": centros_custo,
        "ferramentas": ferramentas,
        "links_uteis": LinkUtil.objects.all(),
        "administrador": administrador,
    }


@login_required
def home(request):
    context = _contexto_sidebar(request.user)

    return render(
        request,
        "usuarios/home.html",
        context,
    )


def raiz(request):
    return redirect("usuarios:home")


class PrimeiroAcessoTrocarSenha(auth_views.PasswordChangeView):
    template_name = "usuarios/primeiro_acesso_mudar_senha.html"
    success_url = reverse_lazy("usuarios:home")
    form_class = AlterarSenhaForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_sidebar(self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.deve_trocar_senha = False
        self.request.user.save(update_fields=["deve_trocar_senha"])
        return response


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "usuarios/mudar_senha.html"
    success_url = reverse_lazy("usuarios:home")
    form_class = AlterarSenhaForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.vinculado_ad:
            messages.info(
                request,
                "Sua senha é gerenciada pelo Active Directory. "
                "Fale com o TI para alterá-la.",
            )
            return redirect("usuarios:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_sidebar(self.request.user))
        return context


def admin_nao_superuser_required(user):
    return (
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
        )
    )

@user_passes_test(
    admin_nao_superuser_required,
    login_url="usuarios:home"
)
def cadastrar_recurso_admin(request):
    if request.method == "POST":
        form = CadastroRecursoForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            tipo = form.cleaned_data["tipo_destino"]
            nome = form.cleaned_data["nome"]
            arquivo = form.cleaned_data["arquivo"]
            url = form.cleaned_data["url"]

            if tipo == "colaborador":
                LinkUtil.objects.create(
                    nome=nome,
                    arquivo=arquivo,
                    url=url
                )
                messages.success(
                    request,
                    "Link/Arquivo para colaboradores cadastrado com sucesso!"
                )

            elif tipo == "centro_custo":
                centro_custo = form.cleaned_data["centro_custo"]
                Ferramenta.objects.create(
                    centro_custo=centro_custo,
                    nome=nome,
                    arquivo=arquivo,
                    url=url
                )
                messages.success(
                    request,
                    "Link/Arquivo para o Centro de Custo cadastrado com sucesso!"
                )

            # Redireciona para o gerenciamento de recursos
            return redirect(
                "usuarios:gerenciar_recursos"
            )

    else:
        form = CadastroRecursoForm()

    context = _contexto_sidebar(request.user)
    context["form"] = form

    return render(
        request,
        "usuarios/cadastrar_recurso.html",
        context,
    )


@login_required
def listar_usuarios(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied(
            "Apenas administradores podem visualizar os colaboradores."
        )

    busca = request.GET.get("busca", "").strip()
    unidade_fabril_id = request.GET.get("empresa", "")
    centro_custo_id = request.GET.get("centro_custo", "")
    departamento_id = request.GET.get("departamento", "")
    status = request.GET.get("status", "")

    usuarios = Funcionario.objects.select_related(
        "centro_custo", "departamento", "unidade_fabril"
    ).all().order_by("nome", "username")

    if busca:
        from django.db.models import Q
        usuarios = usuarios.filter(
            Q(nome__icontains=busca)
            | Q(username__icontains=busca)
            | Q(email__icontains=busca)
        )

    if unidade_fabril_id:
        usuarios = usuarios.filter(unidade_fabril_id=unidade_fabril_id)

    if centro_custo_id:
        usuarios = usuarios.filter(centro_custo_id=centro_custo_id)

    if departamento_id:
        usuarios = usuarios.filter(departamento_id=departamento_id)

    if status == "ativo":
        usuarios = usuarios.filter(ativo=True)
    elif status == "inativo":
        usuarios = usuarios.filter(ativo=False)

    centros_custo = CentroCusto.objects.all().order_by("descricao")
    
    from .models import Departamento, UnidadeFabril
    departamentos = Departamento.objects.all().order_by("nome")
    empresas = UnidadeFabril.objects.all().order_by("nome")

    context = _contexto_sidebar(request.user)

    context.update(
        {
            "usuarios": usuarios,
            "centros_custo": centros_custo,
            "departamentos": departamentos,
            "empresas": empresas,
            "busca": busca,
            "empresa_selecionada": unidade_fabril_id,
            "centro_custo_selecionado": centro_custo_id,
            "departamento_selecionado": departamento_id,
            "status_selecionado": status,
        }
    )

    return render(
        request,
        "usuarios/listar_usuarios.html",
        context,
    )


@login_required
def cadastrar_usuario(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied(
            "Apenas administradores podem cadastrar colaboradores."
        )

    if request.method == "POST":
        form = FuncionarioCadastroForm(request.POST)

        if form.is_valid():
            funcionario = form.save()

            if funcionario.nome:
                funcionario.nome = funcionario.nome.upper()
                funcionario.save(update_fields=['nome'])

            nome_colaborador = getattr(funcionario, 'nome', None) or funcionario.username
            
            messages.success(
                request,
                f'Usuário "{nome_colaborador}" cadastrado com sucesso'
            )
            
            return redirect("usuarios:listar_usuarios")
    else:
        form = FuncionarioCadastroForm()

    context = _contexto_sidebar(request.user)
    context["form"] = form

    return render(
        request,
        "usuarios/cadastro_usuario.html",
        context,
    )


@login_required
def editar_usuario(request, usuario_id):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied(
            "Apenas administradores podem alterar colaboradores."
        )

    usuario = get_object_or_404(
        Funcionario,
        pk=usuario_id,
    )

    if request.method == "POST":
        form = FuncionarioEdicaoForm(
            request.POST,
            instance=usuario,
        )

        if form.is_valid():
            # Usamos commit=False para tratar as travas de segurança caso a conta seja reativada
            usuario = form.save(commit=False)

            if usuario.ativo:
                usuario.is_active = True
                usuario.tentativas_falhas = 0
                usuario.bloqueado_ate = None

            usuario.save()

            messages.success(
                request,
                f"Colaborador {usuario.nome or usuario.username} atualizado com sucesso!"
            )

            return redirect(
                "usuarios:listar_usuarios"
            )

    else:
        form = FuncionarioEdicaoForm(
            instance=usuario
        )

    context = _contexto_sidebar(request.user)
    context.update(
        {
            "form": form,
            "usuario_editado": usuario,
        }
    )

    return render(
        request,
        "usuarios/editar_usuario.html",
        context,
    )


@login_required
def excluir_usuario(request, usuario_id):
    if not request.user.is_superuser:
        raise PermissionDenied(
            "Apenas superusuários podem excluir colaboradores."
        )

    usuario = get_object_or_404(
        Funcionario,
        pk=usuario_id,
    )

    if request.method != "POST":
        raise PermissionDenied(
            "Operação não permitida."
        )

    if usuario.pk == request.user.pk:
        messages.error(
            request,
            "Você não pode excluir o seu próprio usuário."
        )
        return redirect(
            "usuarios:editar_usuario",
            usuario_id=usuario.pk,
        )

    nome_usuario = usuario.nome or usuario.username
    usuario.delete()

    messages.success(
        request,
        f"Colaborador {nome_usuario} excluído com sucesso!"
    )

    return redirect(
        "usuarios:listar_usuarios"
    )

@login_required
def gerenciar_recursos(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem gerenciar recursos.")
    # Busca todas as ferramentas e adiciona uma tag identificadora
    ferramentas = Ferramenta.objects.all()
    lista_ferramentas = []
    for f in ferramentas:
        lista_ferramentas.append({
            'id': f.id,
            'nome': f.nome,
            'url': f.url,
            'arquivo': f.arquivo,
            'local': f"Centro de Custo ({f.centro_custo.codigo} - {f.centro_custo.descricao})",
            'tipo_origem': 'ferramenta'
        })

    # Busca todos os links úteis e adiciona a tag identificadora
    links = LinkUtil.objects.all()
    lista_links = []
    for l in links:
        lista_links.append({
            'id': l.id,
            'nome': l.nome,
            'url': l.url,
            'arquivo': l.arquivo,
            'local': "Espaço Colaboradores",
            'tipo_origem': 'link'
        })

    # Junta as duas listas em uma só e ordena por ID decrescente (mais recentes primeiro)
    recursos_unificados = sorted(
        lista_ferramentas + lista_links, 
        key=lambda x: x['id'], 
        reverse=True
    )

    return render(request, 'usuarios/gerenciar_recursos.html', {'recursos': recursos_unificados})


@login_required
def editar_recurso(request, tipo, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem editar recursos.")
    # Identifica o modelo correto com base no tipo que veio da URL
    if tipo == 'ferramenta':
        recurso = get_object_or_404(Ferramenta, pk=pk)
        tipo_inicial = 'centro_custo'
    elif tipo == 'link':
        recurso = get_object_or_404(LinkUtil, pk=pk)
        tipo_inicial = 'colaborador'
    else:
        messages.error(request, "Tipo de recurso inválido.")
        return redirect('usuarios:gerenciar_recursos')

    if request.method == 'POST':
        form = CadastroRecursoForm(request.POST, request.FILES)
        if form.is_valid():
            tipo_destino = form.cleaned_data['tipo_destino']
            nome = form.cleaned_data['nome']
            centro_custo = form.cleaned_data['centro_custo']
            arquivo = form.cleaned_data['arquivo']
            url = form.cleaned_data['url']

            recurso.nome = nome
            recurso.url = url if url else ''
            if arquivo:
                recurso.arquivo = arquivo
            
            if tipo_destino == 'centro_custo':
                if isinstance(recurso, Ferramenta):
                    recurso.centro_custo = centro_custo
                    recurso.save()
                else:
                    LinkUtil.objects.filter(pk=pk).delete()
                    Ferramenta.objects.create(
                        nome=nome,
                        centro_custo=centro_custo,
                        url=url,
                        arquivo=arquivo if arquivo else None
                    )
            else:
                # Se virou colaborador (geral)
                if isinstance(recurso, LinkUtil):
                    recurso.save()
                else:
                    # Se era Ferramenta e mudou para LinkUtil, apagamos a ferramenta e criamos o LinkUtil
                    Ferramenta.objects.filter(pk=pk).delete()
                    LinkUtil.objects.create(
                        nome=nome,
                        url=url,
                        arquivo=arquivo if arquivo else None
                    )

            messages.success(request, f"O recurso '{nome}' foi atualizado com sucesso!")
            return redirect('usuarios:gerenciar_recursos')
    else:
        # Preenche o formulário com os dados atuais do recurso para exibição
        dados_iniciais = {
            'tipo_destino': tipo_inicial,
            'nome': recurso.nome,
            'url': recurso.url if hasattr(recurso, 'url') else '',
            'centro_custo': getattr(recurso, 'centro_custo', None),
        }
        form = CadastroRecursoForm(initial=dados_iniciais)

    context = {
        'form': form,
        'recurso': recurso,
        'tipo': tipo,
    }
    return render(request, 'usuarios/editar_recurso.html', context)

@login_required
def excluir_recurso(request, tipo, pk):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas administradores podem excluir recursos.")
    if tipo == 'ferramenta':
        recurso = get_object_or_404(Ferramenta, pk=pk)
    elif tipo == 'link':
        recurso = get_object_or_404(LinkUtil, pk=pk)
    else:
        messages.error(request, "Tipo de recurso inválido.")
        return redirect('usuarios:gerenciar_recursos')

    nome = recurso.nome
    recurso.delete()
    messages.success(request, f"O recurso '{nome}' foi excluído com sucesso!")
    return redirect('usuarios:gerenciar_recursos')
