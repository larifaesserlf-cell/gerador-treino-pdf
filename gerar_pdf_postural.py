import io
import os
from datetime import datetime

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, Image as RLImage, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

try:
    from PIL import Image as PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _registrar_fontes():
    try:
        pdfmetrics.registerFont(TTFont('ArialPT',      'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('ArialPT-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        return 'ArialPT', 'ArialPT-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'

FONTE_N, FONTE_B = _registrar_fontes()

PRETO       = HexColor('#1A1A1A')
CINZA_MEIO  = HexColor('#666666')
CINZA_PAR   = HexColor('#FAFAFA')
CINZA_IMPAR = HexColor('#FFFFFF')
CINZA_SEP   = HexColor('#E8E8E8')
CINZA_ROD   = HexColor('#666666')
CINZA_SUB   = HexColor('#888888')
ROXO        = HexColor('#7C4DFF')

NOME_CONSULTORIA = 'Studio Personal Training'
PAGE_W, PAGE_H   = A4
MARGIN            = 2 * cm
CONTENT_W         = PAGE_W - 2 * MARGIN

MAX_FOTO_W = (CONTENT_W - 0.5 * cm) / 2
MAX_FOTO_H = 9.0 * cm

VISTAS_INFO = [
    {"key": "frente",       "label": "FRENTE"},
    {"key": "costas",       "label": "COSTAS"},
    {"key": "lat_direita",  "label": "LATERAL DIREITA"},
    {"key": "lat_esquerda", "label": "LATERAL ESQUERDA"},
    {"key": "agachamento",  "label": "AGACHAMENTO"},
    {"key": "core",         "label": "CORE / PRANCHA"},
]


def _p(texto, estilo):
    return Paragraph(str(texto) if texto else '—', estilo)


def _estilos():
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        'hdr_titulo': ps('PHdrTitulo', fontName=FONTE_B, fontSize=18,
                         textColor=white, alignment=TA_CENTER, leading=24),
        'hdr_nome':   ps('PHdrNome',   fontName=FONTE_B, fontSize=13,
                         textColor=white, alignment=TA_CENTER, spaceBefore=2),
        'hdr_sub':    ps('PHdrSub',    fontName=FONTE_N, fontSize=9,
                         textColor=CINZA_SUB, alignment=TA_CENTER, spaceBefore=2),
        'sec_titulo': ps('PSecTit',    fontName=FONTE_B, fontSize=11,
                         textColor=PRETO, spaceBefore=14, spaceAfter=4),
        'foto_lbl':   ps('PFotoLbl',   fontName=FONTE_B, fontSize=9,
                         textColor=PRETO, alignment=TA_CENTER, spaceAfter=4),
        'lbl':        ps('PLbl',       fontName=FONTE_B, fontSize=8,
                         textColor=CINZA_MEIO, leading=12),
        'val':        ps('PVal',       fontName=FONTE_N, fontSize=8,
                         textColor=PRETO, leading=12),
        'val_obs':    ps('PValObs',    fontName=FONTE_N, fontSize=8,
                         textColor=CINZA_MEIO, leading=12, alignment=TA_CENTER),
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
                             'Avaliação Postural — Documento Confidencial')
    canvas.drawRightString(PAGE_W - MARGIN, y - 0.35 * cm, f'Página {doc.page}')
    canvas.restoreState()


def _titulo_secao(texto, est):
    return [
        _p(texto, est['sec_titulo']),
        HRFlowable(width=CONTENT_W, thickness=0.6, color=CINZA_SEP, spaceAfter=5),
    ]


def _tabela_kv_2col(pares, est):
    validos = [(k, v if v else '—') for k, v in pares if k]
    rows = []
    for i in range(0, len(validos), 2):
        p1 = validos[i]
        p2 = validos[i + 1] if i + 1 < len(validos) else ('', '')
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


def _tabela_kv_1col(pares, est):
    rows = [
        [_p(k, est['lbl']), _p(v if v else '—', est['val'])]
        for k, v in pares if k
    ]
    if not rows:
        return Spacer(1, 0.1 * cm)
    cw = [CONTENT_W * 0.28, CONTENT_W * 0.72]
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


def _get_foto_path(dados, vkey):
    fotos = dados.get('fotos', {}).get(vkey, {})
    return fotos.get('editada') or fotos.get('original')


def _calc_foto_dims(path):
    if not _HAS_PIL:
        return MAX_FOTO_W, MAX_FOTO_H * 0.7
    try:
        with PILImage.open(path) as img:
            w, h = img.size
        if w == 0:
            return MAX_FOTO_W, MAX_FOTO_H * 0.7
        aspect = h / w
        fw = MAX_FOTO_W
        fh = fw * aspect
        if fh > MAX_FOTO_H:
            fh = MAX_FOTO_H
            fw = fh / aspect
        return fw, fh
    except Exception:
        return MAX_FOTO_W, MAX_FOTO_H * 0.7


def _cell_foto(path, label, obs, est):
    cell = [_p('<b>' + label + '</b>', est['foto_lbl'])]
    if path and os.path.exists(path):
        try:
            fw, fh = _calc_foto_dims(path)
            cell.append(RLImage(path, width=fw, height=fh))
        except Exception:
            cell.append(_p('(erro ao carregar foto)', est['val_obs']))
    else:
        cell.append(_p('(foto não enviada)', est['val_obs']))
    if obs:
        cell.append(Spacer(1, 0.12 * cm))
        cell.append(_p(obs, est['val_obs']))
    return cell


def gerar_pdf_postural(dados: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.2 * cm, bottomMargin=2.5 * cm,
    )
    est   = _estilos()
    story = []
    nome         = dados.get('cliente', 'Cliente')
    data_aval    = dados.get('data_avaliacao', '')
    data_geracao = dados.get('data_geracao', datetime.now().strftime('%d/%m/%Y %H:%M'))
    hdr = Table([
        [_p('AVALIAÇÃO POSTURAL',          est['hdr_titulo'])],
        [_p(nome.upper(),                   est['hdr_nome'])],
        [_p('Studio Personal Training',     est['hdr_sub'])],
        [_p('Data da avaliação: ' + data_aval + '  ·  Gerado em: ' + data_geracao, est['hdr_sub'])],
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
    story += _titulo_secao('REGISTRO FOTOGRÁFICO', est)
    foto_rows = []
    for i in range(0, len(VISTAS_INFO), 2):
        v_left  = VISTAS_INFO[i]
        v_right = VISTAS_INFO[i + 1] if i + 1 < len(VISTAS_INFO) else None
        p_left   = _get_foto_path(dados, v_left['key'])
        obs_left = dados.get('observacoes_fotos', {}).get(v_left['key'], '')
        cell_left = _cell_foto(p_left, v_left['label'], obs_left, est)
        if v_right:
            p_right    = _get_foto_path(dados, v_right['key'])
            obs_right  = dados.get('observacoes_fotos', {}).get(v_right['key'], '')
            cell_right = _cell_foto(p_right, v_right['label'], obs_right, est)
        else:
            cell_right = []
        foto_rows.append([cell_left, cell_right])
    if foto_rows:
        cw = [MAX_FOTO_W + 0.25 * cm, MAX_FOTO_W + 0.25 * cm]
        ft = Table(foto_rows, colWidths=cw)
        ft.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('LINEBELOW',     (0, 0), (-1, -2), 0.5, CINZA_SEP),
        ]))
        story.append(ft)
    story.append(Spacer(1, 0.4 * cm))
    va = dados.get('vista_anterior', {})
    if any(va.values()):
        story += _titulo_secao('VISTA ANTERIOR (FRENTE)', est)
        story.append(_tabela_kv_2col([
            ('Alinhamento da cabeça', va.get('alinhamento_cabeca', '')),
            ('Ombros',                  va.get('ombros', '')),
            ('Triângulo de Tales',    va.get('triangulo_tales', '')),
            ('Cristas ilíacas',        va.get('cristas_iliacas', '')),
            ('Joelhos',                 va.get('joelhos', '')),
            ('Pés',                     va.get('pes', '')),
        ], est))
        if va.get('obs'):
            story.append(Spacer(1, 0.15 * cm))
            story.append(_tabela_kv_1col([('Observações', va['obs'])], est))
        story.append(Spacer(1, 0.3 * cm))
    vp = dados.get('vista_posterior', {})
    if any(vp.values()):
        story += _titulo_secao('VISTA POSTERIOR (COSTAS)', est)
        story.append(_tabela_kv_2col([
            ('Coluna',             vp.get('coluna', '')),
            ('Escápulas',           vp.get('escapulas', '')),
            ('Glúteos',             vp.get('gluteos', '')),
            ('Dobras poplíteas',   vp.get('dobras_popliteas', '')),
            ('Calcanhares',        vp.get('calcanhares', '')),
        ], est))
        if vp.get('obs'):
            story.append(Spacer(1, 0.15 * cm))
            story.append(_tabela_kv_1col([('Observações', vp['obs'])], est))
        story.append(Spacer(1, 0.3 * cm))
    vl = dados.get('vista_lateral', {})
    if any(vl.values()):
        story += _titulo_secao('VISTA LATERAL', est)
        story.append(_tabela_kv_2col([
            ('Posição da cabeça',   vl.get('cabeca', '')),
            ('Coluna cervical',        vl.get('cervical', '')),
            ('Coluna torácica',        vl.get('toracica', '')),
            ('Coluna lombar',          vl.get('lombar', '')),
            ('Pelve',                  vl.get('pelve', '')),
            ('Joelho (lateral)',        vl.get('joelho_lat', '')),
        ], est))
        if vl.get('obs'):
            story.append(Spacer(1, 0.15 * cm))
            story.append(_tabela_kv_1col([('Observações', vl['obs'])], est))
        story.append(Spacer(1, 0.3 * cm))
    af = dados.get('avaliacao_funcional', {})
    if af.get('agachamento') or af.get('core'):
        story += _titulo_secao('AVALIAÇÃO FUNCIONAL', est)
        pares_af = []
        if af.get('agachamento'):
            pares_af.append(('Agachamento', af['agachamento']))
        if af.get('core'):
            pares_af.append(('Core / Prancha', af['core']))
        story.append(_tabela_kv_1col(pares_af, est))
        story.append(Spacer(1, 0.3 * cm))
    conc = dados.get('conclusao', {})
    if any(conc.values()):
        story += _titulo_secao('CONCLUSÃO E RECOMENDAÇÕES', est)
        pares_conc = []
        if conc.get('principais_alteracoes'):
            pares_conc.append(('Principais alterações', conc['principais_alteracoes']))
        if conc.get('musculos_encurtados'):
            pares_conc.append(('Músculos encurtados', conc['musculos_encurtados']))
        if conc.get('musculos_fracos'):
            pares_conc.append(('Músculos fracos/alongados', conc['musculos_fracos']))
        if conc.get('exercicios_corretivos'):
            pares_conc.append(('Exerc. corretivos', conc['exercicios_corretivos']))
        if conc.get('obs_gerais'):
            pares_conc.append(('Observações gerais', conc['obs_gerais']))
        if conc.get('proxima_reavaliacao'):
            pares_conc.append(('Próxima reavaliação', conc['proxima_reavaliacao']))
        if pares_conc:
            story.append(_tabela_kv_1col(pares_conc, est))
    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer.read()
