import io
from datetime import datetime

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)


# ── Fontes ────────────────────────────────────────────────────────────────────

def _registrar_fontes():
    try:
        pdfmetrics.registerFont(TTFont('ArialPT',      'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('ArialPT-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        return 'ArialPT', 'ArialPT-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'

FONTE_N, FONTE_B = _registrar_fontes()

# ── Paleta ────────────────────────────────────────────────────────────────────

PRETO       = HexColor('#1A1A1A')
CINZA_MEIO  = HexColor('#666666')
CINZA_PAR   = HexColor('#FAFAFA')
CINZA_IMPAR = HexColor('#FFFFFF')
CINZA_SEP   = HexColor('#E8E8E8')
CINZA_ROD   = HexColor('#666666')
CINZA_SUB   = HexColor('#888888')
CINZA_TH    = HexColor('#1A1A1A')
VERMELHO    = HexColor('#C0392B')
AMARELO_AV  = HexColor('#FFF3CD')
TEXTO_AV    = HexColor('#856404')

NOME_CONSULTORIA = "Studio Personal Training"
PAGE_W, PAGE_H   = A4
MARGIN            = 2 * cm
CONTENT_W         = PAGE_W - 2 * MARGIN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _p(texto, estilo):
    return Paragraph(str(texto) if texto else "—", estilo)


def _estilos():
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        'hdr_titulo': ps('AHdrTitulo', fontName=FONTE_B, fontSize=18,
                         textColor=white, alignment=TA_CENTER, leading=24),
        'hdr_nome':   ps('AHdrNome',   fontName=FONTE_B, fontSize=13,
                         textColor=white, alignment=TA_CENTER, spaceBefore=2),
        'hdr_sub':    ps('AHdrSub',    fontName=FONTE_N, fontSize=9,
                         textColor=CINZA_SUB, alignment=TA_CENTER, spaceBefore=2),
        'sec_titulo': ps('ASecTit',    fontName=FONTE_B, fontSize=11,
                         textColor=VERMELHO, spaceBefore=14, spaceAfter=4),
        'lbl':        ps('ALbl',       fontName=FONTE_B, fontSize=8,
                         textColor=CINZA_MEIO, leading=12),
        'val':        ps('AVal',       fontName=FONTE_N, fontSize=8,
                         textColor=PRETO, leading=12),
        'alerta':     ps('AAlerta',    fontName=FONTE_B, fontSize=8,
                         textColor=TEXTO_AV, leading=13),
        'parq_sim':   ps('AParqSim',   fontName=FONTE_B, fontSize=8,
                         textColor=HexColor('#B71C1C'), leading=12),
        'parq_nao':   ps('AParqNao',   fontName=FONTE_N, fontSize=8,
                         textColor=CINZA_MEIO, leading=12),
    }


def _rodape(canvas, doc):
    canvas.saveState()
    y = 1.4 * cm
    canvas.setStrokeColor(CINZA_SEP)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, y, PAGE_W - MARGIN, y)
    canvas.setFont(FONTE_N, 7)
    canvas.setFillColor(CINZA_ROD)
    canvas.drawString(MARGIN, y - 0.35 * cm, NOME_CONSULTORIA)
    canvas.drawCentredString(PAGE_W / 2, y - 0.35 * cm,
                             "Ficha de Anamnese — Documento Confidencial")
    canvas.drawRightString(PAGE_W - MARGIN, y - 0.35 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _titulo_secao(texto, est):
    return [
        _p(texto, est['sec_titulo']),
        HRFlowable(width=CONTENT_W, thickness=0.6, color=CINZA_SEP, spaceAfter=5),
    ]


def _tabela_kv_1col(pares, est):
    """Tabela de key-value com 1 par por linha."""
    rows = [
        [_p(k, est['lbl']), _p(v if v else "—", est['val'])]
        for k, v in pares if k
    ]
    if not rows:
        return Spacer(1, 0.1 * cm)
    cw = [CONTENT_W * 0.25, CONTENT_W * 0.75]
    t = Table(rows, colWidths=cw)
    s = TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ])
    for i in range(len(rows)):
        s.add('BACKGROUND', (0, i), (-1, i), CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
    t.setStyle(s)
    return t


def _tabela_kv_2col(pares, est):
    """Tabela de key-value com 2 pares por linha (4 colunas)."""
    validos = [(k, v if v else "—") for k, v in pares if k]
    rows = []
    for i in range(0, len(validos), 2):
        p1 = validos[i]
        p2 = validos[i + 1] if i + 1 < len(validos) else ("", "")
        rows.append([
            _p(p1[0], est['lbl']), _p(p1[1], est['val']),
            _p(p2[0], est['lbl']), _p(p2[1], est['val']),
        ])
    if not rows:
        return Spacer(1, 0.1 * cm)
    cw = [CONTENT_W * f for f in (0.18, 0.32, 0.18, 0.32)]
    t = Table(rows, colWidths=cw)
    s = TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ])
    for i in range(len(rows)):
        s.add('BACKGROUND', (0, i), (-1, i), CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
    t.setStyle(s)
    return t


# ── Entrada pública ───────────────────────────────────────────────────────────

def gerar_pdf_anamnese(dados: dict) -> bytes:
    """Gera a ficha de anamnese em PDF e retorna os bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.2 * cm, bottomMargin=2.5 * cm,
    )
    est   = _estilos()
    story = []

    nome       = dados.get('dados_pessoais', {}).get('nome', 'Cliente')
    data_envio = dados.get('data_envio', '')

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    hdr = Table([
        [_p("FICHA DE ANAMNESE", est['hdr_titulo'])],
        [_p(nome.upper(),        est['hdr_nome'])],
        [_p(NOME_CONSULTORIA,    est['hdr_sub'])],
        [_p(f"Recebida em: {data_envio}", est['hdr_sub'])],
    ], colWidths=[CONTENT_W])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), PRETO),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, 0),  18),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
        ('TOPPADDING',    (0, 1), (-1, 2),  4),
        ('BOTTOMPADDING', (0, 1), (-1, 2),  4),
        ('TOPPADDING',    (0, 3), (-1, 3),  4),
        ('BOTTOMPADDING', (0, 3), (-1, -1), 18),
        ('LEFTPADDING',   (0, 0), (-1, -1), 18),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 18),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.4 * cm))

    # ── 1. Dados Pessoais ─────────────────────────────────────────────────────
    dp = dados.get('dados_pessoais', {})
    story += _titulo_secao("1. DADOS PESSOAIS", est)
    story.append(_tabela_kv_2col([
        ("Nome",             dp.get('nome', '')),
        ("Data de Nascimento", dp.get('data_nascimento', '')),
        ("Sexo",             dp.get('sexo', '')),
        ("Telefone",         dp.get('telefone', '')),
        ("E-mail",           dp.get('email', '')),
        ("Ocupação",         dp.get('ocupacao', '')),
        ("Cidade / Estado",  dp.get('cidade_estado', '')),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 2. Objetivo ───────────────────────────────────────────────────────────
    obj = dados.get('objetivo', {})
    story += _titulo_secao("2. OBJETIVO", est)
    story.append(_tabela_kv_1col([
        ("Objetivos",          ", ".join(obj.get('objetivos', []))),
        ("Descrição",          obj.get('descricao', '')),
        ("Praticou antes?",    obj.get('praticou_antes', '')),
        ("Atividade anterior", obj.get('atividade_anterior', '') or "—"),
        ("Por que parou?",     obj.get('motivo_parou', '') or "—"),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 3. PAR-Q+ ─────────────────────────────────────────────────────────────
    parq = dados.get('parq', {})
    story += _titulo_secao("3. PAR-Q+ — PRONTIDÃO PARA ATIVIDADE FÍSICA", est)

    questoes = parq.get('questoes', [])
    if questoes:
        pq_rows = []
        for i, q in enumerate(questoes):
            resp   = q.get('resposta', 'Não')
            e_sim  = resp == "Sim"
            est_resp = est['parq_sim'] if e_sim else est['parq_nao']
            bg = HexColor('#FDECEA') if e_sim else (CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
            pq_rows.append([_p(resp, est_resp), _p(q.get('pergunta', ''), est_resp)])
        cw = [CONTENT_W * 0.1, CONTENT_W * 0.9]
        pq_t = Table(pq_rows, colWidths=cw)
        pq_s = TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ])
        for i, q in enumerate(questoes):
            bg = HexColor('#FDECEA') if q.get('resposta') == "Sim" else (CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
            pq_s.add('BACKGROUND', (0, i), (-1, i), bg)
        pq_t.setStyle(pq_s)
        story.append(pq_t)

    if parq.get('alerta_medico'):
        story.append(Spacer(1, 0.2 * cm))
        av_t = Table([[_p(
            "⚠️  ATENÇÃO: Uma ou mais respostas indicam necessidade de avaliação "
            "médica antes do início do programa de treinamento.",
            est['alerta'],
        )]], colWidths=[CONTENT_W])
        av_t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), AMARELO_AV),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ]))
        story.append(av_t)
    story.append(Spacer(1, 0.3 * cm))

    # ── 4. Histórico de Saúde ─────────────────────────────────────────────────
    hs = dados.get('historico_saude', {})
    story += _titulo_secao("4. HISTÓRICO DE SAÚDE", est)
    coluna_str = hs.get('coluna', 'Não')
    if hs.get('coluna_regiao'):
        coluna_str += f" — {hs['coluna_regiao']}"
    story.append(_tabela_kv_2col([
        ("Doenças diagnosticadas",   hs.get('doencas', '') or "Nenhuma"),
        ("Hist. familiar cardíaco",  hs.get('historico_cardiaco', '')),
        ("Medicamentos",             hs.get('medicamentos', '') or "Nenhum"),
        ("Diabetes",                 hs.get('diabetes', '')),
        ("Cirurgias",                hs.get('cirurgia', '') or "Nenhuma"),
        ("Hipertensão",              hs.get('hipertensao', '')),
        ("Problemas na coluna",      coluna_str),
        ("Gravidez",                 hs.get('gravidez', '')),
        ("Lesões / Limitações",      hs.get('lesoes', '') or "Nenhuma"),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 5. Estilo de Vida ─────────────────────────────────────────────────────
    ev = dados.get('estilo_vida', {})
    story += _titulo_secao("5. ESTILO DE VIDA", est)
    story.append(_tabela_kv_2col([
        ("Horas de sono",          ev.get('horas_sono', '')),
        ("Qualidade do sono",      ev.get('qualidade_sono', '')),
        ("Nível de estresse",      ev.get('estresse', '')),
        ("Álcool",                 ev.get('alcool', '')),
        ("Tabagismo",              ev.get('fuma', '')),
        ("Atividade no trabalho",  ev.get('atividade_trabalho', '')),
        ("Horas sentado/dia",      ev.get('horas_sentado', '')),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 6. Disponibilidade e Preferências ─────────────────────────────────────
    disp = dados.get('disponibilidade', {})
    story += _titulo_secao("6. DISPONIBILIDADE E PREFERÊNCIAS", est)
    story.append(_tabela_kv_2col([
        ("Dias/semana",        str(disp.get('dias_semana', ''))),
        ("Horário preferido",  disp.get('horario', '')),
        ("Tempo por sessão",   f"{disp.get('tempo_sessao', '')} min"),
        ("Local de treino",    disp.get('local', '')),
        ("Equipamentos",       ", ".join(disp.get('equipamentos', []))),
        ("Não gosta de",       disp.get('nao_gosta', '') or "—"),
        ("Prefere",            disp.get('prefere', '') or "—"),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 7. Medidas Iniciais ───────────────────────────────────────────────────
    med = dados.get('medidas', {})
    story += _titulo_secao("7. MEDIDAS INICIAIS", est)
    p_val  = med.get('peso', 0)
    a_val  = med.get('altura', 0)
    ca_val = med.get('circ_abdominal', 0)
    pg_val = med.get('perc_gordura', 0)
    story.append(_tabela_kv_2col([
        ("Peso",                 f"{p_val} kg" if p_val > 0 else "Não informado"),
        ("Altura",               f"{a_val} cm" if a_val > 0 else "Não informado"),
        ("Circ. Abdominal",      f"{ca_val} cm" if ca_val > 0 else "Não informado"),
        ("% de Gordura",         f"{pg_val}%" if pg_val > 0 else "Não informado"),
        ("Observações",          med.get('obs', '') or "—"),
    ], est))
    story.append(Spacer(1, 0.3 * cm))

    # ── 8. Termo ──────────────────────────────────────────────────────────────
    termo = dados.get('termo', {})
    story += _titulo_secao("8. TERMO DE RESPONSABILIDADE", est)
    story.append(_tabela_kv_1col([
        ("Aceito o termo",    "Sim" if termo.get('aceito') else "Não"),
        ("Assinatura digital", termo.get('assinatura', '')),
    ], est))

    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer.read()
