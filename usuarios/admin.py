from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CentroCusto, Ferramenta, Funcionario, LinkUtil, UnidadeFabril, Departamento


@admin.register(Funcionario)
class FuncionarioAdmin(UserAdmin):
    list_display = (
        "username", "nome", "centro_custo", "unidade_fabril", "departamento", "ativo", "is_staff", "vinculado_ad", "email",
    )
    list_filter = (
        "ativo", "is_staff", "is_superuser", "vinculado_ad", "centro_custo", "unidade_fabril", "departamento", "email",
    )
    search_fields = ("username", "nome", "email")
    ordering = ("nome",)
    fieldsets = UserAdmin.fieldsets + (
        ("Dados corporativos", {"fields": ("nome", "unidade_fabril", "centro_custo", "departamento", "ativo", "vinculado_ad")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Dados corporativos", {"fields": ("nome", "unidade_fabril", "centro_custo", "departamento", "ativo", "vinculado_ad")}),
    )


class FerramentaInline(admin.TabularInline):
    model = Ferramenta
    extra = 1


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao")
    search_fields = ("codigo", "descricao")
    ordering = ("codigo",)
    inlines = (FerramentaInline,)


@admin.register(Ferramenta)
class FerramentaAdmin(admin.ModelAdmin):
    list_display = ("nome", "centro_custo", "url")
    list_filter = ("centro_custo",)
    search_fields = ("nome", "url", "centro_custo__codigo", "centro_custo__descricao")
    ordering = ("centro_custo", "nome")


@admin.register(LinkUtil)
class LinkUtilAdmin(admin.ModelAdmin):
    list_display = ("nome", "url")
    search_fields = ("nome", "url")
    ordering = ("nome",)


@admin.register(UnidadeFabril)
class UnidadeFabrilAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)