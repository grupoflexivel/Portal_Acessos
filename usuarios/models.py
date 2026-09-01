from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


ICONE_RECURSO_CHOICES = [
    ("link", "Link"),
    ("globe", "Site / Internet"),
    ("document", "Documento"),
    ("folder", "Pasta / Arquivos"),
    ("chart", "Gráfico / Relatórios"),
    ("computer", "Sistema / Aplicação"),
    ("database", "Banco de dados"),
    ("email", "E-mail"),
    ("users", "Usuários"),
    ("support", "Suporte"),
    ("shield", "Segurança"),
    ("settings", "Configurações"),
]


class UnidadeFabril(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Unidade fabril"
        verbose_name_plural = "Unidades fabris"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class CentroCusto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descricao = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Centro de custo"
        verbose_name_plural = "Centros de custo"
        ordering = ("codigo",)

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class GrupoEspaco(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    descricao = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=True)
    grupo_sistema = models.BooleanField(
        default=False,
        editable=False,
        help_text="Marca grupos internos protegidos contra exclusão/renomeação.",
    )

    class Meta:
        verbose_name = "Grupo/Espaço"
        verbose_name_plural = "Grupos/Espaços"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

    @property
    def eh_todos(self):
        nome_lower = self.nome.casefold()
        return nome_lower in ("espaço geral", "geral")


class Ferramenta(models.Model):
    # CAMPO LEGADO:
    # Mantido temporariamente para evitar uma remoção destrutiva antes da migração
    # dos dados antigos. O sistema novo NÃO usa centro_custo para autorização.
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.SET_NULL,
        related_name="ferramentas",
        null=True,
        blank=True,
        editable=False,
    )

    grupos = models.ManyToManyField(
        GrupoEspaco,
        related_name="ferramentas",
        blank=True,
        verbose_name="Grupos/Espaços",
    )

    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to="ferramentas/", blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)
    logo = models.ImageField(
        upload_to="ferramentas/logos/",
        blank=True,
        null=True,
        verbose_name="Logo personalizada",
    )
    icone = models.CharField(
        max_length=30,
        choices=ICONE_RECURSO_CHOICES,
        blank=True,
        default="",
        verbose_name="Ícone",
    )

    class Meta:
        verbose_name = "Ferramenta / Recurso"
        verbose_name_plural = "Ferramentas / Recursos"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if not self.arquivo and not self.url:
            raise ValidationError("Você deve preencher o campo de URL ou enviar um arquivo.")
        if self.arquivo and self.url:
            raise ValidationError("Preencha apenas um: ou o arquivo ou o link da URL, não ambos.")


class LinkUtil(models.Model):
    """Modelo legado de recursos gerais.

    Ele é mantido para compatibilidade com os registros existentes. A partir desta
    alteração, também recebe grupos/espaços e participa da mesma regra de acesso.
    Novos recursos são cadastrados preferencialmente em Ferramenta.
    """

    grupos = models.ManyToManyField(
        GrupoEspaco,
        related_name="links_uteis",
        blank=True,
        verbose_name="Grupos/Espaços",
    )
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to="links_uteis/", blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)
    logo = models.ImageField(
        upload_to="links_uteis/logos/",
        blank=True,
        null=True,
        verbose_name="Logo personalizada",
    )
    icone = models.CharField(
        max_length=30,
        choices=ICONE_RECURSO_CHOICES,
        blank=True,
        default="",
        verbose_name="Ícone",
    )

    class Meta:
        verbose_name = "Link legado"
        verbose_name_plural = "Links legados"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if not self.arquivo and not self.url:
            raise ValidationError("Você deve preencher o campo de URL ou enviar um arquivo.")
        if self.arquivo and self.url:
            raise ValidationError("Preencha apenas um: ou o arquivo ou o link da URL, não ambos.")


class Departamento(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

class Funcionario(AbstractUser):
    nome = models.CharField(max_length=255)
    unidade_fabril = models.ForeignKey(
        UnidadeFabril,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funcionarios",
    )
    centro_custo = models.ForeignKey(
        CentroCusto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funcionarios",
    )

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funcionarios",
    )
    grupos = models.ManyToManyField(
        GrupoEspaco,
        related_name="funcionarios",
        blank=True,
        verbose_name="Grupos/Espaços",
    )

    ativo = models.BooleanField(default=True)
    deve_trocar_senha = models.BooleanField(default=False)
    vinculado_ad = models.BooleanField(
        default=False,
        verbose_name="Vinculado ao Active Directory",
        help_text="Quando marcado, o login é autenticado no Active Directory em vez da senha local.",

    )

    # --- NOVOS CAMPOS PARA CONTROLE DE SEGURANÇA (BLOQUEIO POR SENHA) ---
    tentativas_falhas = models.PositiveIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ("nome",)

    def __str__(self):
        return self.nome or self.username

    # --- MÉTODO AUXILIAR PARA VERIFICAR O BLOQUEIO DE 1 MINUTO ---
    def esta_bloqueado_temporariamente(self):
        if self.bloqueado_ate and timezone.now() < self.bloqueado_ate:
            return True
        if self.bloqueado_ate and timezone.now() >= self.bloqueado_ate:
            self.bloqueado_ate = None
            self.save(update_fields=["bloqueado_ate"])
        return False
