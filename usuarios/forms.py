import unicodedata
from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import (Funcionario, GrupoEspaco, ICONE_RECURSO_CHOICES,)

CAMPO_PADRAO = (
    "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 "
    "text-sm text-slate-900 outline-none transition focus:border-[#00776d] "
    "focus:ring-4 focus:ring-emerald-700/10"
)

CHECKBOX = (
    "h-4 w-4 rounded border-slate-300 text-[#00776d] focus:ring-[#00776d]"
)

class GrupoCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    option_template_name = "django/forms/widgets/checkbox_option.html"

class FuncionarioCadastroForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=GrupoEspaco.objects.none(),
        required=True,
        label="Grupos/Espaços",
        widget=GrupoCheckboxSelectMultiple,
        help_text=(
            "O grupo Todos libera acesso a todos os espaços. Para segregar o usuário, "
            "desmarque Todos e selecione um ou mais grupos específicos."
        ),
    )

    class Meta:
        model = Funcionario
        fields = (
            "nome",
            "email",
            "unidade_fabril",
            "centro_custo",
            "departamento",
            "grupos",
            "ativo",
            "vinculado_ad",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupos"].queryset = GrupoEspaco.objects.filter(ativo=True).order_by("nome")

        for nome, campo in self.fields.items():
            if nome in ("ativo", "vinculado_ad"):
                campo.widget.attrs["class"] = CHECKBOX
            elif nome != "grupos":
                campo.widget.attrs["class"] = CAMPO_PADRAO

            if isinstance(campo, forms.ModelChoiceField):
                campo.empty_label = "-- Selecione uma opção --"
                # Centro de Custo é apenas para registro, não é obrigatório
                if nome == "centro_custo":
                    campo.required = False

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and Funcionario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean_nome(self):
        nome = self.cleaned_data.get("nome")
        if not nome:
            return nome
        
        nome_maiusculo = nome.upper()
        if Funcionario.objects.filter(nome__iexact=nome_maiusculo).exists():
            raise forms.ValidationError("Já existe um colaborador cadastrado com exatamente este nome.")
        return nome_maiusculo

    def _gerar_username(self, nome_completo):
        nfkd = unicodedata.normalize('NFKD', nome_completo)
        nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
        
        partes = nome_limpo.split()
        if not partes:
            return "usuario"

        base_username = partes[0] if len(partes) == 1 else f"{partes[0]}.{partes[-1]}"
        username = base_username
        contador = 1
        
        while Funcionario.objects.filter(username=username).exists():
            username = f"{base_username}{contador}"
            contador += 1
            
        return username

    def save(self, commit=True):
        funcionario = super().save(commit=False)
        funcionario.username = self._gerar_username(funcionario.nome)

        if funcionario.vinculado_ad:
            funcionario.set_unusable_password()
            funcionario.deve_trocar_senha = False
        else:
            funcionario.set_password("MudarSenha123")
            funcionario.deve_trocar_senha = True

        if commit:
            funcionario.save()
            self.save_m2m()
        return funcionario


class AlterarSenhaForm(PasswordChangeForm):
    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password1 = cleaned_data.get("new_password1")

        if old_password and new_password1 and old_password == new_password1:
            raise forms.ValidationError(
                "A nova senha não pode ser igual à senha atual. Por favor, escolha uma senha diferente.",
                code="password_same_as_old",
            )
        return cleaned_data


class CadastroRecursoForm(forms.Form):
    grupos = forms.ModelMultipleChoiceField(
        queryset=GrupoEspaco.objects.none(),
        required=True,
        label="Disponibilizar para os Grupos/Espaços",
        widget=GrupoCheckboxSelectMultiple,
        help_text="Selecione um ou mais grupos. Todos disponibiliza o recurso para qualquer usuário.",
    )
    nome = forms.CharField(
        max_length=255,
        label="Nome",
        widget=forms.TextInput(
            attrs={
                "class": CAMPO_PADRAO,
                "placeholder": "Ex: Sistema de Ponto / Manual de Vendas",
            }
        ),
    )

    arquivo = forms.FileField(
        required=False,
        label="Enviar Arquivo",
        widget=forms.ClearableFileInput(
            attrs={
                "class": (
                    "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 "
                    "file:rounded-xl file:border-0 file:text-sm file:font-semibold "
                    "file:bg-emerald-50 file:text-[#00776d] hover:file:bg-emerald-100 cursor-pointer"
                )
            }
        ),
    )
    url = forms.URLField(
        max_length=500,
        required=False,
        label="Link da URL (Externo)",
        widget=forms.URLInput(
            attrs={
                "class": CAMPO_PADRAO,
                "placeholder": "https://exemplo.com",
            }
        ),
    )
    logo = forms.ImageField(
        required=False,
        label="Logo personalizada",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": "image/png,image/jpeg,image/webp,image/gif",
                "class": (
                    "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 "
                    "file:rounded-xl file:border-0 file:text-sm file:font-semibold "
                    "file:bg-emerald-50 file:text-[#00776d] hover:file:bg-emerald-100 cursor-pointer"
                ),
            }
        ),
    )
    icone = forms.ChoiceField(
        choices=[("", "Selecione um ícone padrão")] + ICONE_RECURSO_CHOICES,
        required=False,
        label="Ícone Padrão",
        widget=forms.Select(attrs={"class": CAMPO_PADRAO}),
    )

    def __init__(self, *args, recurso=None, **kwargs):
        self.recurso = recurso
        super().__init__(*args, **kwargs)
        self.fields["grupos"].queryset = GrupoEspaco.objects.filter(ativo=True).order_by("nome")

        if not self.is_bound and not recurso:
            grupo_todos = GrupoEspaco.objects.filter(nome__iexact="Todos", ativo=True).first()
            if grupo_todos:
                self.initial.setdefault("grupos", [grupo_todos.pk])

    def clean(self):
        cleaned_data = super().clean()
        arquivo = cleaned_data.get("arquivo")
        url = cleaned_data.get("url")

        arquivo_existente = bool(getattr(self.recurso, "arquivo", None))
        url_existente = bool(getattr(self.recurso, "url", None))

        if not arquivo and not url and not arquivo_existente and not url_existente:
            raise forms.ValidationError(
                "Você deve preencher o campo de URL ou enviar um arquivo."
            )

        # Quando o usuário informa uma nova URL, ela substitui o arquivo existente.
        # Quando envia um novo arquivo, ele substitui a URL existente.
        if arquivo and url:
            raise forms.ValidationError(
                "Preencha apenas um: ou o arquivo ou o link da URL, não ambos."
            )
        return cleaned_data


class FuncionarioEdicaoForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=GrupoEspaco.objects.none(),
        required=True,
        label="Grupos/Espaços",
        widget=GrupoCheckboxSelectMultiple,
        help_text=(
            "Todos libera acesso a todos os espaços. Para segregar, desmarque Todos "
            "e selecione um ou mais grupos específicos."
        ),
    )
    nova_senha = forms.CharField(
        label="Nova senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": CAMPO_PADRAO,
                "placeholder": "Deixe em branco para manter a senha atual",
                "autocomplete": "new-password",
            }
        ),
    )

    confirmar_senha = forms.CharField(
        label="Confirmar nova senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": CAMPO_PADRAO,
                "placeholder": "Repita a nova senha",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = Funcionario
        fields = [
            "username",
            "nome",
            "email",
            "unidade_fabril",
            "centro_custo",
            "departamento",
            "grupos",
            "ativo",
            "is_staff",
            "vinculado_ad",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupos"].queryset = GrupoEspaco.objects.filter(ativo=True).order_by("nome")

        for nome, campo in self.fields.items():
            if nome in ["ativo", "is_staff", "vinculado_ad"]:
                campo.widget.attrs["class"] = CHECKBOX
            elif nome not in ["grupos", "nova_senha", "confirmar_senha"]:
                campo.widget.attrs["class"] = CAMPO_PADRAO

            if isinstance(campo, forms.ModelChoiceField):
                campo.empty_label = "-- Selecione uma opção --"
                # Centro de Custo é apenas para registro, não é obrigatório
                if nome == "centro_custo":
                    campo.required = False

        self.fields["username"].label = "Usuário"
        self.fields["nome"].label = "Nome"
        self.fields["email"].label = "E-mail"
        self.fields["unidade_fabril"].label = "Unidade Fabril"
        self.fields["centro_custo"].label = "Centro de Custo"
        self.fields["departamento"].label = "Departamento"
        self.fields["ativo"].label = "Usuário ativo"
        self.fields["is_staff"].label = "Staff"
        self.fields["vinculado_ad"].label = "Vinculado ao Active Directory"
        self.fields["vinculado_ad"].help_text = (
            "O usuário informado acima deve ser exatamente igual ao login de rede "
            "(sAMAccountName) do colaborador no AD."
        )

    def clean_nome(self):
        nome = self.cleaned_data.get("nome")
        return nome.upper() if nome else nome

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            qs = Funcionario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        vinculado_ad = cleaned_data.get("vinculado_ad")
        nova_senha = cleaned_data.get("nova_senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

        # Se for usuário do AD e tentou digitar algo nos campos de senha
        if vinculado_ad and (nova_senha or confirmar_senha):
            raise forms.ValidationError(
                "Cadastro vinculado ao AD, não será possível alterar a senha por aqui"
            )

        if not nova_senha and not confirmar_senha:
            return cleaned_data

        if not nova_senha:
            self.add_error("nova_senha", "Informe a nova senha.")

        if not confirmar_senha:
            self.add_error("confirmar_senha", "Confirme a nova senha.")

        if nova_senha and confirmar_senha and nova_senha != confirmar_senha:
            self.add_error("confirmar_senha", "As senhas informadas não coincidem.")

        return cleaned_data

    def save(self, commit=True):
        funcionario = super().save(commit=False)
        nova_senha = self.cleaned_data.get("nova_senha")
        
        # Se estiver vinculado ao AD, garante senha inutilizável
        if funcionario.vinculado_ad:
            funcionario.set_unusable_password()
            funcionario.deve_trocar_senha = False
        elif nova_senha:
            funcionario.set_password(nova_senha)
            funcionario.deve_trocar_senha = False

        if commit:
            funcionario.save()
            self.save_m2m()
        return funcionario


class GrupoEspacoForm(forms.ModelForm):
    class Meta:
        model = GrupoEspaco
        fields = ["nome", "descricao", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": CAMPO_PADRAO, "placeholder": "Ex: Financeiro"}),
            "descricao": forms.TextInput(
                attrs={"class": CAMPO_PADRAO, "placeholder": "Descrição opcional do grupo/espaço"}
            ),
            "ativo": forms.CheckboxInput(attrs={"class": CHECKBOX}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.grupo_sistema:
            self.fields["nome"].disabled = True
            self.fields["ativo"].disabled = True
            self.fields["nome"].help_text = "Este é um grupo do sistema e não pode ser renomeado."
            self.fields["ativo"].help_text = "O grupo Todos deve permanecer ativo."

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if nome.casefold() == "todos":
            existente = GrupoEspaco.objects.filter(nome__iexact="Todos")
            if self.instance.pk:
                existente = existente.exclude(pk=self.instance.pk)
            if existente.exists():
                raise forms.ValidationError("Já existe o grupo reservado Todos.")
        return nome
