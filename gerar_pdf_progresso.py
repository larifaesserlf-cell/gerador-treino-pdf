"""PDF de progresso do cliente — Studio Personal Training."""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Paleta ────────────────────────────────────────────────────────────────────
PRETO     = colors.HexColor("#1A1A1A")
CINZA_ESC = colors.HexColor("#666666")
CINZA_MED = colors.HexColor("#888888")
CINZA_CLR = colors.HexColor("#E8E8E8")
ROXO      = colors.HexColor("#7C4DFF")
BRANCO    = colors.white

PAGE_W, PAGE_H = A4
MARGIN        = 2.0 * cm
CONTENT_W     = PAGE_W - 2 * MARGIN

_sty_titulo = ParagraphStyle("pt",  fontName="Helvetica-Bold", fontSize=16,
                              textColor=PRETO,    spaceAfter=4)
_sty_sub    = ParagraphStyle("ps",  fontName="Helvetica-Bold", fontSize=11,
                              textColor=CINZA_ESC, spaceAfter=6, spaceBefore=10)
_sty_body   = ParagraphStyle("pb",  fontName="Helvetica",      fontSize=9,
                              textColor=CINZA_ESC, spaceAfter=3)
_sty_small  = ParagraphStyle("psm", fontName="Helvetica",      fontSize=8,
                              textColor=CINZA_MED)


def _chart_img_peso(registros, meta=None):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime as dt

        if not registros:
            return None
        pairs = []
        for r in registros:
            try:
                pairs.append((dt.strptime(r["data"], "%d/%m/%Y").date(), float(r["peso"])))
            except Exception:
                continue
        if not pairs:
            return None
        pairs.sort()
        xs, ys = zip(*pairs)

        fig, ax = plt.subplots(figsize=(7, 2.8))
        ax.plot(xs, ys, marker="o", color="#7C4DFF", linewidth=2, markersize=5)
        if meta:
            ax.axhline(float(meta), color="#888888", linestyle="--", linewidth=1,
                       label=f"Meta: {meta} kg")
            ax.legend(fontsize=8)
        ax.set_ylabel("kg", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.autofmt_xdate(rotation=30)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=110)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _chart_img_medidas(registros):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime as dt

        CAMPOS = [
            ("circ_abd", "Circ. Abd."),
            ("cintura",  "Cintura"),
            ("quadril",  "Quadril"),
            ("coxa_d",   "Coxa D."),
            ("braco_d",  "Braço D."),
        ]
        CORES = ["#7C4DFF", "#5C3DC5", "#666666", "#888888", "#CCCCCC"]

        if not registros:
            return None

        fig, ax = plt.subplots(figsize=(7, 3.2))
        plotou = False
        for (key, label), cor in zip(CAMPOS, CORES):
            pts = []
            for r in registros:
                try:
                    v = r.get(key)
                    if v:
                        pts.append((dt.strptime(r["data"], "%d/%m/%Y").date(), float(v)))
                except Exception:
                    continue
            if pts:
                pts.sort()
                xs, ys = zip(*pts)
                ax.plot(xs, ys, marker="o", color=cor, linewidth=1.5,
                        markersize=4, label=label)
                plotou = True

        if not plotou:
            plt.close(fig)
            return None

        ax.set_ylabel("cm", fontsize=8)
        ax.legend(fontsize=7, loc="best")
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.autofmt_xdate(rotation=30)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=110)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def gerar_pdf_progresso(dados: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=MARGIN, rightMargin=MARGIN,
                             topMargin=MARGIN, bottomMargin=MARGIN)
    story = []

    # Cabeçalho
    story.append(Paragraph("Studio Personal Training", _sty_titulo))
    story.append(Paragraph("Relatório de Progresso", _sty_sub))
    story.append(Paragraph(f"<b>Cliente:</b> {dados.get('cliente', '')}", _sty_body))
    ini = dados.get("data_inicio", "—")
    fim = dados.get("data_fim", datetime.now().strftime("%d/%m/%Y"))
    story.append(Paragraph(f"<b>Período:</b> {ini} → {fim}", _sty_body))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=CINZA_CLR))
    story.append(Spacer(1, 0.3 * cm))

    medidas    = dados.get("medidas", [])
    todos_peso = dados.get("todos_pesos", [])
    meta       = dados.get("meta_peso")

    # Tabela comparativa
    if len(medidas) >= 1:
        story.append(Paragraph("Comparativo de Medidas", _sty_sub))

        CAMPOS_PDF = [
            ("peso",      "Peso (kg)"),
            ("circ_abd",  "Circ. Abd. (cm)"),
            ("cintura",   "Cintura (cm)"),
            ("quadril",   "Quadril (cm)"),
            ("coxa_d",    "Coxa D. (cm)"),
            ("braco_d",   "Braço D. (cm)"),
            ("perc_gord", "% Gordura"),
        ]
        primeira = medidas[0]
        ultima   = medidas[-1]

        header = [
            "Medida",
            f"Inicial\n{primeira.get('data', '')}",
            f"Atual\n{ultima.get('data', '')}",
            "Variação",
        ]
        rows = [header]
        for key, label in CAMPOS_PDF:
            vi = primeira.get(key)
            va = ultima.get(key)
            if vi is None and va is None:
                continue
            vi_s = f"{float(vi):.1f}" if vi else "—"
            va_s = f"{float(va):.1f}" if va else "—"
            diff_s = "—"
            if vi and va:
                d = float(va) - float(vi)
                diff_s = f"{'+'if d>0 else''}{d:.1f}"
            rows.append([label, vi_s, va_s, diff_s])

        cw = [CONTENT_W*0.38, CONTENT_W*0.22, CONTENT_W*0.22, CONTENT_W*0.18]
        tbl = Table(rows, colWidths=cw)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",      (0, 0), (-1, 0), PRETO),
            ("TEXTCOLOR",       (0, 0), (-1, 0), BRANCO),
            ("FONTNAME",        (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",        (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",  (0, 1), (-1, -1), [BRANCO, CINZA_CLR]),
            ("GRID",            (0, 0), (-1, -1), 0.5, CINZA_MED),
            ("ALIGN",           (1, 0), (-1, -1), "CENTER"),
            ("VALIGN",          (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",      (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",   (0, 0), (-1, -1), 3),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

        # Resumo peso / meta
        partes = []
        p_ini = primeira.get("peso")
        p_atu = ultima.get("peso")
        if p_ini:
            partes.append(f"Peso inicial: <b>{float(p_ini):.1f} kg</b>")
        if p_atu:
            partes.append(f"Peso atual: <b>{float(p_atu):.1f} kg</b>")
        if meta:
            partes.append(f"Meta: <b>{float(meta):.1f} kg</b>")
        if partes:
            story.append(Paragraph("  |  ".join(partes), _sty_body))
            story.append(Spacer(1, 0.3 * cm))

    # Gráfico de peso
    if todos_peso:
        story.append(Paragraph("Evolução do Peso", _sty_sub))
        buf_c = _chart_img_peso(todos_peso, meta)
        if buf_c:
            story.append(Image(buf_c, width=CONTENT_W, height=CONTENT_W * 2.8 / 7))
            story.append(Spacer(1, 0.3 * cm))

    # Gráfico de medidas
    if len(medidas) >= 2:
        story.append(Paragraph("Evolução das Medidas", _sty_sub))
        buf_m = _chart_img_medidas(medidas)
        if buf_m:
            story.append(Image(buf_m, width=CONTENT_W, height=CONTENT_W * 3.2 / 7))
            story.append(Spacer(1, 0.3 * cm))

    # Observações
    obs = dados.get("obs_gerais", "")
    if obs:
        story.append(Paragraph("Observações Gerais", _sty_sub))
        story.append(Paragraph(obs, _sty_body))
        story.append(Spacer(1, 0.3 * cm))

    # Rodapé
    story.append(HRFlowable(width="100%", thickness=1, color=CINZA_CLR))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} — Studio Personal Training",
        _sty_small,
    ))

    doc.build(story)
    return buf.getvalue()
