from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    AlterarSenhaForm,
    CadastroRecursoForm,
    FuncionarioCadastroForm,
    FuncionarioEdicaoForm,
    GrupoEspacoForm,
)
from .models import (CentroCusto, Departamento, Ferramenta, Funcionario, GrupoEspaco, LinkUtil, UnidadeFabril,)

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
            if not usuario.is_active or not usuario.ativo:
                form.errors.clear()
                form.add_error(
                    None,
                    ValidationError(
                        "Conta desativada por segurança após 5 tentativas incorretas. "
                        "Apenas o administrador pode reativá-la."
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
                        f"Muitas tentativas incorretas. Aguarde {segundos} segundos para tentar novamente."
                    ),
                )
                return self.form_invalid(form)

            if usuario.bloqueado_ate and usuario.bloqueado_ate <= agora:
                usuario.bloqueado_ate = None
                if usuario.tentativas_falhas < 3:
                    usuario.tentativas_falhas = 3
                usuario.save(update_fields=["bloqueado_ate", "tentativas_falhas"])

        if form.is_valid():
            user = form.get_user()
            user.tentativas_falhas = 0
            user.bloqueado_ate = None
            user.save(update_fields=["tentativas_falhas", "bloqueado_ate"])

            response = super().form_valid(form)
            self.request.session.set_expiry(0)

            if getattr(user, "deve_trocar_senha", False):
                return redirect("usuarios:primeiro_acesso_mudar_senha")
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
                        "Conta desativada por segurança após 5 tentativas incorretas. "
                        "Apenas o administrador pode reativá-la."
                    ),
                )
            elif usuario.tentativas_falhas == 3:
                usuario.bloqueado_ate = timezone.now() + timedelta(minutes=1)
                usuario.save(update_fields=["tentativas_falhas", "bloqueado_ate"])
                diferenca = usuario.bloqueado_ate - timezone.now()
                segundos = max(int(diferenca.total_seconds()), 1)
                form.add_error(
                    None,
                    ValidationError(
                        f"Muitas tentativas incorretas. Aguarde {segundos} segundos para tentar novamente."
                    ),
                )
            elif usuario.tentativas_falhas < 3:
                usuario.save(update_fields=["tentativas_falhas"])
                restantes = 3 - usuario.tentativas_falhas
                form.add_error(
                    None,
                    ValidationError(
                        f"Senha incorreta. Você tem mais {restantes} "
                        f"{'tentativa' if restantes == 1 else 'tentativas'} antes do bloqueio temporário."
                    ),
                )
            else:
                usuario.save(update_fields=["tentativas_falhas"])
                restantes = 5 - usuario.tentativas_falhas
                form.add_error(
                    None,
                    ValidationError(
                        f"Senha incorreta. Você tem mais {restantes} "
                        f"{'tentativa' if restantes == 1 else 'tentativas'} antes da desativação definitiva."
                    ),
                )

        return self.form_invalid(form)


def logout_view(request):
    return auth_views.LogoutView.as_view(
        next_page=reverse_lazy("usuarios:login")
    )(request)


def _grupo_todos():
    return GrupoEspaco.objects.filter(nome__iexact="Todos", ativo=True).first()


def _usuario_tem_acesso_total(user):
    if user.is_superuser:
        return True
    return user.grupos.filter(nome__iexact="Todos", ativo=True).exists()


def _grupos_visiveis_para_usuario(user):
    ativos = GrupoEspaco.objects.filter(ativo=True)
    if _usuario_tem_acesso_total(user):
        return ativos.order_by("nome")

    ids_usuario = user.grupos.filter(ativo=True).values_list("pk", flat=True)
    return ativos.filter(Q(pk__in=ids_usuario) | Q(nome__iexact="Todos")).distinct().order_by("nome")


def _recursos_do_grupo(grupo):
    ferramentas = list(
        Ferramenta.objects.filter(grupos=grupo).prefetch_related("grupos").order_by("nome")
    )
    links = list(
        LinkUtil.objects.filter(grupos=grupo).prefetch_related("grupos").order_by("nome")
    )
    recursos = ferramentas + links
    recursos.sort(key=lambda item: item.nome.casefold())
    return recursos


def _recursos_por_grupo_para_usuario(user):
    grupos = []

    grupos_visiveis = list(_grupos_visiveis_para_usuario(user))

    grupos_visiveis.sort(
        key=lambda grupo: (
            0 if grupo.nome.casefold() == "todos" else 1,
            grupo.nome.casefold()
        )
    )

    for grupo in grupos_visiveis:
        itens = _recursos_do_grupo(grupo)

        if itens:
            grupos.append({
                "id": grupo.pk,
                "nome": grupo.nome,
                "descricao": grupo.descricao,
                "itens": itens,
            })

    return grupos


def _contexto_sidebar(user):
    grupos_recursos = _recursos_por_grupo_para_usuario(user)
    return {
        "grupos_recursos": grupos_recursos,
        # Alias temporário para templates antigos que ainda referenciem 'ferramentas'.
        "ferramentas": grupos_recursos,
        "administrador": user.is_staff or user.is_superuser,
    }


@login_required
def home(request):
    return render(request, "usuarios/home.html", _contexto_sidebar(request.user))


def raiz(request):
    return redirect("usuarios:home")


class PrimeiroAcessoTrocarSenha(auth_views.PasswordChangeView):
    template_name = "usuarios/primeiro_acesso_mudar_senha.html"
    success_url = reverse_lazy("usuarios:home")
    form_class = AlterarSenhaForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.vinculado_ad:
            return redirect("usuarios:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_sidebar(self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        self.request.user.deve_trocar_senha = False
        self.request.user.save(update_fields=["deve_trocar_senha"])
        return response


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "usuarios/mudar_senha.html"
    success_url = reverse_lazy("usuarios:home")
    form_class = AlterarSenhaForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, "vinculado_ad", False):
            messages.info(
                request,
                "Sua senha é gerenciada pelo Active Directory. Fale com o TI para alterá-la.",
            )
            return redirect("usuarios:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_sidebar(self.request.user))
        return context


def admin_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _exigir_superuser(user):
    if not user.is_superuser:
        raise PermissionDenied("Apenas superusuários podem gerenciar Grupos/Espaços.")


@user_passes_test(admin_required, login_url="usuarios:home")
def cadastrar_recurso_admin(request):
    if request.method == "POST":
        form = CadastroRecursoForm(request.POST, request.FILES)
        if form.is_valid():
            recurso = Ferramenta.objects.create(
                nome=form.cleaned_data["nome"],
                arquivo=form.cleaned_data["arquivo"],
                url=form.cleaned_data["url"],
                logo=form.cleaned_data["logo"],
                icone=form.cleaned_data["icone"],
            )
            recurso.grupos.set(form.cleaned_data["grupos"])
            messages.success(request, f"Recurso '{recurso.nome}' cadastrado com sucesso!")
            return redirect("usuarios:gerenciar_recursos")
    else:
        form = CadastroRecursoForm()

    context = _contexto_sidebar(request.user)
    context["form"] = form
    return render(request, "usuarios/cadastrar_recurso.html", context)


@login_required
def listar_usuarios(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem visualizar os colaboradores.")

    busca = request.GET.get("busca", "").strip()
    unidade_fabril_id = request.GET.get("empresa", "")
    centro_custo_id = request.GET.get("centro_custo", "")
    departamento_id = request.GET.get("departamento", "")
    grupo_id = request.GET.get("grupo", "")
    status = request.GET.get("status", "")

    usuarios = (
        Funcionario.objects.select_related("centro_custo", "departamento", "unidade_fabril")
        .prefetch_related("grupos")
        .all()
        .order_by("nome", "username")
    )

    if busca:
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
    if grupo_id:
        usuarios = usuarios.filter(grupos__id=grupo_id)
    if status == "ativo":
        usuarios = usuarios.filter(ativo=True)
    elif status == "inativo":
        usuarios = usuarios.filter(ativo=False)

    context = _contexto_sidebar(request.user)
    context.update(
        {
            "usuarios": usuarios.distinct(),
            "centros_custo": CentroCusto.objects.all().order_by("descricao"),
            "departamentos": Departamento.objects.all().order_by("nome"),
            "empresas": UnidadeFabril.objects.all().order_by("nome"),
            "grupos_filtro": GrupoEspaco.objects.filter(ativo=True).order_by("nome"),
            "busca": busca,
            "empresa_selecionada": unidade_fabril_id,
            "centro_custo_selecionado": centro_custo_id,
            "departamento_selecionado": departamento_id,
            "grupo_selecionado": grupo_id,
            "status_selecionado": status,
        }
    )
    return render(request, "usuarios/listar_usuarios.html", context)


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
            messages.success(
                request,
                f'Usuário "{funcionario.nome or funcionario.username}" cadastrado com sucesso!',
            )
            return redirect("usuarios:listar_usuarios")
    else:
        form = FuncionarioCadastroForm()

    context = _contexto_sidebar(request.user)
    context["form"] = form
    return render(request, "usuarios/cadastro_usuario.html", context)


@login_required
def editar_usuario(request, usuario_id):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem alterar colaboradores.")

    usuario = get_object_or_404(Funcionario, pk=usuario_id)
    if request.method == "POST":
        form = FuncionarioEdicaoForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            if usuario.ativo:
                usuario.is_active = True
                usuario.tentativas_falhas = 0
                usuario.bloqueado_ate = None
            else:
                usuario.is_active = False
            usuario.save()
            form.save_m2m()
            messages.success(
                request,
                f"Colaborador {usuario.nome or usuario.username} atualizado com sucesso!",
            )
            return redirect("usuarios:listar_usuarios")
    else:
        form = FuncionarioEdicaoForm(instance=usuario)

    context = _contexto_sidebar(request.user)
    context.update({"form": form, "usuario_editado": usuario})
    return render(request, "usuarios/editar_usuario.html", context)


@login_required
def excluir_usuario(request, usuario_id):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas superusuários podem excluir colaboradores.")
    if request.method != "POST":
        raise PermissionDenied("Operação não permitida.")

    usuario = get_object_or_404(Funcionario, pk=usuario_id)
    if usuario.pk == request.user.pk:
        messages.error(request, "Você não pode excluir o seu próprio usuário.")
        return redirect("usuarios:editar_usuario", usuario_id=usuario.pk)

    nome_usuario = usuario.nome or usuario.username
    usuario.delete()
    messages.success(request, f"Colaborador {nome_usuario} excluído com sucesso!")
    return redirect("usuarios:listar_usuarios")


@login_required
def gerenciar_recursos(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem gerenciar recursos.")

    recursos = []
    for recurso in Ferramenta.objects.prefetch_related("grupos").all():
        recursos.append(
            {
                "id": recurso.id,
                "nome": recurso.nome,
                "url": recurso.url,
                "arquivo": recurso.arquivo,
                "grupos": list(recurso.grupos.all()),
                "tipo_origem": "ferramenta",
            }
        )

    for recurso in LinkUtil.objects.prefetch_related("grupos").all():
        recursos.append(
            {
                "id": recurso.id,
                "nome": recurso.nome,
                "url": recurso.url,
                "arquivo": recurso.arquivo,
                "grupos": list(recurso.grupos.all()),
                "tipo_origem": "link",
            }
        )

    recursos.sort(key=lambda x: (x["nome"].casefold(), x["tipo_origem"]))
    context = _contexto_sidebar(request.user)
    context["recursos"] = recursos
    return render(request, "usuarios/gerenciar_recursos.html", context)


@login_required
def editar_recurso(request, tipo, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Apenas administradores podem editar recursos.")

    if tipo == "ferramenta":
        recurso = get_object_or_404(Ferramenta.objects.prefetch_related("grupos"), pk=pk)
    elif tipo == "link":
        recurso = get_object_or_404(LinkUtil.objects.prefetch_related("grupos"), pk=pk)
    else:
        messages.error(request, "Tipo de recurso inválido.")
        return redirect("usuarios:gerenciar_recursos")

    if request.method == "POST":
        form = CadastroRecursoForm(request.POST, request.FILES, recurso=recurso)
        if form.is_valid():
            recurso.nome = form.cleaned_data["nome"]
            novo_arquivo = form.cleaned_data["arquivo"]
            nova_url = form.cleaned_data["url"]
            nova_logo = form.cleaned_data["logo"]

            if novo_arquivo:
                recurso.arquivo = novo_arquivo
                recurso.url = ""
            elif nova_url:
                recurso.url = nova_url
                recurso.arquivo = None

            if nova_logo:
                recurso.logo = nova_logo
            recurso.icone = form.cleaned_data["icone"] or ""
            recurso.save()
            recurso.grupos.set(form.cleaned_data["grupos"])

            messages.success(request, f"O recurso '{recurso.nome}' foi atualizado com sucesso!")
            return redirect("usuarios:gerenciar_recursos")
    else:
        # Se o recurso não tem grupos, usa "Todos" como padrão
        grupos_ids = list(recurso.grupos.values_list("pk", flat=True))
        if not grupos_ids:
            grupo_todos = GrupoEspaco.objects.filter(nome__iexact="Todos", ativo=True).first()
            if grupo_todos:
                grupos_ids = [grupo_todos.pk]
        
        form = CadastroRecursoForm(
            recurso=recurso,
            initial={
                "nome": recurso.nome,
                "url": recurso.url,
                "icone": recurso.icone,
                "grupos": grupos_ids,
            },
        )

    context = _contexto_sidebar(request.user)
    context.update({"form": form, "recurso": recurso, "tipo": tipo})
    return render(request, "usuarios/editar_recurso.html", context)


@login_required
def excluir_recurso(request, tipo, pk):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas superusuários podem excluir recursos.")
    if request.method != "POST":
        raise PermissionDenied("Operação não permitida.")

    if tipo == "ferramenta":
        recurso = get_object_or_404(Ferramenta, pk=pk)
    elif tipo == 'link':
        recurso = get_object_or_404(LinkUtil, pk=pk)
    else:
        messages.error(request, "Tipo de recurso inválido.")
        return redirect('usuarios:gerenciar_recursos')

    nome = recurso.nome
    recurso.delete()
    messages.success(request, f"O recurso '{nome}' foi excluído com sucesso!")
    return redirect("usuarios:gerenciar_recursos")


@login_required
def cadastrar_grupo(request):
    _exigir_superuser(request.user)

    if request.method == "POST":
        form = GrupoEspacoForm(request.POST)
        if form.is_valid():
            grupo = form.save()
            messages.success(request, f"Grupo/Espaço '{grupo.nome}' cadastrado com sucesso!")
            return redirect("usuarios:gerenciar_grupos")
    else:
        form = GrupoEspacoForm(initial={"ativo": True})

    context = _contexto_sidebar(request.user)
    context["form"] = form
    return render(request, "usuarios/cadastrar_grupo.html", context)


@login_required
def gerenciar_grupos(request):
    _exigir_superuser(request.user)

    grupos = (
        GrupoEspaco.objects.annotate(
            total_usuarios=Count("funcionarios", distinct=True),
            total_ferramentas=Count("ferramentas", distinct=True),
            total_links=Count("links_uteis", distinct=True),
        )
        .order_by("nome")
    )
    for grupo in grupos:
        grupo.total_recursos = grupo.total_ferramentas + grupo.total_links

    context = _contexto_sidebar(request.user)
    context["grupos"] = grupos
    return render(request, "usuarios/gerenciar_grupos.html", context)


@login_required
def editar_grupo(request, grupo_id):
    _exigir_superuser(request.user)
    grupo = get_object_or_404(GrupoEspaco, pk=grupo_id)

    if request.method == "POST":
        form = GrupoEspacoForm(request.POST, instance=grupo)
        if form.is_valid():
            grupo = form.save()
            messages.success(request, f"Grupo/Espaço '{grupo.nome}' atualizado com sucesso!")
            return redirect("usuarios:gerenciar_grupos")
    else:
        form = GrupoEspacoForm(instance=grupo)

    context = _contexto_sidebar(request.user)
    context.update({"form": form, "grupo": grupo})
    return render(request, "usuarios/editar_grupo.html", context)


@login_required
def excluir_grupo(request, grupo_id):
    _exigir_superuser(request.user)
    if request.method != "POST":
        raise PermissionDenied("Operação não permitida.")

    grupo = get_object_or_404(GrupoEspaco, pk=grupo_id)
    if grupo.grupo_sistema or grupo.eh_todos:
        messages.error(request, "O grupo Todos é estrutural e não pode ser excluído.")
        return redirect("usuarios:gerenciar_grupos")

    if grupo.funcionarios.exists() or grupo.ferramentas.exists() or grupo.links_uteis.exists():
        messages.error(
            request,
            "Este Grupo/Espaço possui usuários ou recursos vinculados. Remova os vínculos antes de excluí-lo.",
        )
        return redirect("usuarios:gerenciar_grupos")

    nome = grupo.nome
    grupo.delete()
    messages.success(request, f"Grupo/Espaço '{nome}' excluído com sucesso!")
    return redirect("usuarios:gerenciar_grupos")
