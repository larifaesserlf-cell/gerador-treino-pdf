"""PDFs financeiros (relatório mensal + recibo) — Studio Personal Training."""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

PRETO     = colors.HexColor("#1A1A1A")
CINZA_ESC = colors.HexColor("#666666")
CINZA_MED = colors.HexColor("#888888")
CINZA_CLR = colors.HexColor("#E8E8E8")
CINZA_PAR = colors.HexColor("#FAFAFA")
ROXO      = colors.HexColor("#7C4DFF")
BRANCO    = colors.white

PAGE_W, PAGE_H = A4
MARGIN    = 2.0 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

_titulo = ParagraphStyle("ft", fontName="Helvetica-Bold", fontSize=16,
                         textColor=PRETO, spaceAfter=2)
_sub    = ParagraphStyle("fs", fontName="Helvetica-Bold", fontSize=11,
                         textColor=ROXO, spaceAfter=6, spaceBefore=12)
_body   = ParagraphStyle("fb", fontName="Helvetica", fontSize=9,
                         textColor=CINZA_ESC, spaceAfter=3)
_small  = ParagraphStyle("fsm", fontName="Helvetica", fontSize=8,
                         textColor=CINZA_MED)
_right  = ParagraphStyle("fr", fontName="Helvetica", fontSize=9,
                         textColor=CINZA_ESC, alignment=2)


def _p(t, s):
    return Paragraph(str(t), s)


def _base_tbl_style():
    return TableStyle([
        ("FONTNAME",       (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",      (0, 0), (-1, -1), CINZA_ESC),
        ("BACKGROUND",     (0, 0), (-1,  0), CINZA_CLR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_PAR]),
        ("GRID",           (0, 0), (-1, -1), 0.3, CINZA_CLR),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ])


def gerar_relatorio_mensal(dados):
    """
    dados = {
        'mes_ref': 'Junho/2026',
        'clientes_ativos': int,
        'receita_prevista': float,
        'receita_recebida': float,
        'pagamentos': [{'nome', 'valor', 'data', 'forma'}],
        'inadimplentes': [{'nome', 'valor', 'dias_atraso'}],
        'despesas': [{'data', 'descricao', 'categoria', 'valor'}],
    }
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN, bottomMargin=MARGIN)
    story = []

    story += [
        _p("Studio Personal Training", _titulo),
        _p(f"Relatório Financeiro — {dados.get('mes_ref', '')}", _sub),
        HRFlowable(width=CONTENT_W, thickness=1.5, color=PRETO),
        Spacer(1, 0.4 * cm),
    ]

    # Resumo geral
    receita_prev = float(dados.get("receita_prevista", 0))
    receita_rec  = float(dados.get("receita_recebida", 0))
    desp_list    = dados.get("despesas", [])
    total_desp   = sum(float(d.get("valor", 0)) for d in desp_list)
    lucro        = receita_rec - total_desp

    story.append(_p("Resumo do Mês", _sub))
    tbl_resumo = Table(
        [
            ["Indicador", "Valor"],
            ["Clientes ativos",    str(dados.get("clientes_ativos", 0))],
            ["Receita prevista",   f"R$ {receita_prev:,.2f}"],
            ["Receita recebida",   f"R$ {receita_rec:,.2f}"],
            ["Total de despesas",  f"R$ {total_desp:,.2f}"],
            ["Lucro líquido",      f"R$ {lucro:,.2f}"],
        ],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35],
    )
    tbl_resumo.setStyle(_base_tbl_style())
    story += [tbl_resumo, Spacer(1, 0.5 * cm)]

    # Pagamentos recebidos
    pags = dados.get("pagamentos", [])
    if pags:
        story.append(_p("Pagamentos Recebidos", _sub))
        rows = [["Cliente", "Valor", "Data", "Forma de pagamento"]]
        for p in pags:
            rows.append([
                p.get("nome", ""),
                f"R$ {float(p.get('valor', 0)):,.2f}",
                p.get("data", ""),
                p.get("forma", ""),
            ])
        tbl_pags = Table(
            rows,
            colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.18, CONTENT_W * 0.22, CONTENT_W * 0.22],
        )
        tbl_pags.setStyle(_base_tbl_style())
        story += [tbl_pags, Spacer(1, 0.5 * cm)]

    # Inadimplentes
    inad = dados.get("inadimplentes", [])
    if inad:
        story.append(_p("Inadimplentes", _sub))
        rows3 = [["Cliente", "Valor (R$)", "Dias de atraso"]]
        for i in inad:
            rows3.append([
                i.get("nome", ""),
                f"R$ {float(i.get('valor', 0)):,.2f}",
                f"{i.get('dias_atraso', '')} dias",
            ])
        tbl_inad = Table(
            rows3,
            colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.25, CONTENT_W * 0.25],
        )
        tbl_inad.setStyle(_base_tbl_style())
        story += [tbl_inad, Spacer(1, 0.5 * cm)]

    # Despesas por categoria
    if desp_list:
        story.append(_p("Despesas do Mês", _sub))
        rows4 = [["Data", "Descrição", "Categoria", "Valor"]]
        for d in sorted(desp_list, key=lambda x: x.get("data", "")):
            rows4.append([
                d.get("data", ""),
                d.get("descricao", ""),
                d.get("categoria", ""),
                f"R$ {float(d.get('valor', 0)):,.2f}",
            ])
        rows4.append(["", "TOTAL", "", f"R$ {total_desp:,.2f}"])
        tbl_desp = Table(
            rows4,
            colWidths=[CONTENT_W * 0.18, CONTENT_W * 0.42, CONTENT_W * 0.2, CONTENT_W * 0.2],
        )
        sty = _base_tbl_style()
        sty.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
        tbl_desp.setStyle(sty)
        story += [tbl_desp, Spacer(1, 0.5 * cm)]

    story.append(Spacer(1, 0.5 * cm))
    story.append(_p(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} — Studio Personal Training",
        _small,
    ))
    doc.build(story)
    return buf.getvalue()


def gerar_recibo(dados):
    """
    dados = {
        'numero': 'REC-LARI-0001',
        'cliente': 'Larissa',
        'servico': 'Plano 3 meses',
        'periodo': 'Junho/2026',
        'valor': 150.0,
        'data': '01/06/2026',
        'forma': 'PIX',
        'obs': '',
    }
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN * 2, bottomMargin=MARGIN * 2)
    story = []

    story += [
        _p("Studio Personal Training", _titulo),
        _p("RECIBO DE PAGAMENTO", _sub),
        HRFlowable(width=CONTENT_W, thickness=2, color=PRETO),
        Spacer(1, 0.6 * cm),
    ]

    info = [
        ["Nº do Recibo",        dados.get("numero", "")],
        ["Cliente",             dados.get("cliente", "")],
        ["Serviço contratado",  dados.get("servico", "")],
        ["Período de referência", dados.get("periodo", "")],
        ["Valor pago",          f"R$ {float(dados.get('valor', 0)):,.2f}"],
        ["Data do pagamento",   dados.get("data", "")],
        ["Forma de pagamento",  dados.get("forma", "")],
    ]
    if dados.get("obs"):
        info.append(["Observações", dados["obs"]])

    tbl = Table(info, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
    tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (-1, -1), CINZA_ESC),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [BRANCO, CINZA_PAR]),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, CINZA_CLR),
    ]))
    story += [tbl, Spacer(1, 2.0 * cm)]

    story += [
        HRFlowable(width=CONTENT_W * 0.45, thickness=1, color=CINZA_ESC),
        _p("Assinatura / Carimbo", _small),
        Spacer(1, 0.4 * cm),
        _p(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} — Studio Personal Training",
            _small,
        ),
    ]

    doc.build(story)
    return buf.getvalue()
