from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CentroCusto, Ferramenta, Funcionario, UnidadeFabril, Departamento, GrupoEspaco


@admin.register(Funcionario)
class FuncionarioAdmin(UserAdmin):
    list_display = (
        "username", "nome", "centro_custo", "unidade_fabril", "departamento", "ativo", "is_staff", "vinculado_ad", "email",
    )
    list_filter = (
        "ativo", "is_staff", "is_superuser", "vinculado_ad", "centro_custo", "unidade_fabril", "departamento",
    )
    search_fields = ("username", "nome", "email")
    ordering = ("nome",)
    fieldsets = UserAdmin.fieldsets + (
        ("Dados corporativos", {"fields": ("nome", "unidade_fabril", "centro_custo", "departamento", "ativo", "vinculado_ad", "grupos")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Dados corporativos", {"fields": ("nome", "unidade_fabril", "centro_custo", "departamento", "ativo", "vinculado_ad", "grupos")}),
    )


class FerramentaInline(admin.TabularInline):
    model = Ferramenta.grupos.through 
    extra = 1


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao")
    search_fields = ("codigo", "descricao")
    ordering = ("codigo",)


@admin.register(Ferramenta)
class FerramentaAdmin(admin.ModelAdmin):
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