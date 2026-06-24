import io
import os
import tempfile
import unicodedata
from datetime import date, datetime

import streamlit as st

from exercicios import (
    EXERCICIOS, DESCRICOES_TREINO,
    CARDIO, PROGRESSAO, PERIODIZACAO, OBSERVACOES,
)
from gerar_pdf import gerar_pdf


st.set_page_config(
    page_title="Gerador de Treino Personalizado",
    page_icon="🏋️",
    layout="centered",
)

st.markdown("""
<style>
    /* botão primário maior */
    div[data-testid="stButton"] > button[kind="primary"] {
        height: 3.2em;
        font-size: 1.05em;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    /* botão de download em destaque */
    div[data-testid="stDownloadButton"] > button {
        height: 3em;
        font-size: 1em;
        font-weight: 600;
    }
    /* subtítulo */
    .subtitulo {
        color: #555555;
        font-size: 1.05em;
        margin-top: -0.6em;
        margin-bottom: 0.2em;
    }
</style>
""", unsafe_allow_html=True)


# ── Cabeçalho ─────────────────────────────────────────────────────────────────

st.title("Gerador de Treino Personalizado")
st.markdown('<p class="subtitulo">Studio Personal Training</p>', unsafe_allow_html=True)
st.divider()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('ascii').lower().strip()
    s = ''.join(c if c.isalnum() else '_' for c in s)
    return '_'.join(p for p in s.split('_') if p)


# ── Mapeamentos ───────────────────────────────────────────────────────────────

DIVISOES_F = {
    "AB Feminino 4x  —  A: Pernas/Glúteos  |  B: Braço/Ombro":                                     "AB_4x",
    "ABC Feminino  —  A: Glúteos/Post.  |  B: Pernas/Quad  |  C: Upper Body":                      "ABC",
    "ABCD Feminino  —  A: Glúteos  |  B: Pernas  |  C: Costas/Bíceps  |  D: Ombro/Tríceps":       "ABCD",
    "Full Body 3x  —  FB-A, FB-B, FB-C com exercícios diferentes":                                  "full_body_3x",
}

DIVISOES_M = {
    "AB Masculino 4x  —  A: Peito/Tríceps/Ombro/Quad  |  B: Costas/Bíceps/Post.":                 "AB_4x",
    "ABC Masculino  —  A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas/Ombro":                "ABC",
    "ABCD Masculino  —  A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas  |  D: Ombro/Core":  "ABCD",
    "Push Pull Legs  —  Push: Peito/Ombro/Tríceps  |  Pull: Costas/Bíceps  |  Legs: Pernas":      "push_pull_legs",
    "Full Body 3x  —  FB-A, FB-B, FB-C com exercícios diferentes":                                  "full_body_3x",
}

PERIODIZACOES = {
    "Linear  —  aumento progressivo de carga a cada semana":                   "linear",
    "Ondulatória Semanal  —  alterna volume e intensidade semanalmente":        "ondulatoria_semanal",
    "Ondulatória Diária (DUP)  —  alterna volume e intensidade a cada treino": "ondulatoria_diaria",
    "Em Blocos  —  bloco de volume → força → pico":                            "blocos",
    "Reversa  —  começa com alta intensidade, aumenta volume":                 "reversa",
}

OBJETIVOS = {
    "Hipertrofia":        "hipertrofia",
    "Emagrecimento":      "emagrecimento",
    "Correção Postural":  "postural",
}

NIVEIS = {
    "Iniciante  —  até 1 ano de treino":          "iniciante",
    "Intermediário  —  1 a 3 anos de treino":     "intermediario",
    "Avançado  —  mais de 3 anos de treino":      "avancado",
}

EQUIPAMENTOS_OPCOES = ["Academia completa", "Halteres", "Elásticos", "Peso corporal", "Outro"]


# ── Seção: Dados do Cliente ───────────────────────────────────────────────────

with st.expander("📋 Dados do Cliente", expanded=True):
    nome = st.text_input("Nome completo", placeholder="Ex: Maria Silva")

    col_idade, col_sexo = st.columns([1, 2])
    with col_idade:
        idade = st.number_input("Idade", min_value=10, max_value=100, value=30, step=1)
    with col_sexo:
        sexo_label = st.radio("Sexo", ["Feminino", "Masculino"], horizontal=True)

    sexo = "F" if sexo_label == "Feminino" else "M"

    col_peso, col_altura = st.columns(2)
    with col_peso:
        peso = st.number_input("Peso (kg)", min_value=30.0, max_value=300.0,
                               value=70.0, step=0.5, format="%.1f")
    with col_altura:
        altura = st.number_input("Altura (cm)", min_value=100, max_value=250,
                                 value=170, step=1)

    col_data, col_periodo = st.columns(2)
    with col_data:
        data_inicio = st.date_input("Data de início", value=date.today())
    with col_periodo:
        periodo = st.selectbox("Período do plano (semanas)", [4, 6, 8, 10, 12, 16], index=2)

    restricoes = st.text_area(
        "Restrições / Lesões",
        placeholder="Descreva lesões ou limitações (deixe em branco se não houver)",
        height=80,
    )


# ── Seção: Configuração do Treino ─────────────────────────────────────────────

with st.expander("⚙️ Configuração do Treino", expanded=True):
    col_obj, col_nivel = st.columns(2)
    with col_obj:
        objetivo_label = st.selectbox("Objetivo", list(OBJETIVOS.keys()))
    with col_nivel:
        nivel_label = st.selectbox("Nível", list(NIVEIS.keys()))

    col_freq, col_tempo = st.columns(2)
    with col_freq:
        frequencia = st.selectbox(
            "Frequência semanal", [2, 3, 4, 5, 6], index=2,
            format_func=lambda x: f"{x}x por semana",
        )
    with col_tempo:
        tempo = st.selectbox(
            "Tempo por sessão", [30, 45, 60, 75, 90], index=2,
            format_func=lambda x: f"{x} minutos",
        )

    equipamentos_sel = st.multiselect(
        "Equipamentos disponíveis",
        EQUIPAMENTOS_OPCOES,
        default=["Academia completa"],
    )

    equipamentos_outro_txt = ""
    if "Outro" in equipamentos_sel:
        equipamentos_outro_txt = st.text_input(
            "Descreva o(s) equipamento(s) adicional(is):",
            placeholder="Ex: Kettlebell, TRX",
        )

    divisoes_map = DIVISOES_F if sexo == "F" else DIVISOES_M
    divisao_label = st.selectbox("Divisão de treino", list(divisoes_map.keys()))

    periodizacao_label = st.selectbox("Periodização", list(PERIODIZACOES.keys()))


st.divider()


# ── Botão principal ───────────────────────────────────────────────────────────

col_l, col_btn, col_r = st.columns([1, 2, 1])
with col_btn:
    gerar_clicado = st.button(
        "🏋️  Gerar Treino em PDF",
        use_container_width=True,
        type="primary",
    )


# ── Geração do PDF ────────────────────────────────────────────────────────────

if gerar_clicado:
    # Validações
    erros = []
    if not nome.strip():
        erros.append("Informe o nome completo do cliente.")
    if not equipamentos_sel:
        erros.append("Selecione pelo menos um equipamento.")
    if "Outro" in equipamentos_sel and not equipamentos_outro_txt.strip():
        erros.append("Descreva o equipamento personalizado selecionado.")

    if erros:
        for e in erros:
            st.error(e)
        st.stop()

    # Montar string de equipamentos
    equip_partes = [
        equipamentos_outro_txt.strip() if item == "Outro" else item
        for item in equipamentos_sel
    ]
    equip_str = ", ".join(equip_partes)

    objetivo        = OBJETIVOS[objetivo_label]
    nivel           = NIVEIS[nivel_label]
    divisao         = divisoes_map[divisao_label]
    periodizacao_key = PERIODIZACOES[periodizacao_label]

    dados = {
        'nome':         nome.strip(),
        'idade':        int(idade),
        'sexo':         sexo,
        'peso':         float(peso),
        'altura':       int(altura),
        'objetivo':     objetivo,
        'nivel':        nivel,
        'divisao':      divisao,
        'periodizacao': periodizacao_key,
        'frequencia':   frequencia,
        'tempo':        tempo,
        'equipamentos': equip_str,
        'restricoes':   restricoes.strip() if restricoes else "",
        'data_inicio':  data_inicio.strftime("%d/%m/%Y"),
        'periodo':      periodo,
    }

    sexo_key    = "masculino" if sexo == "M" else "feminino"
    treinos     = EXERCICIOS[sexo_key][divisao]
    descricoes  = DESCRICOES_TREINO[sexo_key][divisao]
    cardio      = CARDIO[objetivo]
    progressao  = PROGRESSAO[nivel]
    periodizacao = PERIODIZACAO[periodizacao_key]
    observacoes = OBSERVACOES[objetivo]

    data_hoje    = datetime.now().strftime("%Y-%m-%d")
    nome_arquivo = f"{_slug(nome.strip())}_{data_hoje}.pdf"

    with st.spinner("Gerando seu treino..."):
        try:
            tmp_path = os.path.join(tempfile.gettempdir(), nome_arquivo)
            gerar_pdf(
                dados, treinos, descricoes,
                cardio, progressao, periodizacao, observacoes,
                tmp_path,
            )
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_path)
        except Exception as exc:
            st.error(f"Erro ao gerar o PDF: {exc}")
            st.stop()

    st.success("Treino gerado com sucesso!")

    col_dl_l, col_dl, col_dl_r = st.columns([1, 2, 1])
    with col_dl:
        st.download_button(
            label="📥  Baixar PDF",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=True,
        )
