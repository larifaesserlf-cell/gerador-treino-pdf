from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# ── Registro de fonte com suporte a acentos (Arial TTF) ───────────────────────

def _registrar_fontes():
    try:
        pdfmetrics.registerFont(TTFont('ArialPT',      'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('ArialPT-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        pdfmetrics.registerFont(TTFont('ArialPT-It',   'C:/Windows/Fonts/ariali.ttf'))
        return 'ArialPT', 'ArialPT-Bold'
    except Exception:
        # Fallback para Helvetica (suporta latin-1 / WinAnsi)
        return 'Helvetica', 'Helvetica-Bold'

FONTE_N, FONTE_B = _registrar_fontes()

# ── Paleta de cores ───────────────────────────────────────────────────────────

PRETO       = HexColor('#1A1A1A')
CINZA_MEIO  = HexColor('#595959')
CINZA_PAR   = HexColor('#F4F4F4')
CINZA_IMPAR = HexColor('#EAEAEA')
CINZA_SEP   = HexColor('#CCCCCC')
CINZA_ROD   = HexColor('#999999')
CINZA_SUB   = HexColor('#AAAAAA')
CINZA_TH    = HexColor('#333333')
CINZA_FILL  = HexColor('#FAFAFA')

NOME_CONSULTORIA = "Studio Personal Training"

PAGE_W, PAGE_H = A4
MARGIN    = 2 * cm
CONTENT_W = PAGE_W - 2 * MARGIN   # ~17 cm


# ── Helpers ───────────────────────────────────────────────────────────────────

def _p(texto, estilo):
    return Paragraph(str(texto), estilo)


def _calcular_imc(peso, altura_cm):
    imc = peso / (altura_cm / 100) ** 2
    if   imc < 18.5: classe = "Abaixo do peso"
    elif imc < 25.0: classe = "Peso normal"
    elif imc < 30.0: classe = "Sobrepeso"
    elif imc < 35.0: classe = "Obesidade I"
    elif imc < 40.0: classe = "Obesidade II"
    else:            classe = "Obesidade III"
    return round(imc, 1), classe


def _estilos():
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        # ── Cabeçalho (todos centralizados) ──────────────────────────────────
        'hdr_titulo': ps('HdrTitulo', fontName=FONTE_B, fontSize=18,
                         textColor=white, alignment=TA_CENTER, leading=24),
        'hdr_nome':   ps('HdrNome',   fontName=FONTE_B, fontSize=13,
                         textColor=white, alignment=TA_CENTER, spaceBefore=2),
        'hdr_consul': ps('HdrConsul', fontName=FONTE_N, fontSize=9,
                         textColor=CINZA_SUB, alignment=TA_CENTER, spaceBefore=2),
        'hdr_data':   ps('HdrData',   fontName=FONTE_N, fontSize=8,
                         textColor=CINZA_SUB, alignment=TA_CENTER),
        # ── Seções ────────────────────────────────────────────────────────────
        'sec_titulo': ps('SecTitulo', fontName=FONTE_B, fontSize=12,
                         textColor=PRETO, spaceBefore=14, spaceAfter=5),
        'div_info':   ps('DivInfo',   fontName=FONTE_N, fontSize=9,
                         textColor=PRETO, spaceAfter=8),
        # ── Tabela de treino — header ─────────────────────────────────────────
        'treino_hdr': ps('TreinoHdr', fontName=FONTE_B, fontSize=11,
                         textColor=white),
        'th_left':    ps('ThLeft',    fontName=FONTE_B, fontSize=7,
                         textColor=white, alignment=TA_LEFT),
        'th_center':  ps('ThCenter',  fontName=FONTE_B, fontSize=7,
                         textColor=white, alignment=TA_CENTER),
        # ── Tabela de treino — dados ──────────────────────────────────────────
        'td_nome':    ps('TdNome',    fontName=FONTE_B, fontSize=8,
                         textColor=PRETO,      leading=11),
        'td_left':    ps('TdLeft',    fontName=FONTE_N, fontSize=8,
                         textColor=PRETO,      leading=11),
        'td_center':  ps('TdCenter2', fontName=FONTE_N, fontSize=8,
                         textColor=PRETO,      leading=11, alignment=TA_CENTER),
        'td_met':     ps('TdMet',     fontName=FONTE_N, fontSize=8,
                         textColor=CINZA_MEIO, leading=11),
        # ── Perfil ────────────────────────────────────────────────────────────
        'lbl': ps('Lbl', fontName=FONTE_B, fontSize=8, textColor=CINZA_MEIO),
        'val': ps('Val', fontName=FONTE_N, fontSize=8, textColor=PRETO),
        # ── Corpo de texto ────────────────────────────────────────────────────
        'corpo': ps('Corpo', fontName=FONTE_N, fontSize=8,
                    textColor=CINZA_MEIO, leading=13, spaceAfter=2),
    }


# ── Rodapé (callback por página) ──────────────────────────────────────────────

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
                             "Documento confidencial — uso exclusivo do cliente")
    canvas.drawRightString(PAGE_W - MARGIN, y - 0.35 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ── Blocos visuais ─────────────────────────────────────────────────────────────

def _bloco_cabecalho(dados, est):
    """Cabeçalho: 4 linhas centralizadas sobre fundo preto."""
    data_geracao = datetime.now().strftime("%d/%m/%Y")

    tabela = Table(
        [
            [_p("PLANO DE TREINO PERSONALIZADO", est['hdr_titulo'])],
            [_p(dados['nome'].upper(), est['hdr_nome'])],
            [_p(NOME_CONSULTORIA, est['hdr_consul'])],
            [_p(f"Gerado em: {data_geracao}", est['hdr_data'])],
        ],
        colWidths=[CONTENT_W],
    )
    tabela.setStyle(TableStyle([
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
    return tabela


def _bloco_perfil(dados, est):
    imc, classe_imc = _calcular_imc(dados['peso'], dados['altura'])
    nivel_map   = {"iniciante": "Iniciante", "intermediario": "Intermediário",
                   "avancado": "Avançado"}
    sexo_map    = {"M": "Masculino", "F": "Feminino"}
    divisao_map = {
        "AB_4x": "A/B (4x/sem)", "ABC": "A/B/C", "ABCD": "A/B/C/D",
        "push_pull_legs": "Push/Pull/Legs", "full_body_3x": "Full Body (3x/sem)",
        "full_body_50_2x": "Full Body 50+ (2x/sem)", "full_body_50_3x": "Full Body 50+ (3x/sem)",
    }
    objetivo_map = {
        "hipertrofia": "Hipertrofia Muscular",
        "emagrecimento": "Emagrecimento",
        "postural": "Correção Postural",
    }

    linhas = [
        ("Nome",             dados['nome'],
         "Objetivo",         objetivo_map.get(dados['objetivo'], dados['objetivo'].title())),
        ("Idade",            f"{dados['idade']} anos",
         "Nível",       nivel_map.get(dados['nivel'], dados['nivel'])),
        ("Sexo",             sexo_map.get(dados['sexo'], dados['sexo']),
         "IMC",              f"{imc}  ({classe_imc})"),
        ("Peso / Altura",    f"{dados['peso']} kg  /  {dados['altura']} cm",
         "Frequência",  f"{dados['frequencia']}x por semana"),
        ("Duração sessão", f"{dados['tempo']} min",
         "Período",     f"{dados['periodo']} semanas"),
        ("Divisão",     divisao_map.get(dados['divisao'], dados['divisao']),
         "Início",      dados['data_inicio']),
        ("Equipamentos",     dados['equipamentos'], "", ""),
    ]
    if dados.get('restricoes'):
        linhas.append(("Restrições / Lesões",
                        dados['restricoes'], "", ""))

    rows = []
    for a, b, c, d in linhas:
        rows.append([_p(a, est['lbl']), _p(b, est['val']),
                     _p(c, est['lbl']), _p(d, est['val'])])

    cw = [CONTENT_W * f for f in (0.16, 0.34, 0.16, 0.34)]
    t  = Table(rows, colWidths=cw)
    s  = TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 7),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
    ])
    for i in range(len(rows)):
        s.add('BACKGROUND', (0, i), (-1, i),
              CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
    t.setStyle(s)
    return t


def _bloco_treino(letra, exercicios, est, descricao=""):
    label = f"TREINO  {letra}" + (f"  —  {descricao}" if descricao else "")

    hdr_t = Table([[_p(label, est['treino_hdr'])]], colWidths=[CONTENT_W])
    hdr_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), PRETO),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
    ]))

    # 8 colunas — larguras ajustadas para SERIES caber sem quebrar
    # #=3%  Exercicio=21%  Grupo=17.5%  Series=8%  Reps=8.5%  Metodo=16%  Carga=13%  Obs=13%
    cw = [CONTENT_W * f for f in (0.03, 0.21, 0.175, 0.08, 0.085, 0.16, 0.13, 0.13)]

    cabecalho = [
        _p("#",              est['th_left']),
        _p("EXERCÍCIO", est['th_left']),
        _p("GRUPO MUSCULAR", est['th_left']),
        _p("SÉRIES",    est['th_center']),
        _p("REPS",           est['th_center']),
        _p("MÉTODO",    est['th_center']),
        _p("CARGA (kg)",     est['th_center']),
        _p("OBSERVAÇÃO", est['th_center']),
    ]

    rows = [cabecalho]
    for i, ex in enumerate(exercicios, 1):
        rows.append([
            _p(str(i),            est['td_center']),
            _p(ex['nome'],        est['td_nome']),
            _p(ex['grupo'],       est['td_left']),
            _p(str(ex['series']), est['td_center']),
            _p(ex['reps'],        est['td_center']),
            _p(ex['metodo'],      est['td_met']),
            _p("", est['td_left']),   # Carga — preencher à mão
            _p("", est['td_left']),   # Observação — preencher à mão
        ])

    ex_t = Table(rows, colWidths=cw, repeatRows=1)
    s = TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  CINZA_TH),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, 0),  4),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  4),
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.3,  HexColor('#DDDDDD')),
        # Colunas de preenchimento manual com borda visível
        ('BOX',           (6, 1), (7, -1),  0.6,  HexColor('#AAAAAA')),
        ('LINEBEFORE',    (7, 1), (7, -1),  0.6,  HexColor('#AAAAAA')),
        ('BACKGROUND',    (6, 1), (7, -1),  CINZA_FILL),
    ])
    for i in range(1, len(rows)):
        s.add('BACKGROUND', (0, i), (5, i),
              CINZA_PAR if i % 2 != 0 else CINZA_IMPAR)
    ex_t.setStyle(s)

    return KeepTogether([hdr_t, ex_t])


def _bloco_cardio(cardio, est):
    campos = [
        ("Protocolo",    cardio['protocolo']),
        ("Frequência", cardio['frequencia']),
        ("Duração", cardio['duracao']),
        ("Intensidade",  cardio['intensidade']),
        ("Observação", cardio['obs']),
    ]
    rows = [[_p(k, est['lbl']), _p(v, est['corpo'])] for k, v in campos]
    cw   = [CONTENT_W * 0.18, CONTENT_W * 0.82]
    t    = Table(rows, colWidths=cw)
    s    = TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEBELOW',     (0, -1), (-1, -1), 0.3, HexColor('#CCCCCC')),
    ])
    for i in range(len(rows)):
        s.add('BACKGROUND', (0, i), (-1, i),
              CINZA_PAR if i % 2 == 0 else CINZA_IMPAR)
    t.setStyle(s)
    return t


def _bloco_periodizacao(periodizacao, est):
    rows = [
        [_p("Modelo",         est['lbl']), _p(periodizacao['nome'],      est['val'])],
        [_p("Descrição", est['lbl']),
         _p(periodizacao['descricao'], est['corpo'])],
        [_p("Protocolo",      est['lbl']),
         _p(periodizacao['protocolo'].replace('\n', '<br/>'), est['corpo'])],
    ]
    cw = [CONTENT_W * 0.18, CONTENT_W * 0.82]
    t  = Table(rows, colWidths=cw)
    s  = TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('BACKGROUND',    (0, 0), (-1, 0),  CINZA_PAR),
        ('BACKGROUND',    (0, 1), (-1, 1),  CINZA_IMPAR),
        ('BACKGROUND',    (0, 2), (-1, 2),  CINZA_PAR),
        ('LINEAFTER',     (0, 0), (0, -1),  3, PRETO),
        ('LINEBELOW',     (0, -1), (-1, -1), 0.3, HexColor('#CCCCCC')),
    ])
    t.setStyle(s)
    return t


def _bloco_texto(texto, est):
    html = texto.replace('\n', '<br/>')
    t = Table([[_p(html, est['corpo'])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), CINZA_PAR),
        ('TOPPADDING',    (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('LINEAFTER',     (0, 0), (0, -1),   3, PRETO),
    ]))
    return t


def _titulo_secao(texto, est):
    return [
        _p(texto, est['sec_titulo']),
        HRFlowable(width=CONTENT_W, thickness=0.8, color=PRETO, spaceAfter=7),
    ]


# ── Entrada pública ────────────────────────────────────────────────────────────

def gerar_pdf(dados, treinos, descricoes_treino, cardio,
              progressao, periodizacao, observacoes, nome_arquivo):

    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.2 * cm,
        bottomMargin=2.5 * cm,
    )

    est   = _estilos()
    story = []

    divisao_nomes = {
        "AB_4x":           "A/B  (4x por semana)",
        "ABC":             "A/B/C",
        "ABCD":            "A/B/C/D",
        "push_pull_legs":  "Push / Pull / Legs",
        "full_body_3x":    "Full Body  (3x por semana)",
        "full_body_50_2x": "Full Body 50+  (2x por semana)",
        "full_body_50_3x": "Full Body 50+  (3x por semana)",
    }

    story.append(_bloco_cabecalho(dados, est))
    story.append(Spacer(1, 0.45 * cm))

    story += _titulo_secao("PERFIL DO CLIENTE", est)
    story.append(_bloco_perfil(dados, est))
    story.append(Spacer(1, 0.3 * cm))

    story += _titulo_secao("PLANO DE TREINO", est)
    div_label = divisao_nomes.get(dados['divisao'], dados['divisao'])
    story.append(_p(
        f"Divisão: <b>{div_label}</b>  —  "
        f"{dados['frequencia']}x por semana  /  {dados['tempo']} min por sessão",
        est['div_info'],
    ))
    for letra, exercicios in treinos.items():
        story.append(_bloco_treino(letra, exercicios, est,
                                   descricao=descricoes_treino.get(letra, "")))
        story.append(Spacer(1, 0.35 * cm))

    story += _titulo_secao("PROTOCOLO DE CARDIO / AERÓBICO", est)
    story.append(_bloco_cardio(cardio, est))
    story.append(Spacer(1, 0.3 * cm))

    story += _titulo_secao("PERIODIZAÇÃO", est)
    story.append(_bloco_periodizacao(periodizacao, est))
    story.append(Spacer(1, 0.3 * cm))

    story += _titulo_secao("PROTOCOLO DE PROGRESSÃO DE CARGA", est)
    story.append(_bloco_texto(progressao, est))
    story.append(Spacer(1, 0.3 * cm))

    story += _titulo_secao("OBSERVAÇÕES GERAIS DO PLANO", est)
    story.append(_bloco_texto(observacoes, est))

    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
