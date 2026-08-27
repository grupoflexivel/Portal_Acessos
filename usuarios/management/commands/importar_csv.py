import csv
import re
import unicodedata
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from usuarios.models import CentroCusto, Departamento, Funcionario, UnidadeFabril


COLUNAS_OBRIGATORIAS = {"nome", "centro_custo_codigo", "centro_custo_descricao", "unidade_fabril_nome", "departamento",}

def texto_limpo(valor):
    return (valor or "").strip()


def gerar_base_username(nome):
    """Cria primeiro.ultimo, sem acentos ou caracteres inválidos."""
    partes = texto_limpo(nome).split()
    if not partes:
        raise ValueError("nome vazio")
    primeiro, ultimo = partes[0], partes[-1]
    base = f"{primeiro}.{ultimo}"
    base = unicodedata.normalize("NFKD", base).encode("ASCII", "ignore").decode("ASCII")
    base = re.sub(r"[^a-zA-Z0-9._-]", "", base).lower().strip("._-")
    if not base:
        raise ValueError("nome não produziu um username válido")
    return base[:150]


def proximo_username(nome):
    base = gerar_base_username(nome)
    candidato = base
    numero = 2
    while Funcionario.objects.filter(username=candidato).exists():
        sufixo = str(numero)
        candidato = f"{base[:150 - len(sufixo)]}{sufixo}"
        numero += 1
    return candidato


class Command(BaseCommand):
    help = "Importa ou atualiza funcionários a partir de um arquivo CSV UTF-8."

    def add_arguments(self, parser):
        parser.add_argument("arquivo_csv", type=str, help="Caminho para o arquivo CSV")

    def handle(self, *args, **options):
        caminho = Path(options["arquivo_csv"])
        if not caminho.is_file():
            raise CommandError(f"Arquivo inexistente ou inválido: {caminho}")
        if caminho.stat().st_size == 0:
            raise CommandError("O CSV está vazio.")

        contadores = {"criados": 0, "atualizados": 0, "centros": 0, "unidades": 0, "departamentos": 0, "erros": 0}
        emails_processados = set()

        try:
            arquivo = caminho.open("r", encoding="utf-8-sig", newline="")
        except OSError as erro:
            raise CommandError(f"Não foi possível abrir o arquivo: {erro}") from erro

        with arquivo:
            leitor = csv.DictReader(arquivo, delimiter=";")
            if not leitor.fieldnames:
                raise CommandError("O CSV não possui cabeçalho.")
            leitor.fieldnames = [texto_limpo(coluna) for coluna in leitor.fieldnames]
            ausentes = COLUNAS_OBRIGATORIAS - set(leitor.fieldnames)
            if ausentes:
                raise CommandError("Colunas obrigatórias ausentes: " + ", ".join(sorted(ausentes)))

            total_linhas = 0
            for numero_linha, linha in enumerate(leitor, start=2):
                total_linhas += 1
                try:
                    self._processar_linha(linha, numero_linha, emails_processados, contadores)
                except (ValueError, ValidationError, IntegrityError) as erro:
                    contadores["erros"] += 1
                    self.stdout.write(self.style.ERROR(f"Linha {numero_linha}: {erro}"))

        if total_linhas == 0:
            raise CommandError("O CSV possui cabeçalho, mas não contém registros.")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Importação concluída."))
        self.stdout.write(f"Usuários criados: {contadores['criados']}")
        self.stdout.write(f"Usuários atualizados: {contadores['atualizados']}")
        self.stdout.write(f"Centros de custo criados: {contadores['centros']}")
        self.stdout.write(f"Unidades fabris criadas: {contadores['unidades']}")
        self.stdout.write(f"Departamentos criados: {contadores['departamentos']}")
        mensagem_erros = f"Erros encontrados: {contadores['erros']}"
        estilo = self.style.WARNING if contadores["erros"] else self.style.SUCCESS
        self.stdout.write(estilo(mensagem_erros))

    def _processar_linha(self, linha, numero_linha, emails_processados, contadores):
        nome = texto_limpo(linha.get("nome"))
        email = texto_limpo(linha.get("email")).lower()
        codigo = texto_limpo(linha.get("centro_custo_codigo"))
        descricao = texto_limpo(linha.get("centro_custo_descricao"))
        unidade_nome = texto_limpo(linha.get("unidade_fabril_nome"))
        departamento_nome = texto_limpo(linha.get("departamento"))

        if not nome:
            raise ValueError("nome é obrigatório")
        if email:
            try:
                validate_email(email)
            except ValidationError as erro:
                raise ValueError("email inválido") from erro
            
            if email in emails_processados:
                self.stdout.write(self.style.WARNING(
                    f"Linha {numero_linha}: email duplicado no CSV; registro será atualizado com os últimos dados."
                ))
            emails_processados.add(email)
        if not codigo:
            raise ValueError("centro_custo_codigo é obrigatório")
        if not descricao:
            raise ValueError("centro_custo_descricao é obrigatório")
        if not unidade_nome:
            raise ValueError("unidade_fabril_nome é obrigatório")
        if not departamento_nome:
            raise ValueError("departamento é obrigatório")

        with transaction.atomic():
            unidade, unidade_criada = UnidadeFabril.objects.get_or_create(nome=unidade_nome)
            if unidade_criada:
                contadores["unidades"] += 1

            departamento, departamento_criado = Departamento.objects.get_or_create(nome=departamento_nome)
            if departamento_criado:
                contadores["departamentos"] += 1

            centro, centro_criado = CentroCusto.objects.get_or_create(
                codigo=codigo, defaults={"descricao": descricao}
            )
            if centro_criado:
                contadores["centros"] += 1
            elif centro.descricao != descricao:
                centro.descricao = descricao
                centro.save(update_fields=["descricao"])

            # Localiza o funcionário priorizando o e-mail (se houver), ou pelo nome exato
            funcionario = None
            if email:
                funcionario = Funcionario.objects.filter(email__iexact=email).first()
            
            if not funcionario:
                funcionario = Funcionario.objects.filter(nome__iexact=nome).first()

            if funcionario is None:
                funcionario = Funcionario(
                    username=proximo_username(nome),
                    nome=nome,
                    email=email if email else "",
                    centro_custo=centro,
                    unidade_fabril=unidade,
                    departamento=departamento,
                    ativo=True,
                    deve_trocar_senha=True,
                )
                funcionario.set_password("Flex@123")
                funcionario.save()
                contadores["criados"] += 1
            else:
                funcionario.nome = nome
                funcionario.email = email if email else ""
                funcionario.unidade_fabril = unidade
                funcionario.ativo = True
                funcionario.centro_custo = centro
                funcionario.departamento = departamento
                funcionario.save(update_fields=["nome", "email", "centro_custo", "unidade_fabril", "departamento", "ativo"])
                contadores["atualizados"] += 1