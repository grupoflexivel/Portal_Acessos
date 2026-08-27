from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django import forms
from .models import CentroCusto, Funcionario
import unicodedata


class FuncionarioCadastroForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = (
            "nome",
            "email",
            "unidade_fabril",
            "centro_custo",
            "departamento",
            "ativo",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            if nome == "ativo":
                campo.widget.attrs["class"] = "h-4 w-4 rounded border-slate-300 text-[#00776d] focus:ring-[#00776d]"
            else:
                campo.widget.attrs["class"] = "w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-[#00776d] focus:ring-4 focus:ring-emerald-700/10"

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and Funcionario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean_nome(self):
        nome = self.cleaned_data.get("nome")
        if not nome:
            return nome
        
        # Converte para maiúsculas logo na validação
        nome_maiusculo = nome.upper()
        
        if Funcionario.objects.filter(nome__iexact=nome_maiusculo).exists():
            raise forms.ValidationError("Já existe um colaborador cadastrado com exatamente este nome.")
        return nome_maiusculo

    def _gerar_username(self, nome_completo):
        """Transforma 'João da Silva' em 'joao.silva' de forma única."""
        nfkd = unicodedata.normalize('NFKD', nome_completo)
        nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
        
        partes = nome_limpo.split()
        if not partes:
            return "usuario"
        
        if len(partes) == 1:
            base_username = partes[0]
        else:
            base_username = f"{partes[0]}.{partes[-1]}"
            
        username = base_username
        contador = 1
        
        while Funcionario.objects.filter(username=username).exists():
            username = f"{base_username}{contador}"
            contador += 1
            
        return username

    def save(self, commit=True):
        funcionario = super().save(commit=False)
        
        # O nome já vem em maiúsculo do clean_nome
        funcionario.username = self._gerar_username(funcionario.nome)
        
        senha_padrao = "Flex@123"
        funcionario.set_password(senha_padrao)
        funcionario.deve_trocar_senha = True  
        
        if commit:
            funcionario.save()
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
    TIPO_CHOICES = (
        ('colaborador', 'Links/Arquivos Colaboradores (Geral)'),
        ('centro_custo', 'Links/Arquivos Centro de Custos'),
    )

    tipo_destino = forms.ChoiceField(
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm focus:border-[#00776d] focus:outline-none focus:ring-1 focus:ring-[#00776d]'
        }),
        label="Destino"
    )
    
    centro_custo = forms.ModelChoiceField(
        queryset=CentroCusto.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm focus:border-[#00776d] focus:outline-none focus:ring-1 focus:ring-[#00776d]'
        }),
        label="Centro de Custo (Obrigatório se o destino for Centro de Custos)"
    )

    nome = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm placeholder-slate-400 focus:border-[#00776d] focus:outline-none focus:ring-1 focus:ring-[#00776d]',
            'placeholder': 'Ex: Sistema de Ponto / Manual de Vendas'
        }),
        label="Nome"
    )

    arquivo = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-emerald-50 file:text-[#00776d] hover:file:bg-emerald-100 cursor-pointer'
        }),
        label="Enviar Arquivo"
    )

    url = forms.URLField(
        max_length=500,
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm placeholder-slate-400 focus:border-[#00776d] focus:outline-none focus:ring-1 focus:ring-[#00776d]',
            'placeholder': 'https://exemplo.com'
        }),
        label="Link da URL (Externo)"
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_destino')
        cc = cleaned_data.get('centro_custo')
        arquivo = cleaned_data.get('arquivo')
        url = cleaned_data.get('url')

        if tipo == 'centro_custo' and not cc:
            raise forms.ValidationError("Você deve selecionar um Centro de Custo para este tipo de destino.")

        if not arquivo and not url:
            raise forms.ValidationError("Você deve preencher o campo de URL ou enviar um arquivo.")
        if arquivo and url:
            raise forms.ValidationError("Preencha apenas um: ou o arquivo ou o link da URL, não ambos.")

        return cleaned_data


class FuncionarioEdicaoForm(forms.ModelForm):
    nova_senha = forms.CharField(
        label="Nova senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": (
                    "w-full rounded-xl border border-slate-300 "
                    "bg-white px-4 py-3 pr-12 text-sm text-slate-900 "
                    "outline-none transition "
                    "focus:border-[#00776d] "
                    "focus:ring-4 focus:ring-emerald-700/10"
                ),
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
                "class": (
                    "w-full rounded-xl border border-slate-300 "
                    "bg-white px-4 py-3 pr-12 text-sm text-slate-900 "
                    "outline-none transition "
                    "focus:border-[#00776d] "
                    "focus:ring-4 focus:ring-emerald-700/10"
                ),
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
            "ativo",
            "is_staff",
        ]
        

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        campo_padrao = (
            "w-full rounded-xl border border-slate-300 "
            "bg-white px-4 py-3 text-sm text-slate-900 "
            "outline-none transition "
            "focus:border-[#00776d] "
            "focus:ring-4 focus:ring-emerald-700/10"
        )

        checkbox = (
            "h-5 w-5 rounded border-slate-300 "
            "text-[#00776d] focus:ring-[#00776d]"
        )

        for nome, campo in self.fields.items():
            if nome in ["ativo", "is_staff"]:
                campo.widget.attrs["class"] = checkbox
            elif nome not in ["nova_senha", "confirmar_senha"]:
                campo.widget.attrs["class"] = campo_padrao

        self.fields["username"].label = "Usuário"
        self.fields["nome"].label = "Nome"
        self.fields["email"].label = "E-mail"
        self.fields["unidade_fabril"].label = "Unidade Fabril"
        self.fields["centro_custo"].label = "Centro de Custo Principal"
        self.fields["departamento"].label = "Departamento"
        self.fields["ativo"].label = "Usuário ativo"
        self.fields["is_staff"].label = "Staff"

    def clean_nome(self):
        nome = self.cleaned_data.get("nome")
        if nome:
            return nome.upper()
        return nome

    def clean(self):
        cleaned_data = super().clean()

        nova_senha = cleaned_data.get("nova_senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

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
        if nova_senha:
            funcionario.set_password(nova_senha)

        if commit:
            funcionario.save()

        return funcionario