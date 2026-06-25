import glob
import json
import os
import smtplib
import tempfile
import unicodedata
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st

from exercicios import (
    EXERCICIOS, DESCRICOES_TREINO,
    CARDIO, PROGRESSAO, PERIODIZACAO, OBSERVACOES,
)
from gerar_pdf import gerar_pdf
from gerar_pdf_anamnese import gerar_pdf_anamnese
from gerar_pdf_postural import gerar_pdf_postural
from gerar_pdf_progresso import gerar_pdf_progresso
import random

try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False


# ── Configuração da página ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Studio Personal Training",
    page_icon="🏋️",
    layout="centered",
)

st.markdown("""
<style>
    div[data-testid="stButton"] > button[kind="primary"] {
        height: 3.2em; font-size: 1.05em; font-weight: 700; letter-spacing: 0.02em;
    }
    div[data-testid="stDownloadButton"] > button {
        height: 3em; font-size: 1em; font-weight: 600;
    }
    .subtitulo {
        color: #555555; font-size: 1.05em; margin-top: -0.6em; margin-bottom: 0.2em;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('ascii').lower().strip()
    s = ''.join(c if c.isalnum() else '_' for c in s)
    return '_'.join(p for p in s.split('_') if p)


def _formatar_anamnese_texto(dados):
    def bloco(titulo, pares):
        linhas = ["", "=" * 60, titulo, "=" * 60]
        for k, v in pares:
            linhas.append(f"{k}: {v}")
        return linhas

    linhas = [
        "FICHA DE ANAMNESE",
        f"Recebida em: {dados.get('data_envio', '')}",
    ]

    dp = dados.get('dados_pessoais', {})
    linhas += bloco("1. DADOS PESSOAIS", [
        ("Nome",             dp.get('nome', '')),
        ("Data nascimento",  dp.get('data_nascimento', '')),
        ("Sexo",             dp.get('sexo', '')),
        ("Telefone",         dp.get('telefone', '')),
        ("E-mail",           dp.get('email', '')),
        ("Ocupação",         dp.get('ocupacao', '')),
        ("Cidade/Estado",    dp.get('cidade_estado', '')),
    ])

    obj = dados.get('objetivo', {})
    linhas += bloco("2. OBJETIVO", [
        ("Objetivos",        ", ".join(obj.get('objetivos', []))),
        ("Descrição",        obj.get('descricao', '')),
        ("Praticou antes?",  obj.get('praticou_antes', '')),
        ("Atividade ant.",   obj.get('atividade_anterior', '') or "—"),
        ("Por que parou?",   obj.get('motivo_parou', '') or "—"),
    ])

    parq = dados.get('parq', {})
    linhas += ["", "=" * 60, "3. PAR-Q+", "=" * 60]
    for q in parq.get('questoes', []):
        linhas.append(f"[{q['resposta']}]  {q['pergunta']}")
    if parq.get('alerta_medico'):
        linhas.append("\n*** ALERTA: recomendada avaliação médica antes de iniciar. ***")

    hs = dados.get('historico_saude', {})
    coluna_str = hs.get('coluna', 'Não')
    if hs.get('coluna_regiao'):
        coluna_str += f" ({hs['coluna_regiao']})"
    linhas += bloco("4. HISTÓRICO DE SAÚDE", [
        ("Doenças",              hs.get('doencas', '') or "Nenhuma"),
        ("Medicamentos",         hs.get('medicamentos', '') or "Nenhum"),
        ("Cirurgias",            hs.get('cirurgia', '') or "Nenhuma"),
        ("Hist. fam. cardíaco",  hs.get('historico_cardiaco', '')),
        ("Diabetes",             hs.get('diabetes', '')),
        ("Hipertensão",          hs.get('hipertensao', '')),
        ("Coluna",               coluna_str),
        ("Lesões",               hs.get('lesoes', '') or "Nenhuma"),
        ("Gravidez",             hs.get('gravidez', '')),
    ])

    ev = dados.get('estilo_vida', {})
    linhas += bloco("5. ESTILO DE VIDA", [
        ("Sono",               f"{ev.get('horas_sono','')} / {ev.get('qualidade_sono','')}"),
        ("Estresse",           ev.get('estresse', '')),
        ("Álcool",             ev.get('alcool', '')),
        ("Tabagismo",          ev.get('fuma', '')),
        ("Ativ. trabalho",     ev.get('atividade_trabalho', '')),
        ("Horas sentado/dia",  ev.get('horas_sentado', '')),
    ])

    disp = dados.get('disponibilidade', {})
    linhas += bloco("6. DISPONIBILIDADE", [
        ("Dias/semana",   str(disp.get('dias_semana', ''))),
        ("Horário",       disp.get('horario', '')),
        ("Tempo/sessão",  f"{disp.get('tempo_sessao','')} min"),
        ("Local",         disp.get('local', '')),
        ("Equipamentos",  ", ".join(disp.get('equipamentos', []))),
        ("Não gosta de",  disp.get('nao_gosta', '') or "—"),
        ("Prefere",       disp.get('prefere', '') or "—"),
    ])

    med = dados.get('medidas', {})
    p_v  = med.get('peso', 0)
    a_v  = med.get('altura', 0)
    ca_v = med.get('circ_abdominal', 0)
    pg_v = med.get('perc_gordura', 0)
    linhas += bloco("7. MEDIDAS INICIAIS", [
        ("Peso",          f"{p_v} kg" if p_v > 0 else "Não informado"),
        ("Altura",        f"{a_v} cm" if a_v > 0 else "Não informado"),
        ("Circ. abd.",    f"{ca_v} cm" if ca_v > 0 else "Não informado"),
        ("% gordura",     f"{pg_v}%" if pg_v > 0 else "Não informado"),
        ("Observações",   med.get('obs', '') or "—"),
    ])

    termo = dados.get('termo', {})
    linhas += bloco("8. TERMO", [
        ("Aceito",     "Sim" if termo.get('aceito') else "Não"),
        ("Assinatura", termo.get('assinatura', '')),
    ])

    return "\n".join(linhas)


def _enviar_email(nome, dados):
    """Retorna (bool sucesso, str mensagem)."""
    try:
        from config import EMAIL_REMETENTE, EMAIL_SENHA, EMAIL_DESTINATARIO
        if not EMAIL_REMETENTE or not EMAIL_SENHA:
            return False, "nao_configurado"
        corpo = _formatar_anamnese_texto(dados)
        msg = MIMEMultipart()
        msg['From']    = EMAIL_REMETENTE
        msg['To']      = EMAIL_DESTINATARIO
        msg['Subject'] = f"Nova Anamnese — {nome}"
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        with smtplib.SMTP('smtp.gmail.com', 587) as srv:
            srv.starttls()
            srv.login(EMAIL_REMETENTE, EMAIL_SENHA)
            srv.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())
        return True, "ok"
    except Exception as e:
        return False, str(e)


def _encontrar_foto(pasta, view_key):
    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        p = os.path.join(pasta, f"{view_key}.{ext}")
        if os.path.exists(p):
            return p
    return None


def _enviar_email_fotos(nome, data_avaliacao, pasta, n_fotos):
    try:
        from config import EMAIL_REMETENTE, EMAIL_SENHA, EMAIL_DESTINATARIO
        if not EMAIL_REMETENTE or not EMAIL_SENHA:
            return False, "nao_configurado"
        corpo = (
            f"Fotos de avaliação postural recebidas.\n\n"
            f"Cliente: {nome}\n"
            f"Data: {data_avaliacao}\n"
            f"Fotos enviadas: {n_fotos}/6\n"
        )
        msg = MIMEMultipart()
        msg['From']    = EMAIL_REMETENTE
        msg['To']      = EMAIL_DESTINATARIO
        msg['Subject'] = f"Fotos Posturais — {nome}"
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        with smtplib.SMTP('smtp.gmail.com', 587) as srv:
            srv.starttls()
            srv.login(EMAIL_REMETENTE, EMAIL_SENHA)
            srv.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())
        return True, "ok"
    except Exception as e:
        return False, str(e)


def _idx_default(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0


# ── Helpers: gestão de clientes ───────────────────────────────────────────────

def _cadastro_path(slug):  return f"dados_clientes/cadastro_{slug}.json"
def _medidas_path(slug):   return f"dados_clientes/medidas_{slug}.json"
def _peso_path(slug):      return f"dados_clientes/peso_{slug}.json"


def _carregar_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _salvar_json(path, data):
    os.makedirs("dados_clientes", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _todos_cadastros():
    os.makedirs("dados_clientes", exist_ok=True)
    result = []
    for arq in sorted(glob.glob("dados_clientes/cadastro_*.json")):
        d = _carregar_json(arq, None)
        if d:
            result.append(d)
    return result


def _chart_peso(registros, meta=None, height=300):
    if not _HAS_PLOTLY or not registros:
        return None
    datas = [r.get("data", "") for r in registros]
    pesos = [float(r["peso"]) if r.get("peso") else None for r in registros]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=datas, y=pesos, mode="lines+markers", name="Peso (kg)",
        line=dict(color="#333333", width=2), marker=dict(size=6),
    ))
    if meta:
        fig.add_hline(
            y=float(meta), line_dash="dash", line_color="#888888",
            annotation_text=f"Meta: {meta} kg", annotation_position="top right",
        )
    fig.update_layout(
        xaxis_title="Data", yaxis_title="Peso (kg)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=20, t=20, b=60), height=height,
    )
    fig.update_xaxes(tickangle=-30)
    return fig


def _chart_medidas(registros, height=350):
    if not _HAS_PLOTLY or not registros:
        return None
    CAMPOS = [
        ("circ_abd", "Circ. Abd. (cm)"),
        ("cintura",  "Cintura (cm)"),
        ("quadril",  "Quadril (cm)"),
        ("coxa_d",   "Coxa D. (cm)"),
        ("braco_d",  "Braço D. (cm)"),
    ]
    CORES = ["#222222", "#555555", "#888888", "#aaaaaa", "#cccccc"]
    datas = [r.get("data", "") for r in registros]
    fig = go.Figure()
    for (key, label), cor in zip(CAMPOS, CORES):
        vals = [float(r[key]) if r.get(key) else None for r in registros]
        if any(v for v in vals):
            fig.add_trace(go.Scatter(
                x=datas, y=vals, mode="lines+markers", name=label,
                line=dict(color=cor, width=1.5), marker=dict(size=5),
            ))
    fig.update_layout(
        xaxis_title="Data", yaxis_title="cm",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=20, t=20, b=60), height=height,
    )
    fig.update_xaxes(tickangle=-30)
    return fig


# ── Constantes ────────────────────────────────────────────────────────────────

PARQ_PERGUNTAS = [
    "Seu médico já disse que você tem algum problema cardíaco?",
    "Você sente dor no peito ao praticar atividade física?",
    "Você sentiu dor no peito no último mês sem fazer exercício?",
    "Você já perdeu o equilíbrio por tontura ou já desmaiou?",
    "Você tem algum problema ósseo ou articular que piora com exercício?",
    "Seu médico já receitou medicamento para pressão ou problema cardíaco?",
    "Você tem alguma outra razão pela qual não deveria praticar exercício?",
]

DIVISOES_F = {
    "AB Feminino 4x  —  A: Pernas/Glúteos  |  B: Braço/Ombro":                                     "AB_4x",
    "ABC Feminino  —  A: Glúteos/Post.  |  B: Pernas/Quad  |  C: Upper Body":                      "ABC",
    "ABCD Feminino  —  A: Glúteos  |  B: Pernas  |  C: Costas/Bíceps  |  D: Ombro/Tríceps":       "ABCD",
    "Full Body 3x  —  FB-A, FB-B, FB-C com exercícios diferentes":                                  "full_body_3x",
    "— 50+ —  Full Body 2x  —  FB-A e FB-B alternados (baixo impacto)":                            "full_body_50_2x",
    "— 50+ —  Full Body 3x  —  FB-A, FB-B e FB-C  (Core/Equilíbrio no C)":                        "full_body_50_3x",
}

DIVISOES_M = {
    "AB Masculino 4x  —  A: Peito/Tríceps/Ombro/Quad  |  B: Costas/Bíceps/Post.":                 "AB_4x",
    "ABC Masculino  —  A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas/Ombro":                "ABC",
    "ABCD Masculino  —  A: Peito/Tríceps  |  B: Costas/Bíceps  |  C: Pernas  |  D: Ombro/Core":  "ABCD",
    "Push Pull Legs  —  Push: Peito/Ombro/Tríceps  |  Pull: Costas/Bíceps  |  Legs: Pernas":      "push_pull_legs",
    "Full Body 3x  —  FB-A, FB-B, FB-C com exercícios diferentes":                                  "full_body_3x",
    "— 50+ —  Full Body 2x  —  FB-A e FB-B alternados (baixo impacto)":                            "full_body_50_2x",
    "— 50+ —  Full Body 3x  —  FB-A, FB-B e FB-C  (Core/Equilíbrio no C)":                        "full_body_50_3x",
}

PERIODIZACOES = {
    "Linear  —  aumento progressivo de carga a cada semana":                   "linear",
    "Ondulatória Semanal  —  alterna volume e intensidade semanalmente":        "ondulatoria_semanal",
    "Ondulatória Diária (DUP)  —  alterna volume e intensidade a cada treino": "ondulatoria_diaria",
    "Em Blocos  —  bloco de volume → força → pico":                            "blocos",
    "Reversa  —  começa com alta intensidade, aumenta volume":                 "reversa",
}

OBJETIVOS = {
    "Hipertrofia":       "hipertrofia",
    "Emagrecimento":     "emagrecimento",
    "Correção Postural": "postural",
}

NIVEIS = {
    "Iniciante  —  até 1 ano de treino":        "iniciante",
    "Intermediário  —  1 a 3 anos de treino":   "intermediario",
    "Avançado  —  mais de 3 anos de treino":    "avancado",
}

EQUIPAMENTOS_OPCOES = ["Academia completa", "Halteres", "Elásticos", "Peso corporal", "Outro"]

VISTAS_POSTURAL = [
    {"key": "frente",       "label": "Frente",
     "instrucao": "Em pé, braços ao lado do corpo, olhando para frente"},
    {"key": "costas",       "label": "Costas",
     "instrucao": "Em pé, braços ao lado do corpo, de costas para a câmera"},
    {"key": "lat_direita",  "label": "Lateral Direita",
     "instrucao": "Em pé, lado direito para a câmera, braços ao lado do corpo"},
    {"key": "lat_esquerda", "label": "Lateral Esquerda",
     "instrucao": "Em pé, lado esquerdo para a câmera, braços ao lado do corpo"},
    {"key": "agachamento",  "label": "Agachamento",
     "instrucao": "Agachamento completo de frente, calcanhares no chão se possível"},
    {"key": "core",         "label": "Core / Prancha",
     "instrucao": "Posição de prancha frontal, corpo reto da cabeça aos calcanhares"},
]


# ── Exibição de anamnese (área da professora) ─────────────────────────────────

def _exibir_anamnese_streamlit(dados):
    dp = dados.get('dados_pessoais', {})
    with st.expander("📋 Dados Pessoais", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Nome:** {dp.get('nome','')}")
            st.markdown(f"**Nascimento:** {dp.get('data_nascimento','')}")
            st.markdown(f"**Sexo:** {dp.get('sexo','')}")
            st.markdown(f"**Telefone:** {dp.get('telefone','')}")
        with c2:
            st.markdown(f"**E-mail:** {dp.get('email','')}")
            st.markdown(f"**Ocupação:** {dp.get('ocupacao','')}")
            st.markdown(f"**Cidade/Estado:** {dp.get('cidade_estado','')}")

    obj = dados.get('objetivo', {})
    with st.expander("🎯 Objetivo"):
        st.markdown(f"**Objetivos:** {', '.join(obj.get('objetivos',[]))}")
        if obj.get('descricao'):
            st.markdown(f"**Descrição:** {obj['descricao']}")
        st.markdown(f"**Praticou antes:** {obj.get('praticou_antes','')}")
        if obj.get('atividade_anterior'):
            st.markdown(f"**Atividade anterior:** {obj['atividade_anterior']}")
        if obj.get('motivo_parou'):
            st.markdown(f"**Por que parou:** {obj['motivo_parou']}")

    parq = dados.get('parq', {})
    with st.expander("❤️ PAR-Q+"):
        for q in parq.get('questoes', []):
            icone = "🔴" if q['resposta'] == "Sim" else "🟢"
            st.markdown(f"{icone} **{q['resposta']}** — {q['pergunta']}")
        if parq.get('alerta_medico'):
            st.warning("⚠️ Uma ou mais respostas indicam necessidade de avaliação médica.")

    hs = dados.get('historico_saude', {})
    with st.expander("🏥 Histórico de Saúde"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Doenças:** {hs.get('doencas','') or 'Nenhuma'}")
            st.markdown(f"**Medicamentos:** {hs.get('medicamentos','') or 'Nenhum'}")
            st.markdown(f"**Cirurgias:** {hs.get('cirurgia','') or 'Nenhuma'}")
            st.markdown(f"**Hist. fam. cardíaco:** {hs.get('historico_cardiaco','')}")
            st.markdown(f"**Diabetes:** {hs.get('diabetes','')}")
        with c2:
            st.markdown(f"**Hipertensão:** {hs.get('hipertensao','')}")
            coluna_str = hs.get('coluna','Não')
            if hs.get('coluna_regiao'):
                coluna_str += f" — {hs['coluna_regiao']}"
            st.markdown(f"**Coluna:** {coluna_str}")
            st.markdown(f"**Lesões:** {hs.get('lesoes','') or 'Nenhuma'}")
            st.markdown(f"**Gravidez:** {hs.get('gravidez','')}")

    ev = dados.get('estilo_vida', {})
    with st.expander("🌿 Estilo de Vida"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Sono:** {ev.get('horas_sono','')} — {ev.get('qualidade_sono','')}")
            st.markdown(f"**Estresse:** {ev.get('estresse','')}")
            st.markdown(f"**Álcool:** {ev.get('alcool','')}")
        with c2:
            st.markdown(f"**Tabagismo:** {ev.get('fuma','')}")
            st.markdown(f"**Atividade no trabalho:** {ev.get('atividade_trabalho','')}")
            st.markdown(f"**Horas sentado/dia:** {ev.get('horas_sentado','')}")

    disp = dados.get('disponibilidade', {})
    with st.expander("📅 Disponibilidade e Preferências"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Dias/semana:** {disp.get('dias_semana','')}")
            st.markdown(f"**Horário:** {disp.get('horario','')}")
            st.markdown(f"**Tempo/sessão:** {disp.get('tempo_sessao','')} min")
            st.markdown(f"**Local:** {disp.get('local','')}")
        with c2:
            st.markdown(f"**Equipamentos:** {', '.join(disp.get('equipamentos',[]))}")
            st.markdown(f"**Não gosta de:** {disp.get('nao_gosta','') or '—'}")
            st.markdown(f"**Prefere:** {disp.get('prefere','') or '—'}")

    med = dados.get('medidas', {})
    with st.expander("📏 Medidas Iniciais"):
        c1, c2 = st.columns(2)
        p_v  = med.get('peso', 0)
        a_v  = med.get('altura', 0)
        ca_v = med.get('circ_abdominal', 0)
        pg_v = med.get('perc_gordura', 0)
        with c1:
            st.markdown(f"**Peso:** {f'{p_v} kg' if p_v > 0 else 'Não informado'}")
            st.markdown(f"**Altura:** {f'{a_v} cm' if a_v > 0 else 'Não informado'}")
        with c2:
            st.markdown(f"**Circ. abdominal:** {f'{ca_v} cm' if ca_v > 0 else 'Não informado'}")
            st.markdown(f"**% gordura:** {f'{pg_v}%' if pg_v > 0 else 'Não informado'}")
        if med.get('obs'):
            st.markdown(f"**Observações:** {med['obs']}")

    termo = dados.get('termo', {})
    with st.expander("📝 Termo de Responsabilidade"):
        st.markdown(f"**Aceito:** {'✅ Sim' if termo.get('aceito') else '❌ Não'}")
        st.markdown(f"**Assinatura digital:** {termo.get('assinatura','')}")


# ── Página: Home ──────────────────────────────────────────────────────────────

def _pagina_home():
    st.markdown("""
    <div style="text-align:center; padding: 2.5rem 0 1.5rem 0;">
        <div style="font-size: 3rem;">🏋️</div>
        <h1 style="font-size: 2rem; font-weight: 700; margin: 0.3rem 0;">Studio Personal Training</h1>
        <p style="color: #666; font-size: 1.05rem; margin: 0;">Como você deseja continuar?</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="border:1px solid #ddd; border-radius:12px; padding:1.8rem 1.0rem;
                    text-align:center; background:#f8f9fa; min-height:195px;">
            <div style="font-size:2.8rem; margin-bottom:0.4rem;">🧑‍🤸</div>
            <h3 style="margin:0 0 0.5rem 0; font-size:1.1rem;">Ficha de Anamnese</h3>
            <p style="color:#666; font-size:0.85rem; margin:0; line-height:1.5;">
                Preencha sua ficha de anamnese para iniciar seu programa de treino personalizado.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Preencher Anamnese", key="btn_home_aluno",
                     use_container_width=True, type="primary"):
            st.session_state['area'] = 'cliente'
            st.rerun()

    with col2:
        st.markdown("""
        <div style="border:1px solid #ddd; border-radius:12px; padding:1.8rem 1.0rem;
                    text-align:center; background:#f8f9fa; min-height:195px;">
            <div style="font-size:2.8rem; margin-bottom:0.4rem;">📸</div>
            <h3 style="margin:0 0 0.5rem 0; font-size:1.1rem;">Avaliação Postural</h3>
            <p style="color:#666; font-size:0.85rem; margin:0; line-height:1.5;">
                Envie suas fotos para avaliação postural completa com análise profissional.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enviar Fotos", key="btn_home_postural",
                     use_container_width=True, type="primary"):
            st.session_state['area'] = 'postural'
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("""
        <div style="border:1px solid #ddd; border-radius:12px; padding:1.8rem 1.0rem;
                    text-align:center; background:#f8f9fa; min-height:195px;">
            <div style="font-size:2.8rem; margin-bottom:0.4rem;">👤</div>
            <h3 style="margin:0 0 0.5rem 0; font-size:1.1rem;">Portal do Cliente</h3>
            <p style="color:#666; font-size:0.85rem; margin:0; line-height:1.5;">
                Registre seu peso, acompanhe sua evolução e visualize seu progresso.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Acessar Portal", key="btn_home_portal",
                     use_container_width=True, type="primary"):
            st.session_state['area'] = 'portal_cliente'
            st.rerun()

    with col4:
        st.markdown("""
        <div style="border:1px solid #ddd; border-radius:12px; padding:1.8rem 1.0rem;
                    text-align:center; background:#f8f9fa; min-height:195px;">
            <div style="font-size:2.8rem; margin-bottom:0.4rem;">👩‍💼</div>
            <h3 style="margin:0 0 0.5rem 0; font-size:1.1rem;">Acesso Professora</h3>
            <p style="color:#666; font-size:0.85rem; margin:0; line-height:1.5;">
                Gerencie clientes, anamneses e gere planos de treino personalizados.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Acesso Restrito", key="btn_home_prof", use_container_width=True):
            st.session_state['area'] = 'professora'
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center; color:#bbb; font-size:0.8rem;">'
        'Studio Personal Training — Sistema de Gestão</p>',
        unsafe_allow_html=True,
    )


# ── Página: Anamnese (cliente) ────────────────────────────────────────────────

def _pagina_anamnese():
    if st.button("← Início", key="btn_voltar_anamnese"):
        st.session_state['area'] = None
        st.session_state.pop('anamnese_confirmada', None)
        st.rerun()

    # Tela de confirmação pós-envio
    if st.session_state.get('anamnese_confirmada'):
        st.balloons()
        st.success(
            "✅ Anamnese enviada com sucesso!  "
            "Em breve a professora entrará em contato."
        )
        st.info("Você pode fechar esta página ou clicar em '← Início' para voltar.")
        return

    st.title("Ficha de Anamnese")
    st.markdown('<p class="subtitulo">Studio Personal Training</p>', unsafe_allow_html=True)
    st.divider()

    # ── 1. Dados Pessoais ──────────────────────────────────────────────────────
    with st.expander("1. Dados Pessoais", expanded=True):
        nome_cl = st.text_input("Nome completo *", key="an_nome")

        col_nasc, col_sexo = st.columns([1, 2])
        with col_nasc:
            data_nasc = st.date_input("Data de nascimento",
                                      value=None, format="DD/MM/YYYY", key="an_data_nasc")
        with col_sexo:
            sexo_cl = st.radio("Sexo", ["Feminino", "Masculino"],
                               horizontal=True, key="an_sexo")

        col_tel, col_email = st.columns(2)
        with col_tel:
            telefone_cl = st.text_input("Telefone / WhatsApp", key="an_tel")
        with col_email:
            email_cl = st.text_input("E-mail", key="an_email")

        col_ocup, col_cidade = st.columns(2)
        with col_ocup:
            ocupacao_cl = st.text_input("Ocupação profissional", key="an_ocupacao")
        with col_cidade:
            cidade_cl = st.text_input("Cidade / Estado", key="an_cidade")

    # ── 2. Objetivo ────────────────────────────────────────────────────────────
    with st.expander("2. Objetivo", expanded=True):
        objetivos_opcoes = [
            "Emagrecimento", "Hipertrofia", "Condicionamento físico",
            "Saúde e qualidade de vida", "Reabilitação", "Correção postural", "Outro",
        ]
        objetivos_sel = st.multiselect(
            "Objetivo principal (pode marcar mais de um) *",
            objetivos_opcoes, key="an_objetivos",
        )
        objetivo_desc = st.text_area("Descreva seu objetivo com suas palavras",
                                     height=80, key="an_obj_desc")
        praticou = st.radio("Já praticou exercícios antes?", ["Não", "Sim"],
                            horizontal=True, key="an_praticou")
        atividade_ant = ""
        motivo_parou  = ""
        if praticou == "Sim":
            atividade_ant = st.text_input("Qual atividade e por quanto tempo?",
                                          key="an_atividade_ant")
            motivo_parou  = st.text_input("Por que parou? (opcional)",
                                          key="an_motivo_parou")

    # ── 3. PAR-Q+ ─────────────────────────────────────────────────────────────
    with st.expander("3. PAR-Q+ — Prontidão para Atividade Física", expanded=True):
        st.caption("Responda com sinceridade. Essas informações são confidenciais.")
        parq_resps = []
        for i, pergunta in enumerate(PARQ_PERGUNTAS):
            resp = st.radio(pergunta, ["Não", "Sim"],
                            horizontal=True, key=f"an_parq_{i}", index=0)
            parq_resps.append(resp)
        if "Sim" in parq_resps:
            st.warning("⚠️ Recomendamos que você consulte um médico antes de iniciar o programa.")

    # ── 4. Histórico de Saúde ─────────────────────────────────────────────────
    with st.expander("4. Histórico de Saúde", expanded=True):
        doencas     = st.text_area("Possui alguma doença diagnosticada?",
                                   placeholder="Deixe em branco se não houver",
                                   height=60, key="an_doencas")
        medicamentos = st.text_area("Faz uso de medicamentos? Quais?",
                                    placeholder="Deixe em branco se não houver",
                                    height=60, key="an_meds")
        cirurgia    = st.text_input("Já fez cirurgia? Qual e quando?",
                                    placeholder="Deixe em branco se não houver",
                                    key="an_cirurgia")

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            hist_cardiaco = st.radio("Histórico familiar cardíaco?", ["Não", "Sim"],
                                     horizontal=True, key="an_hist_card")
        with col_c2:
            diabetes      = st.selectbox("Diabetes?",
                                         ["Não", "Sim", "Pré-diabetes"], key="an_diabetes")
        with col_c3:
            hipertensao   = st.selectbox("Hipertensão?",
                                         ["Não", "Sim", "Controlada c/ medicamento"],
                                         key="an_hiper")

        coluna_resp  = st.radio("Tem problemas na coluna?", ["Não", "Sim"],
                                horizontal=True, key="an_coluna")
        coluna_regiao = ""
        if coluna_resp == "Sim":
            coluna_regiao = st.text_input("Qual região? (ex: lombar, cervical)",
                                          key="an_coluna_reg")

        lesoes   = st.text_area("Tem alguma lesão ou limitação física atual?",
                                placeholder="Descreva se houver", height=60, key="an_lesoes")
        gravidez = st.selectbox("Está grávida ou pode estar grávida?",
                                ["Não se aplica", "Não", "Sim"], key="an_gravidez")

    # ── 5. Estilo de Vida ─────────────────────────────────────────────────────
    with st.expander("5. Estilo de Vida", expanded=True):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            horas_sono   = st.selectbox("Horas de sono por noite",
                                        ["menos de 5h", "5-6h", "7-8h", "mais de 8h"],
                                        index=2, key="an_sono")
            qual_sono    = st.selectbox("Qualidade do sono",
                                        ["Boa", "Regular", "Ruim"], key="an_qual_sono")
            estresse     = st.selectbox("Nível de estresse",
                                        ["Baixo", "Moderado", "Alto", "Muito alto"],
                                        index=1, key="an_estresse")
            alcool       = st.selectbox("Consome bebida alcoólica?",
                                        ["Não", "Ocasionalmente", "Frequentemente"],
                                        key="an_alcool")
        with col_e2:
            fuma         = st.selectbox("Fuma?",
                                        ["Não", "Sim", "Ex-fumante"], key="an_fuma")
            ativ_trab    = st.selectbox("Nível de atividade no trabalho",
                                        ["Sedentário", "Leve", "Moderado", "Intenso"],
                                        key="an_trab")
            h_sentado    = st.selectbox("Horas sentado por dia",
                                        ["menos de 4h", "4-6h", "6-8h", "mais de 8h"],
                                        index=1, key="an_sentado")

    # ── 6. Disponibilidade e Preferências ─────────────────────────────────────
    with st.expander("6. Disponibilidade e Preferências", expanded=True):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dias_semana_cl  = st.selectbox("Dias por semana para treinar",
                                           [2, 3, 4, 5, 6], index=1, key="an_dias")
            horario_cl      = st.selectbox("Horário preferido",
                                           ["Manhã", "Tarde", "Noite", "Indiferente"],
                                           key="an_horario")
            tempo_cl        = st.selectbox("Tempo por sessão",
                                           [30, 45, 60, 75, 90], index=2, key="an_tempo",
                                           format_func=lambda x: f"{x} min")
            local_cl        = st.selectbox("Onde vai treinar?",
                                           ["Academia", "Em casa", "Ao ar livre", "Misto"],
                                           key="an_local")

        equip_cl_opcoes = ["Academia completa", "Halteres", "Barras", "Elásticos",
                           "Peso corporal", "Bicicleta ergométrica", "Esteira", "Outro"]
        equipamentos_cl = st.multiselect("Equipamentos disponíveis",
                                         equip_cl_opcoes, key="an_equip")
        nao_gosta_cl    = st.text_input("Atividade que não gosta ou não quer fazer (opcional)",
                                        key="an_nao_gosta")
        prefere_cl      = st.text_input("Atividade que gosta ou prefere (opcional)",
                                        key="an_prefere")

    # ── 7. Medidas Iniciais ───────────────────────────────────────────────────
    with st.expander("7. Medidas Iniciais (opcional)", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            peso_cl   = st.number_input("Peso atual (kg) — 0 = não informado",
                                        min_value=0.0, max_value=300.0,
                                        value=0.0, step=0.5, format="%.1f", key="an_peso")
            altura_cl = st.number_input("Altura (cm) — 0 = não informado",
                                        min_value=0, max_value=250, value=0, key="an_altura")
        with col_m2:
            circ_abd  = st.number_input("Circunferência abdominal (cm)",
                                        min_value=0.0, value=0.0,
                                        step=0.5, format="%.1f", key="an_circ")
            perc_gord = st.number_input("% de gordura — 0 = não informado",
                                        min_value=0.0, max_value=100.0,
                                        value=0.0, step=0.1, format="%.1f", key="an_gord")
        obs_med = st.text_area("Observações sobre medidas", height=60, key="an_obs_med")

    # ── 8. Termo de Responsabilidade ──────────────────────────────────────────
    with st.expander("8. Termo de Responsabilidade", expanded=True):
        st.info(
            "Declaro que as informações acima são verdadeiras e que fui orientado(a) "
            "sobre a importância de comunicar qualquer alteração no meu estado de saúde "
            "à professora responsável. Estou ciente de que o programa de treinamento "
            "será elaborado com base nas informações fornecidas."
        )
        aceita_termo  = st.checkbox("Li e concordo com o termo acima *", key="an_termo")
        assinatura_cl = st.text_input("Nome completo para assinatura digital *",
                                      key="an_assinatura")

    st.divider()

    # ── Botão enviar ──────────────────────────────────────────────────────────
    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        enviar = st.button("📨  Enviar Anamnese", use_container_width=True,
                           type="primary", key="btn_enviar_anamnese")

    if enviar:
        erros = []
        if not nome_cl.strip():
            erros.append("Informe o nome completo.")
        if not objetivos_sel:
            erros.append("Selecione pelo menos um objetivo principal.")
        if not aceita_termo:
            erros.append("Você deve aceitar o termo de responsabilidade.")
        if not assinatura_cl.strip():
            erros.append("Informe o nome para assinatura digital.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            dados_anamnese = {
                "dados_pessoais": {
                    "nome":           nome_cl.strip(),
                    "data_nascimento": data_nasc.strftime("%d/%m/%Y") if data_nasc else "",
                    "sexo":           sexo_cl,
                    "telefone":       telefone_cl.strip(),
                    "email":          email_cl.strip(),
                    "ocupacao":       ocupacao_cl.strip(),
                    "cidade_estado":  cidade_cl.strip(),
                },
                "objetivo": {
                    "objetivos":         objetivos_sel,
                    "descricao":         objetivo_desc.strip(),
                    "praticou_antes":    praticou,
                    "atividade_anterior": atividade_ant.strip() if praticou == "Sim" else "",
                    "motivo_parou":      motivo_parou.strip() if praticou == "Sim" else "",
                },
                "parq": {
                    "questoes": [
                        {"pergunta": p, "resposta": r}
                        for p, r in zip(PARQ_PERGUNTAS, parq_resps)
                    ],
                    "alerta_medico": "Sim" in parq_resps,
                },
                "historico_saude": {
                    "doencas":          doencas.strip(),
                    "medicamentos":     medicamentos.strip(),
                    "cirurgia":         cirurgia.strip(),
                    "historico_cardiaco": hist_cardiaco,
                    "diabetes":         diabetes,
                    "hipertensao":      hipertensao,
                    "coluna":           coluna_resp,
                    "coluna_regiao":    coluna_regiao.strip() if coluna_resp == "Sim" else "",
                    "lesoes":           lesoes.strip(),
                    "gravidez":         gravidez,
                },
                "estilo_vida": {
                    "horas_sono":         horas_sono,
                    "qualidade_sono":     qual_sono,
                    "estresse":           estresse,
                    "alcool":             alcool,
                    "fuma":               fuma,
                    "atividade_trabalho": ativ_trab,
                    "horas_sentado":      h_sentado,
                },
                "disponibilidade": {
                    "dias_semana":  dias_semana_cl,
                    "horario":      horario_cl,
                    "tempo_sessao": tempo_cl,
                    "local":        local_cl,
                    "equipamentos": equipamentos_cl,
                    "nao_gosta":    nao_gosta_cl.strip(),
                    "prefere":      prefere_cl.strip(),
                },
                "medidas": {
                    "peso":           float(peso_cl),
                    "altura":         int(altura_cl),
                    "circ_abdominal": float(circ_abd),
                    "perc_gordura":   float(perc_gord),
                    "obs":            obs_med.strip(),
                },
                "termo": {
                    "aceito":     aceita_termo,
                    "assinatura": assinatura_cl.strip(),
                },
                "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "timestamp":  datetime.now().isoformat(),
            }

            # Salvar JSON
            os.makedirs("dados_clientes", exist_ok=True)
            slug = _slug(nome_cl.strip())
            ts   = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            arquivo_json = f"dados_clientes/anamnese_{slug}_{ts}.json"
            with open(arquivo_json, "w", encoding="utf-8") as f:
                json.dump(dados_anamnese, f, ensure_ascii=False, indent=2)

            # Enviar e-mail (falha silenciosa — JSON já está salvo)
            _enviar_email(nome_cl.strip(), dados_anamnese)

            st.session_state['anamnese_confirmada'] = True
            st.rerun()


# ── Página: Upload de Fotos Posturais (cliente) ──────────────────────────────

def _pagina_upload_postural():
    if st.button("← Início", key="btn_voltar_postural"):
        st.session_state['area'] = None
        st.session_state.pop('postural_confirmada', None)
        st.rerun()

    if st.session_state.get('postural_confirmada'):
        st.balloons()
        st.success("✅ Fotos enviadas com sucesso! Em breve a professora entrará em contato.")
        st.info("Você pode fechar esta página ou clicar em '← Início' para voltar.")
        return

    st.title("Avaliação Postural")
    st.markdown('<p class="subtitulo">Studio Personal Training</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("### Seus dados")
    col_nome, col_data = st.columns(2)
    with col_nome:
        nome_cl = st.text_input("Nome completo *", key="post_nome")
    with col_data:
        data_aval = st.date_input("Data da avaliação",
                                   value=date.today(), format="DD/MM/YYYY", key="post_data")

    st.divider()
    st.markdown("### Envio das fotos")
    st.info(
        "Tire as fotos com roupas justas ou maiô/bermuda, em um local bem iluminado. "
        "Fique em posição ereta e relaxada (exceto onde indicado abaixo)."
    )
    st.markdown(
        "> 💡 **Como tirar as fotos sozinho:**\n"
        "> 1. Apoie o celular em uma superfície firme (cadeira, mesa, prateleira) "
        "na altura do quadril e use o **temporizador** da câmera\n"
        "> 2. Peça ajuda para alguém fotografar\n"
        "> 3. **Grave um vídeo** girando devagar nas posições indicadas e tire print "
        "dos melhores frames — essa é a forma mais prática!"
    )

    uploads = {}
    for vista in VISTAS_POSTURAL:
        with st.expander(f"📷  {vista['label']}", expanded=True):
            st.caption(f"Instrução: {vista['instrucao']}")
            f = st.file_uploader(
                f"Foto — {vista['label']}",
                type=["jpg", "jpeg", "png"],
                key=f"post_foto_{vista['key']}",
                label_visibility="collapsed",
            )
            uploads[vista['key']] = f

    st.divider()
    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        enviar = st.button("📨  Enviar Fotos", use_container_width=True,
                           type="primary", key="btn_enviar_fotos")

    if enviar:
        erros = []
        if not nome_cl.strip():
            erros.append("Informe o nome completo.")
        n_fotos = sum(1 for f in uploads.values() if f is not None)
        if n_fotos == 0:
            erros.append("Envie pelo menos uma foto.")
        if erros:
            for e in erros:
                st.error(e)
        else:
            os.makedirs("dados_clientes", exist_ok=True)
            slug = _slug(nome_cl.strip())
            ts    = data_aval.strftime("%Y-%m-%d")
            pasta = f"dados_clientes/fotos_{slug}_{ts}"
            os.makedirs(pasta, exist_ok=True)

            fotos_salvas = []
            for vista in VISTAS_POSTURAL:
                f = uploads[vista['key']]
                if f is not None:
                    ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else "jpg"
                    save_path = os.path.join(pasta, f"{vista['key']}.{ext}")
                    with open(save_path, "wb") as out:
                        out.write(f.getbuffer())
                    fotos_salvas.append(vista['key'])

            meta = {
                "nome":           nome_cl.strip(),
                "data_avaliacao": data_aval.strftime("%d/%m/%Y"),
                "fotos_enviadas": fotos_salvas,
                "timestamp":      datetime.now().isoformat(),
            }
            with open(os.path.join(pasta, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            _enviar_email_fotos(nome_cl.strip(), data_aval.strftime("%d/%m/%Y"),
                                pasta, len(fotos_salvas))
            st.session_state['postural_confirmada'] = True
            st.rerun()


# ── Página: Portal do Cliente ────────────────────────────────────────────────

def _form_cadastro_cliente():
    st.markdown("### Criar Cadastro")
    nome_hint = st.session_state.get('portal_nome_hint', '')

    nome_c = st.text_input("Nome completo *", value=nome_hint, key="cad_nome")
    col_nasc, col_wpp = st.columns(2)
    with col_nasc:
        nasc_c = st.date_input("Data de nascimento", value=None,
                                format="DD/MM/YYYY", key="cad_nasc")
    with col_wpp:
        wpp_c = st.text_input("WhatsApp", key="cad_wpp")
    email_c = st.text_input("E-mail", key="cad_email")
    foto_c  = st.file_uploader("Foto de perfil (opcional)",
                                type=["jpg", "jpeg", "png"], key="cad_foto")

    col_ok, col_bk = st.columns(2)
    with col_ok:
        if st.button("Criar cadastro", type="primary",
                     use_container_width=True, key="btn_criar_cad"):
            if not nome_c.strip():
                st.error("Informe o nome completo.")
                return
            slug_c = _slug(nome_c.strip())
            os.makedirs("dados_clientes", exist_ok=True)
            foto_fn = None
            if foto_c:
                ext = foto_c.name.rsplit(".", 1)[-1].lower()
                foto_fn = f"foto_perfil_{slug_c}.{ext}"
                with open(os.path.join("dados_clientes", foto_fn), "wb") as fout:
                    fout.write(foto_c.getbuffer())
            cad = {
                "nome":           nome_c.strip(),
                "slug":           slug_c,
                "data_nascimento": nasc_c.strftime("%d/%m/%Y") if nasc_c else "",
                "email":          email_c.strip(),
                "whatsapp":       wpp_c.strip(),
                "foto_perfil":    foto_fn,
                "data_cadastro":  date.today().strftime("%d/%m/%Y"),
                "timestamp":      datetime.now().isoformat(),
            }
            _salvar_json(_cadastro_path(slug_c), cad)
            st.session_state['cliente_slug'] = slug_c
            st.session_state.pop('portal_modo', None)
            st.session_state.pop('portal_nome_hint', None)
            st.success("✅ Cadastro criado com sucesso!")
            st.rerun()
    with col_bk:
        if st.button("← Voltar", use_container_width=True, key="btn_cad_voltar"):
            st.session_state.pop('portal_modo', None)
            st.rerun()


def _pagina_portal_cliente():
    if st.button("← Início", key="btn_voltar_portal"):
        st.session_state['area'] = None
        st.session_state.pop('cliente_slug', None)
        st.session_state.pop('portal_modo', None)
        st.session_state.pop('portal_nome_hint', None)
        st.rerun()

    # ── Identificação ─────────────────────────────────────────────────────────
    if not st.session_state.get('cliente_slug'):
        st.title("Portal do Cliente")
        st.markdown('<p class="subtitulo">Studio Personal Training</p>',
                    unsafe_allow_html=True)
        st.divider()

        if st.session_state.get('portal_modo') == 'cadastro':
            _form_cadastro_cliente()
            return

        st.markdown("### Identificação")
        nome_id = st.text_input("Seu nome completo", key="portal_id_nome",
                                 placeholder="Digite exatamente como foi cadastrado")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Acessar meu perfil", type="primary",
                         use_container_width=True, key="btn_portal_acessar"):
                slug_id = _slug(nome_id.strip()) if nome_id.strip() else ""
                if not slug_id:
                    st.error("Digite seu nome.")
                elif os.path.exists(_cadastro_path(slug_id)):
                    st.session_state['cliente_slug'] = slug_id
                    st.rerun()
                else:
                    todos = _todos_cadastros()
                    matches = [
                        c for c in todos
                        if nome_id.strip().lower() in c.get("nome", "").lower()
                        or c.get("nome", "").lower() in nome_id.strip().lower()
                    ]
                    if matches:
                        st.session_state['cliente_slug'] = matches[0]['slug']
                        st.rerun()
                    else:
                        st.warning("Cadastro não encontrado. Você pode se cadastrar abaixo.")
        with col_b:
            if st.button("Fazer cadastro", use_container_width=True,
                         key="btn_portal_cadastrar"):
                st.session_state['portal_modo'] = 'cadastro'
                st.session_state['portal_nome_hint'] = nome_id
                st.rerun()
        return

    # ── Portal autenticado ────────────────────────────────────────────────────
    slug   = st.session_state['cliente_slug']
    cad_c  = _carregar_json(_cadastro_path(slug), {})
    nome_c = cad_c.get("nome", slug)
    meta_p = cad_c.get("meta_peso")

    st.title(f"Olá, {nome_c.split()[0]}!")
    st.markdown('<p class="subtitulo">Studio Personal Training</p>', unsafe_allow_html=True)

    col_sair, _ = st.columns([1, 5])
    with col_sair:
        if st.button("Sair", key="btn_portal_sair"):
            st.session_state.pop('cliente_slug', None)
            st.rerun()

    st.divider()

    pesos = _carregar_json(_peso_path(slug), [])

    tab_peso, tab_prog = st.tabs(["⚖️  Registrar Peso", "📊  Meu Progresso"])

    with tab_peso:
        st.markdown("#### Lançamento de Peso")
        col_p, col_d = st.columns(2)
        with col_p:
            val_inicial = float(pesos[-1]["peso"]) if pesos else 60.0
            novo_peso = st.number_input(
                "Peso atual (kg)", min_value=20.0, max_value=300.0,
                value=val_inicial, step=0.1, format="%.1f", key="portal_peso",
            )
        with col_d:
            data_peso = st.date_input("Data", value=date.today(),
                                      format="DD/MM/YYYY", key="portal_data_peso")

        if st.button("Registrar peso", type="primary",
                     use_container_width=True, key="btn_registrar_peso"):
            entry = {
                "data":      data_peso.strftime("%d/%m/%Y"),
                "peso":      round(float(novo_peso), 1),
                "timestamp": datetime.now().isoformat(),
            }
            pesos.append(entry)
            _salvar_json(_peso_path(slug), pesos)
            frases = [
                "💪 Cada registro é um passo rumo ao seu objetivo!",
                "🌟 Constância é o segredo do sucesso. Continue assim!",
                "🏆 Você está no caminho certo. Não desista!",
                "🎯 Meta em vista! Continue focada.",
                "✨ Pequenos passos levam a grandes conquistas!",
            ]
            st.success("✅ Peso registrado!")
            st.info(random.choice(frases))
            st.rerun()

        if pesos:
            if meta_p:
                st.markdown(f"**Meta definida pela professora:** {meta_p} kg")
            fig = _chart_peso(pesos, meta=meta_p)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                for p in reversed(pesos[-10:]):
                    st.markdown(f"- {p['data']}: **{p['peso']} kg**")

    with tab_prog:
        st.markdown("#### Meu Progresso")
        medidas_c = _carregar_json(_medidas_path(slug), [])

        todos_pesos = []
        for m in medidas_c:
            if m.get("peso"):
                todos_pesos.append({"data": m["data"], "peso": m["peso"]})
        todos_pesos.extend(pesos)
        try:
            todos_pesos.sort(
                key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y"))
        except Exception:
            pass

        if not todos_pesos:
            st.info("Nenhum dado ainda. Registre seu peso na aba ao lado!")
        else:
            p_ini = float(todos_pesos[0]["peso"])
            p_atu = float(todos_pesos[-1]["peso"])
            diff  = p_atu - p_ini
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Peso Inicial", f"{p_ini:.1f} kg")
            with c2:
                st.metric("Peso Atual", f"{p_atu:.1f} kg",
                          delta=f"{'+' if diff>0 else ''}{diff:.1f} kg")
            with c3:
                if meta_p:
                    faltam = p_atu - float(meta_p)
                    st.metric("Meta", f"{float(meta_p):.1f} kg",
                              delta=f"{'+' if faltam>0 else ''}{faltam:.1f} kg")
                else:
                    st.metric("Meta", "—")

            fig_p = _chart_peso(todos_pesos, meta=meta_p)
            if fig_p:
                st.plotly_chart(fig_p, use_container_width=True)

        if len(medidas_c) >= 2:
            st.markdown("**Evolução das Medidas**")
            fig_m = _chart_medidas(medidas_c)
            if fig_m:
                st.plotly_chart(fig_m, use_container_width=True)


# ── Tab: Gerador de Treino ────────────────────────────────────────────────────

def _tab_gerador_treino():
    st.markdown("### Gerador de Treino Personalizado")

    with st.expander("📋 Dados do Cliente", expanded=True):
        nome = st.text_input("Nome completo", placeholder="Ex: Maria Silva", key="gt_nome")

        col_idade, col_sexo = st.columns([1, 2])
        with col_idade:
            idade = st.number_input("Idade", min_value=10, max_value=100,
                                    value=30, step=1, key="gt_idade")
        with col_sexo:
            sexo_label = st.radio("Sexo", ["Feminino", "Masculino"],
                                  horizontal=True, key="gt_sexo")
        sexo = "F" if sexo_label == "Feminino" else "M"

        col_peso, col_altura = st.columns(2)
        with col_peso:
            peso = st.number_input("Peso (kg)", min_value=30.0, max_value=300.0,
                                   value=70.0, step=0.5, format="%.1f", key="gt_peso")
        with col_altura:
            altura = st.number_input("Altura (cm)", min_value=100, max_value=250,
                                     value=170, step=1, key="gt_altura")

        col_data, col_periodo = st.columns(2)
        with col_data:
            data_inicio = st.date_input("Data de início", value=date.today(),
                                        format="DD/MM/YYYY", key="gt_data")
        with col_periodo:
            periodo = st.selectbox("Período do plano (semanas)",
                                   [4, 6, 8, 10, 12, 16], index=2, key="gt_periodo")

        restricoes = st.text_area("Restrições / Lesões",
                                  placeholder="Descreva lesões ou limitações (deixe em branco se não houver)",
                                  height=80, key="gt_restricoes")

    with st.expander("⚙️ Configuração do Treino", expanded=True):
        col_obj, col_nivel = st.columns(2)
        with col_obj:
            objetivo_label = st.selectbox("Objetivo", list(OBJETIVOS.keys()), key="gt_objetivo")
        with col_nivel:
            nivel_label = st.selectbox("Nível", list(NIVEIS.keys()), key="gt_nivel")

        col_freq, col_tempo = st.columns(2)
        with col_freq:
            frequencia = st.selectbox("Frequência semanal", [2, 3, 4, 5, 6], index=2,
                                      key="gt_freq", format_func=lambda x: f"{x}x por semana")
        with col_tempo:
            tempo = st.selectbox("Tempo por sessão", [30, 45, 60, 75, 90], index=2,
                                 key="gt_tempo", format_func=lambda x: f"{x} minutos")

        equipamentos_sel = st.multiselect("Equipamentos disponíveis", EQUIPAMENTOS_OPCOES,
                                          default=["Academia completa"], key="gt_equip")
        equip_outro = ""
        if "Outro" in equipamentos_sel:
            equip_outro = st.text_input("Descreva o(s) equipamento(s) adicional(is):",
                                        placeholder="Ex: Kettlebell, TRX", key="gt_equip_outro")

        divisoes_map  = DIVISOES_F if sexo == "F" else DIVISOES_M
        divisao_label = st.selectbox("Divisão de treino", list(divisoes_map.keys()), key="gt_divisao")
        period_label  = st.selectbox("Periodização", list(PERIODIZACOES.keys()), key="gt_period")

    st.divider()

    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        gerar_clicado = st.button("🏋️  Gerar Treino em PDF", use_container_width=True,
                                  type="primary", key="btn_gerar_treino")

    if gerar_clicado:
        erros = []
        if not nome.strip():
            erros.append("Informe o nome completo do cliente.")
        if not equipamentos_sel:
            erros.append("Selecione pelo menos um equipamento.")
        if "Outro" in equipamentos_sel and not equip_outro.strip():
            erros.append("Descreva o equipamento personalizado selecionado.")
        if erros:
            for e in erros:
                st.error(e)
            return

        equip_str = ", ".join(
            equip_outro.strip() if item == "Outro" else item
            for item in equipamentos_sel
        )
        objetivo      = OBJETIVOS[objetivo_label]
        nivel         = NIVEIS[nivel_label]
        divisao       = divisoes_map[divisao_label]
        period_key    = PERIODIZACOES[period_label]

        dados = {
            'nome':         nome.strip(),
            'idade':        int(idade),
            'sexo':         sexo,
            'peso':         float(peso),
            'altura':       int(altura),
            'objetivo':     objetivo,
            'nivel':        nivel,
            'divisao':      divisao,
            'periodizacao': period_key,
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
        periodizacao = PERIODIZACAO[period_key]
        observacoes = OBSERVACOES[objetivo]

        data_hoje    = datetime.now().strftime("%Y-%m-%d")
        nome_arquivo = f"{_slug(nome.strip())}_{data_hoje}.pdf"

        with st.spinner("Gerando seu treino..."):
            try:
                tmp_path = os.path.join(tempfile.gettempdir(), nome_arquivo)
                gerar_pdf(dados, treinos, descricoes,
                          cardio, progressao, periodizacao, observacoes, tmp_path)
                with open(tmp_path, "rb") as f:
                    pdf_bytes = f.read()
                os.unlink(tmp_path)
            except Exception as exc:
                st.error(f"Erro ao gerar o PDF: {exc}")
                return

        st.success("Treino gerado com sucesso!")
        col_dl_l, col_dl, col_dl_r = st.columns([1, 2, 1])
        with col_dl:
            st.download_button(
                label="📥  Baixar PDF",
                data=pdf_bytes,
                file_name=nome_arquivo,
                mime="application/pdf",
                use_container_width=True,
                key="btn_dl_treino",
            )


# ── Tab: Anamneses Recebidas ──────────────────────────────────────────────────

def _tab_anamneses_recebidas():
    st.markdown("### Anamneses Recebidas")
    os.makedirs("dados_clientes", exist_ok=True)
    arquivos = sorted(glob.glob("dados_clientes/anamnese_*.json"), reverse=True)

    if not arquivos:
        st.info("Nenhuma anamnese recebida ainda. As fichas aparecerão aqui assim que os alunos as enviarem.")
        return

    clientes = []
    for arq in arquivos:
        try:
            with open(arq, encoding="utf-8") as f:
                dados = json.load(f)
            clientes.append({
                "arquivo":    arq,
                "dados":      dados,
                "nome":       dados.get("dados_pessoais", {}).get("nome", arq),
                "data_envio": dados.get("data_envio", "—"),
            })
        except Exception:
            continue

    if not clientes:
        st.warning("Nenhum arquivo de anamnese pôde ser lido.")
        return

    opcoes = [f"{c['nome']}  —  {c['data_envio']}" for c in clientes]
    idx = st.selectbox("Selecionar anamnese", range(len(opcoes)),
                       format_func=lambda i: opcoes[i], key="sel_anamnese")

    st.divider()

    cliente_sel = clientes[idx]
    dados_sel   = cliente_sel["dados"]

    col_info, col_pdf = st.columns([3, 1])
    with col_info:
        st.markdown(f"**{cliente_sel['nome']}** — enviada em {cliente_sel['data_envio']}")
    with col_pdf:
        try:
            pdf_bytes = gerar_pdf_anamnese(dados_sel)
            st.download_button(
                "📄  Exportar PDF",
                data=pdf_bytes,
                file_name=f"anamnese_{_slug(cliente_sel['nome'])}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"btn_pdf_{idx}",
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    _exibir_anamnese_streamlit(dados_sel)


# ── Tab: Avaliação Postural (professora) ─────────────────────────────────────

def _tab_avaliacao_postural():
    st.markdown("### Avaliação Postural")
    os.makedirs("dados_clientes", exist_ok=True)

    pastas = sorted(
        [p for p in glob.glob("dados_clientes/fotos_*") if os.path.isdir(p)],
        reverse=True,
    )

    if not pastas:
        st.info("Nenhuma pasta de fotos recebida ainda.")
        return

    clientes_post = []
    for pasta in pastas:
        meta_path = os.path.join(pasta, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}
        clientes_post.append({
            "pasta": pasta,
            "nome":  meta.get("nome", os.path.basename(pasta)),
            "data":  meta.get("data_avaliacao", "—"),
            "meta":  meta,
        })

    opcoes = [f"{c['nome']}  —  {c['data']}" for c in clientes_post]
    idx = st.selectbox("Selecionar cliente", range(len(opcoes)),
                       format_func=lambda i: opcoes[i], key="sel_postural")

    cliente_sel  = clientes_post[idx]
    pasta_sel    = cliente_sel["pasta"]
    nome_cliente = cliente_sel["nome"]
    pasta_base   = os.path.basename(pasta_sel)

    slug_c = _slug(nome_cliente)
    avals_existentes = sorted(
        glob.glob(f"dados_clientes/avaliacao_{slug_c}_*.json"), reverse=True
    )
    prev = {}
    if avals_existentes:
        try:
            with open(avals_existentes[0], encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:
            prev = {}

    st.divider()
    tab_fotos, tab_kendall = st.tabs(["📸  Fotos", "📋  Ficha de Kendall"])

    obs_fotos = {}

    with tab_fotos:
        foto_subtabs = st.tabs([v['label'] for v in VISTAS_POSTURAL])
        for ftab, vista in zip(foto_subtabs, VISTAS_POSTURAL):
            with ftab:
                vkey      = vista['key']
                foto_orig = _encontrar_foto(pasta_sel, vkey)

                if foto_orig and os.path.exists(foto_orig):
                    st.image(foto_orig, caption=vista['label'], use_container_width=True)
                    with open(foto_orig, "rb") as _f:
                        st.download_button(
                            "⬇️  Baixar foto original",
                            data=_f.read(),
                            file_name=os.path.basename(foto_orig),
                            mime="image/jpeg",
                            key=f"dl_foto_{vkey}_{pasta_base}",
                        )
                else:
                    st.info(f"Foto '{vista['label']}' não foi enviada pelo cliente.")

                obs_default = prev.get("observacoes_fotos", {}).get(vkey, "")
                obs_fotos[vkey] = st.text_area(
                    "Observações sobre esta vista",
                    value=obs_default,
                    height=70,
                    key=f"obs_{vkey}_{pasta_base}",
                )

    vista_ant    = {}
    vista_post_k = {}
    vista_lat    = {}
    aval_func    = {}
    conclusao    = {}

    with tab_kendall:
        st.markdown("#### Vista Anterior (Frente)")
        pva = prev.get("vista_anterior", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            va_cab = st.selectbox("Alinhamento da cabeça",
                ["Centralizada", "Desvio para direita", "Desvio para esquerda"],
                index=_idx_default(["Centralizada","Desvio para direita","Desvio para esquerda"],
                                   pva.get("alinhamento_cabeca","Centralizada")),
                key=f"va_cab_{pasta_base}")
            va_omb = st.selectbox("Ombros",
                ["Nivelados", "Ombro direito elevado", "Ombro esquerdo elevado"],
                index=_idx_default(["Nivelados","Ombro direito elevado","Ombro esquerdo elevado"],
                                   pva.get("ombros","Nivelados")),
                key=f"va_omb_{pasta_base}")
        with c2:
            va_tal = st.selectbox("Triângulo de Tales",
                ["Simétrico", "Assimétrico direita", "Assimétrico esquerda"],
                index=_idx_default(["Simétrico","Assimétrico direita","Assimétrico esquerda"],
                                   pva.get("triangulo_tales","Simétrico")),
                key=f"va_tal_{pasta_base}")
            va_cri = st.selectbox("Cristas ilíacas",
                ["Niveladas", "Direita elevada", "Esquerda elevada"],
                index=_idx_default(["Niveladas","Direita elevada","Esquerda elevada"],
                                   pva.get("cristas_iliacas","Niveladas")),
                key=f"va_cri_{pasta_base}")
        with c3:
            va_joe = st.selectbox("Joelhos",
                ["Neutro","Valgo bilateral","Varo bilateral","Valgo D / Varo E","Varo D / Valgo E"],
                index=_idx_default(["Neutro","Valgo bilateral","Varo bilateral","Valgo D / Varo E","Varo D / Valgo E"],
                                   pva.get("joelhos","Neutro")),
                key=f"va_joe_{pasta_base}")
            va_pes = st.selectbox("Pés",
                ["Neutro","Pronado bilateral","Supinado bilateral","Misto"],
                index=_idx_default(["Neutro","Pronado bilateral","Supinado bilateral","Misto"],
                                   pva.get("pes","Neutro")),
                key=f"va_pes_{pasta_base}")
        va_obs = st.text_area("Observações (Vista Anterior)", value=pva.get("obs",""),
                              height=70, key=f"va_obs_{pasta_base}")
        vista_ant = {
            "alinhamento_cabeca": va_cab, "ombros": va_omb, "triangulo_tales": va_tal,
            "cristas_iliacas": va_cri, "joelhos": va_joe, "pes": va_pes, "obs": va_obs,
        }

        st.divider()
        st.markdown("#### Vista Posterior (Costas)")
        pvp = prev.get("vista_posterior", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            vp_col = st.selectbox("Alinhamento da coluna",
                ["Retilínea","Escoliose funcional","Escoliose estrutural","Desvio direita","Desvio esquerda"],
                index=_idx_default(["Retilínea","Escoliose funcional","Escoliose estrutural","Desvio direita","Desvio esquerda"],
                                   pvp.get("coluna","Retilínea")),
                key=f"vp_col_{pasta_base}")
            vp_esc = st.selectbox("Escápulas",
                ["Simétricas","Alada direita","Alada esquerda","Elevada direita","Elevada esquerda"],
                index=_idx_default(["Simétricas","Alada direita","Alada esquerda","Elevada direita","Elevada esquerda"],
                                   pvp.get("escapulas","Simétricas")),
                key=f"vp_esc_{pasta_base}")
        with c2:
            vp_glu = st.selectbox("Glúteos",
                ["Simétricos","Assimétricos"],
                index=_idx_default(["Simétricos","Assimétricos"], pvp.get("gluteos","Simétricos")),
                key=f"vp_glu_{pasta_base}")
            vp_pop = st.selectbox("Dobras poplíteas",
                ["Simétricas","Assimétricas"],
                index=_idx_default(["Simétricas","Assimétricas"], pvp.get("dobras_popliteas","Simétricas")),
                key=f"vp_pop_{pasta_base}")
        with c3:
            vp_cal = st.selectbox("Calcanhares",
                ["Neutro","Valgo bilateral","Varo bilateral","Valgo D / Varo E","Varo D / Valgo E"],
                index=_idx_default(["Neutro","Valgo bilateral","Varo bilateral","Valgo D / Varo E","Varo D / Valgo E"],
                                   pvp.get("calcanhares","Neutro")),
                key=f"vp_cal_{pasta_base}")
        vp_obs = st.text_area("Observações (Vista Posterior)", value=pvp.get("obs",""),
                              height=70, key=f"vp_obs_{pasta_base}")
        vista_post_k = {
            "coluna": vp_col, "escapulas": vp_esc, "gluteos": vp_glu,
            "dobras_popliteas": vp_pop, "calcanhares": vp_cal, "obs": vp_obs,
        }

        st.divider()
        st.markdown("#### Vista Lateral")
        pvl = prev.get("vista_lateral", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            vl_cab = st.selectbox("Posição da cabeça",
                ["Neutra","Anteriorizada","Posteriorizada"],
                index=_idx_default(["Neutra","Anteriorizada","Posteriorizada"],
                                   pvl.get("cabeca","Neutra")),
                key=f"vl_cab_{pasta_base}")
            vl_cer = st.selectbox("Coluna cervical",
                ["Normal","Hiperlordose","Retificada"],
                index=_idx_default(["Normal","Hiperlordose","Retificada"],
                                   pvl.get("cervical","Normal")),
                key=f"vl_cer_{pasta_base}")
            vl_tor = st.selectbox("Coluna torácica",
                ["Normal","Hipercifose","Retificada"],
                index=_idx_default(["Normal","Hipercifose","Retificada"],
                                   pvl.get("toracica","Normal")),
                key=f"vl_tor_{pasta_base}")
        with c2:
            vl_lom = st.selectbox("Coluna lombar",
                ["Normal","Hiperlordose","Retificada","Escoliose"],
                index=_idx_default(["Normal","Hiperlordose","Retificada","Escoliose"],
                                   pvl.get("lombar","Normal")),
                key=f"vl_lom_{pasta_base}")
            vl_pel = st.selectbox("Pelve",
                ["Neutra","Anteversão","Retroversão"],
                index=_idx_default(["Neutra","Anteversão","Retroversão"],
                                   pvl.get("pelve","Neutra")),
                key=f"vl_pel_{pasta_base}")
        with c3:
            vl_joe = st.selectbox("Joelho (lateral)",
                ["Neutro","Hiperextensão","Semiflexão"],
                index=_idx_default(["Neutro","Hiperextensão","Semiflexão"],
                                   pvl.get("joelho_lat","Neutro")),
                key=f"vl_joe_{pasta_base}")
        vl_obs = st.text_area("Observações (Vista Lateral)", value=pvl.get("obs",""),
                              height=70, key=f"vl_obs_{pasta_base}")
        vista_lat = {
            "cabeca": vl_cab, "cervical": vl_cer, "toracica": vl_tor,
            "lombar": vl_lom, "pelve": vl_pel, "joelho_lat": vl_joe, "obs": vl_obs,
        }

        st.divider()
        st.markdown("#### Avaliação Funcional")
        paf = prev.get("avaliacao_funcional", {})
        af_aga  = st.text_area("Agachamento — observações", value=paf.get("agachamento",""),
                               height=70, key=f"af_aga_{pasta_base}")
        af_core = st.text_area("Core / Prancha — observações", value=paf.get("core",""),
                               height=70, key=f"af_core_{pasta_base}")
        aval_func = {"agachamento": af_aga, "core": af_core}

        st.divider()
        st.markdown("#### Conclusão e Recomendações")
        pconc = prev.get("conclusao", {})
        c1, c2 = st.columns(2)
        with c1:
            conc_alt = st.text_area("Principais alterações encontradas",
                                    value=pconc.get("principais_alteracoes",""),
                                    height=90, key=f"conc_alt_{pasta_base}")
            conc_enc = st.text_area("Músculos encurtados identificados",
                                    value=pconc.get("musculos_encurtados",""),
                                    height=90, key=f"conc_enc_{pasta_base}")
            conc_fra = st.text_area("Músculos alongados/fracos identificados",
                                    value=pconc.get("musculos_fracos",""),
                                    height=90, key=f"conc_fra_{pasta_base}")
        with c2:
            conc_exe = st.text_area("Exercícios corretivos recomendados",
                                    value=pconc.get("exercicios_corretivos",""),
                                    height=90, key=f"conc_exe_{pasta_base}")
            conc_obs = st.text_area("Observações gerais",
                                    value=pconc.get("obs_gerais",""),
                                    height=90, key=f"conc_obs_{pasta_base}")

        prox_default = None
        if pconc.get("proxima_reavaliacao"):
            try:
                prox_default = datetime.strptime(
                    pconc["proxima_reavaliacao"], "%d/%m/%Y").date()
            except Exception:
                pass
        prox_aval = st.date_input("Próxima reavaliação recomendada", value=prox_default,
                                  format="DD/MM/YYYY", key=f"conc_prox_{pasta_base}")
        conclusao = {
            "principais_alteracoes": conc_alt,
            "musculos_encurtados":   conc_enc,
            "musculos_fracos":       conc_fra,
            "exercicios_corretivos": conc_exe,
            "obs_gerais":            conc_obs,
            "proxima_reavaliacao":   prox_aval.strftime("%d/%m/%Y") if prox_aval else "",
        }

    # ── Botões de ação ────────────────────────────────────────────────────────
    st.divider()
    col_sal, col_pdf = st.columns(2)

    def _montar_dados_aval():
        fotos_info = {}
        for v in VISTAS_POSTURAL:
            ep = os.path.join(pasta_sel, f"editada_{v['key']}.png")
            fotos_info[v['key']] = {
                "original": _encontrar_foto(pasta_sel, v['key']),
                "editada":  ep if os.path.exists(ep) else None,
            }
        return {
            "cliente":             nome_cliente,
            "data_avaliacao":      cliente_sel["data"],
            "pasta_fotos":         pasta_sel,
            "fotos":               fotos_info,
            "observacoes_fotos":   obs_fotos,
            "vista_anterior":      vista_ant,
            "vista_posterior":     vista_post_k,
            "vista_lateral":       vista_lat,
            "avaliacao_funcional": aval_func,
            "conclusao":           conclusao,
            "data_geracao":        datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    with col_sal:
        if st.button("💾  Salvar Avaliação", use_container_width=True,
                     type="primary", key=f"btn_salvar_{pasta_base}"):
            dados_aval = _montar_dados_aval()
            ts_aval    = datetime.now().strftime("%Y-%m-%d")
            arq_aval   = f"dados_clientes/avaliacao_{slug_c}_{ts_aval}.json"
            with open(arq_aval, "w", encoding="utf-8") as f:
                json.dump(dados_aval, f, ensure_ascii=False, indent=2)
            st.success("✅ Avaliação salva com sucesso!")

    with col_pdf:
        if st.button("📄  Gerar PDF da Avaliação", use_container_width=True,
                     key=f"btn_pdf_{pasta_base}"):
            dados_aval = _montar_dados_aval()
            try:
                with st.spinner("Gerando PDF..."):
                    pdf_bytes = gerar_pdf_postural(dados_aval)
                st.download_button(
                    "📥  Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"avaliacao_postural_{slug_c}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_pdf_{pasta_base}",
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")


# ── Tab: Clientes (professora) ────────────────────────────────────────────────

def _perfil_cliente_prof(slug):
    cad      = _carregar_json(_cadastro_path(slug), {})
    nome_c   = cad.get("nome", slug)
    medidas  = _carregar_json(_medidas_path(slug), [])
    pesos_c  = _carregar_json(_peso_path(slug), [])

    col_bk, col_ti = st.columns([1, 5])
    with col_bk:
        if st.button("← Lista", key="btn_volta_lista"):
            st.session_state.pop('clientes_perfil_slug', None)
            st.rerun()
    with col_ti:
        st.markdown(f"#### {nome_c}")

    tab_dados, tab_med, tab_prog = st.tabs([
        "👤  Dados Pessoais",
        "📏  Medidas e Evolução",
        "📈  Progresso",
    ])

    # ── Aba: Dados Pessoais ───────────────────────────────────────────────────
    with tab_dados:
        col_foto, col_info = st.columns([1, 3])
        with col_foto:
            fn = cad.get("foto_perfil")
            if fn:
                fp = os.path.join("dados_clientes", fn)
                if os.path.exists(fp):
                    st.image(fp, width=120)
                else:
                    st.markdown("👤")
            else:
                st.markdown("👤")
        with col_info:
            st.markdown(f"**Nome:** {cad.get('nome','')}")
            st.markdown(f"**Nascimento:** {cad.get('data_nascimento','—')}")
            st.markdown(f"**WhatsApp:** {cad.get('whatsapp','—')}")
            st.markdown(f"**E-mail:** {cad.get('email','—')}")
            st.markdown(f"**Cadastrado em:** {cad.get('data_cadastro','—')}")

        st.divider()
        st.markdown("**Registros vinculados**")
        slug_c = cad.get("slug", slug)

        anam = sorted(glob.glob(f"dados_clientes/anamnese_{slug_c}_*.json"), reverse=True)
        if anam:
            st.markdown(f"📋 Anamnese: `{os.path.basename(anam[0])}`")
        else:
            st.markdown("📋 Anamnese: _nenhuma_")

        fotos_dir = sorted(
            [p for p in glob.glob(f"dados_clientes/fotos_{slug_c}_*") if os.path.isdir(p)],
            reverse=True,
        )
        if fotos_dir:
            st.markdown(f"📸 Avaliação Postural: `{os.path.basename(fotos_dir[0])}`")
        else:
            st.markdown("📸 Avaliação Postural: _nenhuma_")

        treinos = sorted(glob.glob(f"{slug_c}_*.pdf"), reverse=True)
        if treinos:
            st.markdown(f"🏋️ Último treino: `{os.path.basename(treinos[0])}`")
        else:
            st.markdown("🏋️ Treino gerado: _nenhum_")

        st.divider()
        with st.expander("✏️ Editar dados"):
            with st.form(key=f"edit_cad_{slug}"):
                e_nome = st.text_input("Nome", value=cad.get("nome",""), key=f"e_nome_{slug}")
                e_nasc = st.text_input("Data de nascimento (DD/MM/AAAA)",
                                       value=cad.get("data_nascimento",""), key=f"e_nasc_{slug}")
                e_wpp  = st.text_input("WhatsApp", value=cad.get("whatsapp",""), key=f"e_wpp_{slug}")
                e_mail = st.text_input("E-mail", value=cad.get("email",""), key=f"e_mail_{slug}")
                if st.form_submit_button("Salvar alterações", type="primary"):
                    cad.update({"nome": e_nome.strip(), "data_nascimento": e_nasc.strip(),
                                "whatsapp": e_wpp.strip(), "email": e_mail.strip()})
                    _salvar_json(_cadastro_path(slug), cad)
                    st.success("✅ Dados atualizados!")
                    st.rerun()

    # ── Aba: Medidas e Evolução ───────────────────────────────────────────────
    with tab_med:
        # Meta de peso
        meta_atual = cad.get("meta_peso")
        st.markdown("#### Meta de Peso")
        col_m, col_ms = st.columns([3, 1])
        with col_m:
            nova_meta = st.number_input(
                "Meta de peso (kg) — 0 = sem meta", min_value=0.0, max_value=300.0,
                value=float(meta_atual) if meta_atual else 0.0,
                step=0.5, format="%.1f", key=f"meta_{slug}",
            )
        with col_ms:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Salvar meta", key=f"btn_meta_{slug}", use_container_width=True):
                cad["meta_peso"] = float(nova_meta) if nova_meta > 0 else None
                _salvar_json(_cadastro_path(slug), cad)
                st.success("Meta atualizada!")
                st.rerun()

        st.divider()
        st.markdown("#### Lançar Medidas")
        with st.form(key=f"form_med_{slug}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                data_med = st.date_input("Data", value=date.today(),
                                          format="DD/MM/YYYY", key=f"md_dt_{slug}")
                peso_med = st.number_input("Peso (kg) — 0 = não inf.",
                                            min_value=0.0, max_value=300.0,
                                            value=0.0, step=0.1, format="%.1f",
                                            key=f"md_p_{slug}")
                circ_abd = st.number_input("Circ. Abdominal (cm)",
                                            min_value=0.0, value=0.0,
                                            step=0.1, format="%.1f", key=f"md_ca_{slug}")
            with c2:
                cintura = st.number_input("Cintura (cm)", min_value=0.0, value=0.0,
                                           step=0.1, format="%.1f", key=f"md_ci_{slug}")
                quadril = st.number_input("Quadril (cm)", min_value=0.0, value=0.0,
                                           step=0.1, format="%.1f", key=f"md_q_{slug}")
                coxa_d  = st.number_input("Coxa Direita (cm)", min_value=0.0, value=0.0,
                                           step=0.1, format="%.1f", key=f"md_co_{slug}")
            with c3:
                braco_d  = st.number_input("Braço Direito (cm)", min_value=0.0, value=0.0,
                                            step=0.1, format="%.1f", key=f"md_br_{slug}")
                perc_g   = st.number_input("% Gordura", min_value=0.0, max_value=100.0,
                                            value=0.0, step=0.1, format="%.1f",
                                            key=f"md_pg_{slug}")
                obs_med  = st.text_area("Observações", height=70, key=f"md_ob_{slug}")
            submitted = st.form_submit_button(
                "Registrar medidas", type="primary", use_container_width=True)

        if submitted:
            entry = {
                "data":      data_med.strftime("%d/%m/%Y"),
                "peso":      float(peso_med) if peso_med > 0 else None,
                "circ_abd":  float(circ_abd) if circ_abd > 0 else None,
                "cintura":   float(cintura)  if cintura  > 0 else None,
                "quadril":   float(quadril)  if quadril  > 0 else None,
                "coxa_d":    float(coxa_d)   if coxa_d   > 0 else None,
                "braco_d":   float(braco_d)  if braco_d  > 0 else None,
                "perc_gord": float(perc_g)   if perc_g   > 0 else None,
                "obs":       obs_med.strip(),
                "timestamp": datetime.now().isoformat(),
            }
            medidas.append(entry)
            _salvar_json(_medidas_path(slug), medidas)
            st.success("✅ Medidas registradas!")
            st.rerun()

        if medidas:
            st.divider()
            st.markdown("#### Histórico de Medidas")
            CAMPOS_TAB = [
                ("data","Data"), ("peso","Peso"), ("circ_abd","Circ.Abd"),
                ("cintura","Cintura"), ("quadril","Quadril"),
                ("coxa_d","Coxa D."), ("braco_d","Braço D."), ("perc_gord","% Gord."),
            ]
            rows_tab = []
            for m in reversed(medidas):
                row = {}
                for k, l in CAMPOS_TAB:
                    v = m.get(k)
                    row[l] = f"{float(v):.1f}" if v not in (None, "") else "—"
                    if k == "data":
                        row[l] = str(v) if v else "—"
                rows_tab.append(row)
            st.dataframe(rows_tab, use_container_width=True)

            st.markdown("#### Gráficos")
            med_peso = [m for m in medidas if m.get("peso")]
            if med_peso:
                fig_p = _chart_peso(med_peso,
                                    meta=float(nova_meta) if nova_meta > 0 else None)
                if fig_p:
                    st.plotly_chart(fig_p, use_container_width=True)
            if len(medidas) >= 2:
                fig_m = _chart_medidas(medidas)
                if fig_m:
                    st.plotly_chart(fig_m, use_container_width=True)

    # ── Aba: Progresso ────────────────────────────────────────────────────────
    with tab_prog:
        todos_pesos = []
        for m in medidas:
            if m.get("peso"):
                todos_pesos.append({"data": m["data"], "peso": m["peso"]})
        todos_pesos.extend(pesos_c)
        try:
            todos_pesos.sort(
                key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y"))
        except Exception:
            pass

        meta_p = cad.get("meta_peso")

        if not todos_pesos:
            st.info("Nenhum dado de evolução registrado ainda.")
        else:
            p_ini = float(todos_pesos[0]["peso"])
            p_atu = float(todos_pesos[-1]["peso"])
            diff  = p_atu - p_ini
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Peso Inicial", f"{p_ini:.1f} kg")
            with c2:
                st.metric("Peso Atual", f"{p_atu:.1f} kg",
                          delta=f"{'+' if diff>0 else ''}{diff:.1f} kg")
            with c3:
                if meta_p:
                    faltam = p_atu - float(meta_p)
                    st.metric("Meta", f"{float(meta_p):.1f} kg",
                              delta=f"{'+' if faltam>0 else ''}{faltam:.1f} kg")
                else:
                    st.metric("Meta", "Não definida")

        if len(medidas) >= 2:
            st.markdown("#### Comparativo: Primeira vs Última Avaliação")
            primeira = medidas[0]
            ultima   = medidas[-1]
            CAMPOS_COMP = [
                ("peso","Peso (kg)"), ("circ_abd","Circ. Abd. (cm)"),
                ("cintura","Cintura (cm)"), ("quadril","Quadril (cm)"),
                ("coxa_d","Coxa D. (cm)"), ("braco_d","Braço D. (cm)"),
                ("perc_gord","% Gordura"),
            ]
            rows_comp = []
            for key, label in CAMPOS_COMP:
                vi = primeira.get(key)
                va = ultima.get(key)
                if vi or va:
                    vi_s = f"{float(vi):.1f}" if vi else "—"
                    va_s = f"{float(va):.1f}" if va else "—"
                    diff_s = "—"
                    if vi and va:
                        d = float(va) - float(vi)
                        diff_s = f"{'+' if d>0 else ''}{d:.1f}"
                    rows_comp.append({
                        "Medida":  label,
                        f"Inicial ({primeira.get('data','')})": vi_s,
                        f"Atual ({ultima.get('data','')})":     va_s,
                        "Variação": diff_s,
                    })
            if rows_comp:
                st.dataframe(rows_comp, use_container_width=True)

        if todos_pesos:
            fig_p = _chart_peso(todos_pesos, meta=meta_p)
            if fig_p:
                st.plotly_chart(fig_p, use_container_width=True)

        if len(medidas) >= 2:
            fig_m = _chart_medidas(medidas)
            if fig_m:
                st.plotly_chart(fig_m, use_container_width=True)

        st.divider()
        if st.button("📄  Gerar PDF de Progresso", key=f"btn_pdf_prog_{slug}",
                     use_container_width=True):
            data_ini_str = (medidas[0]["data"] if medidas
                            else (pesos_c[0]["data"] if pesos_c else "—"))
            dados_pdf = {
                "cliente":    nome_c,
                "data_inicio": data_ini_str,
                "data_fim":    datetime.now().strftime("%d/%m/%Y"),
                "medidas":    medidas,
                "todos_pesos": todos_pesos,
                "meta_peso":  meta_p,
                "obs_gerais": "",
            }
            try:
                with st.spinner("Gerando PDF..."):
                    pdf_b = gerar_pdf_progresso(dados_pdf)
                st.download_button(
                    "📥  Baixar PDF de Progresso",
                    data=pdf_b,
                    file_name=f"progresso_{slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_pdf_prog_{slug}",
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")


def _tab_clientes():
    st.markdown("### Gestão de Clientes")

    if st.session_state.get('clientes_perfil_slug'):
        _perfil_cliente_prof(st.session_state['clientes_perfil_slug'])
        return

    todos = _todos_cadastros()
    if not todos:
        st.info("Nenhum cliente cadastrado ainda. Os clientes aparecem aqui após se cadastrarem no Portal do Cliente.")
        return

    for cad in todos:
        slug_c = cad.get("slug", _slug(cad.get("nome", "")))
        col_foto, col_info, col_btn = st.columns([1, 5, 2])

        with col_foto:
            fn = cad.get("foto_perfil")
            if fn:
                fp = os.path.join("dados_clientes", fn)
                if os.path.exists(fp):
                    st.image(fp, width=60)
                    fn = None
            if fn is None and not cad.get("foto_perfil"):
                st.markdown('<div style="font-size:2rem;text-align:center">👤</div>',
                            unsafe_allow_html=True)

        with col_info:
            medidas_c = _carregar_json(_medidas_path(slug_c), [])
            pesos_c   = _carregar_json(_peso_path(slug_c), [])
            ultimo_peso = "—"
            if medidas_c and medidas_c[-1].get("peso"):
                ultimo_peso = f"{medidas_c[-1]['peso']} kg"
            elif pesos_c:
                ultimo_peso = f"{pesos_c[-1]['peso']} kg"
            st.markdown(f"**{cad.get('nome', '')}**")
            st.caption(
                f"Cadastro: {cad.get('data_cadastro','—')}  |  "
                f"Último peso: {ultimo_peso}"
            )

        with col_btn:
            if st.button("Ver perfil", key=f"btn_perfil_{slug_c}",
                         use_container_width=True):
                st.session_state['clientes_perfil_slug'] = slug_c
                st.rerun()

        st.divider()


# ── Página: Professora ────────────────────────────────────────────────────────

def _pagina_professora():
    # Tela de login
    if not st.session_state.get('autenticado'):
        st.title("Studio Personal Training")
        st.markdown("### Acesso Restrito — Área da Professora")
        st.divider()

        col_l, col_form, col_r = st.columns([1, 2, 1])
        with col_form:
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha   = st.text_input("Senha", type="password")
                entrar  = st.form_submit_button("Entrar", use_container_width=True)

            if entrar:
                if usuario == "admin" and senha == "studio2026":
                    st.session_state['autenticado'] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("← Voltar ao início", key="btn_voltar_login",
                         use_container_width=True):
                st.session_state['area'] = None
                st.rerun()
        return

    # Cabeçalho da área autenticada
    col_titulo, col_sair = st.columns([9, 1])
    with col_titulo:
        st.title("Studio Personal Training")
        st.markdown('<p class="subtitulo">Área da Professora</p>', unsafe_allow_html=True)
    with col_sair:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Sair", key="btn_sair"):
            st.session_state['autenticado'] = False
            st.session_state['area']        = None
            st.rerun()

    st.divider()

    tab_treino, tab_anamneses, tab_postural, tab_cli = st.tabs([
        "🏋️  Gerador de Treino",
        "📋  Anamneses Recebidas",
        "📸  Avaliação Postural",
        "👥  Clientes",
    ])

    with tab_treino:
        _tab_gerador_treino()

    with tab_anamneses:
        _tab_anamneses_recebidas()

    with tab_postural:
        _tab_avaliacao_postural()

    with tab_cli:
        _tab_clientes()


# ── Roteamento principal ──────────────────────────────────────────────────────

if 'area' not in st.session_state:
    st.session_state['area'] = None
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

_area = st.session_state['area']
if _area is None:
    _pagina_home()
elif _area == 'cliente':
    _pagina_anamnese()
elif _area == 'postural':
    _pagina_upload_postural()
elif _area == 'portal_cliente':
    _pagina_portal_cliente()
else:
    _pagina_professora()
