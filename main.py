import os
import unicodedata
from datetime import datetime

import questionary
from questionary import Style, Choice

from exercicios import (
    EXERCICIOS, DESCRICOES_TREINO,
    CARDIO, PROGRESSAO, PERIODIZACAO, OBSERVACOES,
)
from gerar_pdf import gerar_pdf


# ── Estilo visual ──────────────────────────────────────────────────────────────

ESTILO = Style([
    ("qmark",       "fg:#ffffff bold"),
    ("question",    "fg:#ffffff bold"),
    ("answer",      "fg:#aaaaaa"),
    ("pointer",     "fg:#ffffff bold"),
    ("highlighted", "fg:#ffffff bold"),
    ("selected",    "fg:#aaaaaa"),
    ("separator",   "fg:#444444"),
    ("instruction", "fg:#555555"),
    ("text",        "fg:#ffffff"),
    ("disabled",    "fg:#444444 italic"),
])


# ── Utilitários ────────────────────────────────────────────────────────────────

def limpar():
    os.system('cls' if os.name == 'nt' else 'clear')


def separador(titulo=""):
    pad = 46 - len(titulo)
    print(f"\n  -- {titulo} {'-' * pad}")


def _norm(texto):
    return (unicodedata.normalize('NFKD', texto)
            .encode('ascii', 'ignore').decode('ascii').lower().strip())


def _val_inteiro(minimo=None, maximo=None):
    def validate(v):
        try:
            n = int(v)
        except ValueError:
            return "Digite um número inteiro."
        if minimo is not None and n < minimo:
            return f"Valor mínimo: {minimo}."
        if maximo is not None and n > maximo:
            return f"Valor máximo: {maximo}."
        return True
    return validate


def _val_float(minimo=None):
    def validate(v):
        try:
            n = float(v.replace(',', '.'))
        except ValueError:
            return "Digite um número válido (ex: 78.5 ou 78,5)."
        if minimo is not None and n <= minimo:
            return f"Valor deve ser maior que {minimo}."
        return True
    return validate


def _val_data(v):
    if not v or not v.strip():
        return True
    try:
        datetime.strptime(v.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return "Use o formato dd/mm/aaaa (ex: 24/06/2026)."


def _val_nao_vazio(v):
    return True if v.strip() else "Campo obrigatório."


def formatar_nome_arquivo(nome, data_str):
    slug = _norm(nome)
    slug = ''.join(c if c.isalnum() else '_' for c in slug)
    slug = '_'.join(p for p in slug.split('_') if p)
    return f"{slug}_{data_str}.pdf"


# ── Formulário interativo ──────────────────────────────────────────────────────

def coletar_dados():
    limpar()
    print()
    print("  +==================================================+")
    print("  |  GERADOR DE PLANO DE TREINO — PERSONAL TRAINING  |")
    print("  +==================================================+")
    print()

    # ── Dados pessoais ─────────────────────────────────────────────────────────
    separador("DADOS PESSOAIS")
    print()

    nome = questionary.text(
        "Nome completo do cliente:",
        validate=_val_nao_vazio,
        style=ESTILO,
    ).ask()

    idade = questionary.text(
        "Idade (anos):",
        validate=_val_inteiro(minimo=10, maximo=100),
        style=ESTILO,
    ).ask()

    sexo = questionary.select(
        "Sexo:",
        choices=[
            Choice("Masculino", value="M"),
            Choice("Feminino",  value="F"),
        ],
        style=ESTILO,
    ).ask()

    peso = questionary.text(
        "Peso em kg (ex: 78.5):",
        validate=_val_float(minimo=0),
        style=ESTILO,
    ).ask()

    altura = questionary.text(
        "Altura em cm (ex: 175):",
        validate=_val_inteiro(minimo=100, maximo=250),
        style=ESTILO,
    ).ask()

    # ── Objetivo ───────────────────────────────────────────────────────────────
    separador("OBJETIVO E EXPERIÊNCIA")
    print()

    objetivo = questionary.select(
        "Objetivo principal:",
        choices=[
            Choice("Hipertrofia muscular", value="hipertrofia"),
            Choice("Emagrecimento",        value="emagrecimento"),
            Choice("Correção Postural",    value="postural"),
        ],
        style=ESTILO,
    ).ask()

    nivel = questionary.select(
        "Nível de experiência:",
        choices=[
            Choice("Iniciante       — até 1 ano de treino",      value="iniciante"),
            Choice("Intermediário   — 1 a 3 anos de treino",     value="intermediario"),
            Choice("Avançado        — mais de 3 anos de treino", value="avancado"),
        ],
        style=ESTILO,
    ).ask()

    # ── Divisão de treino (por sexo) ───────────────────────────────────────────
    separador("DIVISÃO DE TREINO")
    print()

    if sexo == "F":
        divisao = questionary.select(
            "Escolha a divisão de treino:",
            choices=[
                Choice(
                    "AB Feminino 4x      — A: Pernas/Glúteos  |  B: Braço/Ombro",
                    value="AB_4x",
                ),
                Choice(
                    "ABC Feminino        — A: Glúteos/Post.   |  B: Pernas/Quad  |  C: Upper Body",
                    value="ABC",
                ),
                Choice(
                    "ABCD Feminino       — A: Glúteos  |  B: Pernas  |  C: Costas/Bíceps  |  D: Ombro/Tríceps",
                    value="ABCD",
                ),
                Choice(
                    "Full Body 3x        — FB-A, FB-B, FB-C com exercícios diferentes",
                    value="full_body_3x",
                ),
            ],
            style=ESTILO,
        ).ask()
    else:
        divisao = questionary.select(
            "Escolha a divisão de treino:",
            choices=[
                Choice(
                    "AB Masculino 4x     — A: Peito/Tríceps/Ombro/Quad  |  B: Costas/Bíceps/Post.",
                    value="AB_4x",
                ),
                Choice(
                    "ABC Masculino       — A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas/Ombro",
                    value="ABC",
                ),
                Choice(
                    "ABCD Masculino      — A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas  |  D: Ombro/Core",
                    value="ABCD",
                ),
                Choice(
                    "Push Pull Legs      — Push: Peito/Ombro/Tríceps  |  Pull: Costas/Bíceps  |  Legs: Pernas",
                    value="push_pull_legs",
                ),
                Choice(
                    "Full Body 3x        — FB-A, FB-B, FB-C com exercícios diferentes",
                    value="full_body_3x",
                ),
            ],
            style=ESTILO,
        ).ask()

    # ── Periodização ───────────────────────────────────────────────────────────
    separador("PERIODIZAÇÃO")
    print()

    periodizacao_key = questionary.select(
        "Modelo de periodização:",
        choices=[
            Choice(
                "Linear              — aumento progressivo de carga a cada semana",
                value="linear",
            ),
            Choice(
                "Ondulatória Semanal — alterna volume e intensidade semanalmente",
                value="ondulatoria_semanal",
            ),
            Choice(
                "Ondulatória Diária  — alterna volume e intensidade a cada treino (DUP)",
                value="ondulatoria_diaria",
            ),
            Choice(
                "Em Blocos           — bloco de volume -> força -> pico",
                value="blocos",
            ),
            Choice(
                "Reversa             — começa com alta intensidade, aumenta volume",
                value="reversa",
            ),
        ],
        style=ESTILO,
    ).ask()

    # ── Frequência e tempo ─────────────────────────────────────────────────────
    separador("FREQUÊNCIA E DURAÇÃO")
    print()

    frequencia = questionary.select(
        "Frequência semanal de treinos:",
        choices=[
            Choice("2x por semana", value=2),
            Choice("3x por semana", value=3),
            Choice("4x por semana", value=4),
            Choice("5x por semana", value=5),
            Choice("6x por semana", value=6),
        ],
        style=ESTILO,
    ).ask()

    tempo = questionary.select(
        "Tempo disponível por sessão:",
        choices=[
            Choice("30 minutos", value=30),
            Choice("45 minutos", value=45),
            Choice("60 minutos", value=60),
            Choice("75 minutos", value=75),
            Choice("90 minutos", value=90),
        ],
        style=ESTILO,
    ).ask()

    # ── Estrutura e contexto ───────────────────────────────────────────────────
    separador("ESTRUTURA E CONTEXTO")
    print()

    equipamentos = questionary.select(
        "Equipamentos disponíveis:",
        choices=[
            Choice("Academia completa",           value="Academia completa"),
            Choice("Halteres e banco",            value="Halteres e banco"),
            Choice("Halteres, banco e barra",     value="Halteres, banco e barra"),
            Choice("Elásticos e peso corporal",   value="Elásticos e peso corporal"),
            Choice("Outro (digitar manualmente)", value="__outro__"),
        ],
        style=ESTILO,
    ).ask()

    if equipamentos == "__outro__":
        equipamentos = questionary.text(
            "Descreva os equipamentos disponíveis:",
            validate=_val_nao_vazio,
            style=ESTILO,
        ).ask()

    restricoes = questionary.text(
        "Restrições ou lesões (Enter para nenhuma):",
        style=ESTILO,
    ).ask()

    # ── Período do plano ───────────────────────────────────────────────────────
    separador("PERÍODO DO PLANO")
    print()

    data_raw = questionary.text(
        "Data de início dd/mm/aaaa (Enter = hoje):",
        validate=_val_data,
        style=ESTILO,
    ).ask()

    data_inicio = (data_raw.strip()
                   if data_raw and data_raw.strip()
                   else datetime.now().strftime("%d/%m/%Y"))

    periodo = questionary.select(
        "Duração do plano:",
        choices=[
            Choice("4 semanas",  value=4),
            Choice("6 semanas",  value=6),
            Choice("8 semanas",  value=8),
            Choice("10 semanas", value=10),
            Choice("12 semanas", value=12),
            Choice("16 semanas", value=16),
        ],
        style=ESTILO,
    ).ask()

    return {
        'nome':          nome,
        'idade':         int(idade),
        'sexo':          sexo,
        'peso':          float(peso.replace(',', '.')),
        'altura':        int(altura),
        'objetivo':      objetivo,
        'nivel':         nivel,
        'divisao':       divisao,
        'periodizacao':  periodizacao_key,
        'frequencia':    frequencia,
        'tempo':         tempo,
        'equipamentos':  equipamentos,
        'restricoes':    restricoes or "",
        'data_inicio':   data_inicio,
        'periodo':       periodo,
    }


# ── Confirmação final ──────────────────────────────────────────────────────────

def confirmar(dados, nome_arquivo):
    sexo_label    = "Masculino" if dados['sexo'] == "M" else "Feminino"
    divisao_label = {
        "AB_4x":"A/B (4x)", "ABC":"A/B/C", "ABCD":"A/B/C/D",
        "push_pull_legs":"Push/Pull/Legs", "full_body_3x":"Full Body (3x)",
    }.get(dados['divisao'], dados['divisao'])
    per_label = {
        "linear":"Linear", "ondulatoria_semanal":"Ondulatória Semanal",
        "ondulatoria_diaria":"Ondulatória Diária", "blocos":"Em Blocos",
        "reversa":"Reversa",
    }.get(dados['periodizacao'], dados['periodizacao'])

    print()
    print("  -- RESUMO " + "-" * 42)
    print()
    print(f"  Cliente       : {dados['nome']}  ({sexo_label})")
    print(f"  Objetivo      : {dados['objetivo'].title()}")
    print(f"  Divisão       : {divisao_label}  ({dados['frequencia']}x/sem / {dados['tempo']} min)")
    print(f"  Periodização  : {per_label}")
    print(f"  Período       : {dados['periodo']} semanas a partir de {dados['data_inicio']}")
    print(f"  Arquivo       : {nome_arquivo}")
    print()

    return questionary.confirm(
        "Gerar o PDF com esses dados?",
        default=True,
        style=ESTILO,
    ).ask()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    dados = coletar_dados()

    sexo_key        = "masculino" if dados['sexo'] == "M" else "feminino"
    treinos         = EXERCICIOS[sexo_key][dados['divisao']]
    descricoes      = DESCRICOES_TREINO[sexo_key][dados['divisao']]
    cardio          = CARDIO[dados['objetivo']]
    progressao      = PROGRESSAO[dados['nivel']]
    periodizacao    = PERIODIZACAO[dados['periodizacao']]
    observacoes     = OBSERVACOES[dados['objetivo']]

    data_hoje    = datetime.now().strftime("%Y-%m-%d")
    nome_arquivo = formatar_nome_arquivo(dados['nome'], data_hoje)

    if not confirmar(dados, nome_arquivo):
        print("\n  Cancelado. Nenhum arquivo gerado.\n")
        return

    print()
    print("  Gerando PDF...")

    try:
        gerar_pdf(
            dados, treinos, descricoes,
            cardio, progressao, periodizacao, observacoes,
            nome_arquivo,
        )
    except Exception as exc:
        print(f"\n  ERRO ao gerar PDF: {exc}")
        raise

    print(f"  PDF gerado com sucesso!")
    print(f"  -> {os.path.abspath(nome_arquivo)}")
    print()


if __name__ == "__main__":
    main()
