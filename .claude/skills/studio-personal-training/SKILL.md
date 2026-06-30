---
name: studio-personal-training
description: Contexto completo para trabalhar no projeto Studio Personal Training — Sistema de Gestão Online (Streamlit). Carregue esta skill sempre que for editar este projeto.
---

# Studio Personal Training — Sistema de Gestão Online

## 1. Visão Geral do Projeto

| Campo | Valor |
|---|---|
| **Nome** | Studio Personal Training — Sistema de Gestão Online |
| **Stack** | Python + Streamlit |
| **Deploy** | Streamlit Cloud — https://2rve8kptjdtf3tcvekxhc7.streamlit.app |
| **Repositório** | https://github.com/larifaesserlf-cell/gerador-treino-pdf |
| **Diretório local** | `C:\Users\larif\Documents\projetos\treino-pdf` |
| **Branch principal** | `master` |
| **Comando para rodar** | `python -m streamlit run app.py` |

Push para `master` atualiza o app publicado automaticamente em 2–3 minutos.

---

## 2. Estrutura de Arquivos

```
treino-pdf/
├── app.py                    — ÚNICO arquivo de interface. Toda a UI, roteamento e lógica de negócio.
├── exercicios.py             — Banco de exercícios: dicts EXERCICIOS, DESCRICOES_TREINO,
│                               CARDIO, PROGRESSAO, PERIODIZACAO, OBSERVACOES
│                               (separados por sexo → divisão → treino)
├── video_exercicios.py       — Dict VIDEOS_EXERCICIOS (nome_exercicio → URL YouTube).
│                               _VIDEOS_CADASTRADOS é o dict de fábrica (editar aqui).
│                               Nomes usam "c/" não "com": ex "Supino Reto c/ Barra".
├── videos_exercicios.json    — Overrides salvos pela professora via UI (runtime).
│                               Merge: {**base, **runtime}. Nunca salvar entradas com "".
├── gerar_pdf.py              — Plano de treino em PDF (ReportLab)
├── gerar_pdf_anamnese.py     — Ficha de anamnese em PDF
├── gerar_pdf_postural.py     — Laudo de avaliação postural em PDF
├── gerar_pdf_progresso.py    — Relatório de progresso (peso + medidas) em PDF
├── gerar_pdf_financeiro.py   — Recibo de pagamento e relatório financeiro mensal em PDF
├── config.py                 — EMAIL_REMETENTE e EMAIL_SENHA. NUNCA commitar.
├── requirements.txt          — streamlit, reportlab, Pillow, plotly, matplotlib
├── canvas_editor/
│   └── index.html            — Editor de marcação postural (HTML/JS standalone, sem dependências Python)
├── dados_clientes/           — JSONs de clientes. NUNCA commitar (no .gitignore).
│   ├── cadastro_[slug].json      — Nome, nascimento, WhatsApp, e-mail, foto
│   ├── anamnese_[slug]_[ts].json — Ficha de anamnese
│   ├── medidas_[slug].json       — Lista de registros de medidas corporais
│   ├── peso_[slug].json          — Lista de registros de peso isolado
│   ├── treino_[slug].json        — Último treino gerado (dados + exercícios + descrições)
│   ├── checkins_[slug].json      — Lista de check-ins diários
│   ├── feedback_[slug].json      — Lista de feedbacks semanais
│   ├── acesso_[slug].json        — Usuário e senha do aluno
│   ├── financeiro_[slug].json    — Contrato: tipo, valor, datas, status
│   ├── pagamentos_[slug].json    — Lista de pagamentos registrados
│   └── despesas.json             — Lista global de despesas da consultoria
└── videos_exercicios/        — Vídeos próprios (se houver). NUNCA commitar.
```

**Slug:** gerado por `_slug(nome)` em `app.py` — ASCII lowercase, underscores, sem acentos.

---

## 3. Padrões Obrigatórios do Projeto

### Identidade visual
| Uso | Cor |
|---|---|
| Headers / títulos | `#1A1A1A` (preto) |
| Texto secundário | `#595959` (cinza escuro) |
| Linhas ímpares de tabela | `#F4F4F4` (cinza claro) |
| Linhas pares de tabela | `#EAEAEA` (cinza) |
| Fundo geral | branco |

**Não alterar** a paleta preta/cinza em nenhuma circunstância.

### Datas
- Sempre exibidas como `DD/MM/AAAA` na interface e nos PDFs
- Armazenadas internamente em ISO `YYYY-MM-DD` nos JSONs
- Helper de conversão: `_fmt_data_br(iso_str)` em `app.py`

### Acentuação em PDFs
- Usar sempre `TTFont` com `arial.ttf` do Windows:
  ```python
  pdfmetrics.registerFont(TTFont('ArialPT', 'C:/Windows/Fonts/arial.ttf'))
  ```
- Fallback: `Helvetica` (suporta latin-1 mas não todos os caracteres)
- **Nunca** usar `Helvetica` como fonte principal em PDFs novos

### Salvar dados
- Sempre em `dados_clientes/[tipo]_[slug].json` via `_salvar_json(path, data)`
- Criar o diretório automaticamente: `os.makedirs("dados_clientes", exist_ok=True)`

### Commits
- Sempre em **português**, descrevendo o que foi feito
- Formato: `git commit -m "descrição clara do que foi alterado"`

---

## 4. Estrutura do App (`app.py`)

### Roteamento por session state

```python
st.session_state['area']  # None | 'aluno' | 'aluno_login' | 'aluno_logado' | 'professora'
```

| `area` | Função chamada | Descrição |
|---|---|---|
| `None` | `_pagina_home()` | Tela inicial com os dois botões |
| `'aluno'` | `_pagina_aluno()` | Área do aluno sem login |
| `'aluno_login'` | `_pagina_login_aluno()` | Formulário login do aluno |
| `'aluno_logado'` | `_pagina_aluno_logado()` | Área do aluno autenticado |
| `'professora'` | `_pagina_professora()` | Área da professora |

### Página inicial
Dois cards + dois botões:
- **"Sou Aluno"** → `area = 'aluno'`
- **"Acesso Professora"** → formulário de senha (`admin` / `studio2026`)
- **"Entrar como Aluno"** → `area = 'aluno_login'` (com credenciais)

### Área do Aluno (sem login) — `_pagina_aluno()`
Abas:
1. **Anamnese** — ficha completa com PAR-Q, exportação PDF
2. **Avaliação Postural** — upload de fotos frontais/lateral/costas
3. **Meu Progresso** — medidas corporais + peso + gráficos

### Área do Aluno (com login) — `_pagina_aluno_logado()`
Abas:
1. **🏋️ Meu Treino** — treino gerado pela professora + botões "▶ Ver execução" (YouTube embed)
2. **📅 Check-in** — registro diário + calendário visual do mês
3. **💬 Feedback** — feedback semanal (humor, dor, sono)

### Área da Professora — `_pagina_professora()`
Login: `admin` / `studio2026`

Abas principais:
1. **🏋️ Gerador de Treino** — formulário completo → PDF + envio por e-mail
2. **📋 Anamneses Recebidas** — lista + visualização + PDF
3. **📸 Avaliação Postural** — galeria + editor canvas + laudo PDF
4. **👥 Clientes** — lista de clientes → perfil individual com 7 abas:
   - 👤 Dados Pessoais (foto, edição, geração de acesso)
   - 🏋️ Treino (visualização do treino gerado)
   - 📏 Medidas e Evolução
   - 📈 Progresso (gráficos, comparativo, PDF)
   - 📅 Check-ins (calendário, gráfico por tipo de treino)
   - 💬 Feedbacks (cards coloridos + gráfico humor/dor)
   - 💰 Financeiro (contrato do cliente)
5. **🎬 Vídeos** — biblioteca de vídeos por exercício
6. **💰 Financeiro** — painel financeiro completo (ver seção abaixo)

### Módulo Financeiro
Sub-abas em "💰 Financeiro":
- **📊 Visão Geral:** 4 cards + tabela de status por cliente (🔴/🟡/🟢) + gráfico receita mensal
- **💸 Despesas:** registro + lista por mês
- **📄 Relatório Mensal:** geração de PDF com receita, inadimplentes, despesas e lucro

Navegação por session state:
- `fin_reg_slug` → tela de registro de pagamento (+ download recibo PDF)
- `fin_hist_slug` → tela de histórico de pagamentos

---

## 5. Como Gerar PDFs

```python
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle

# Registrar fonte com suporte a acentos
pdfmetrics.registerFont(TTFont('ArialPT',      'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialPT-Bold', 'C:/Windows/Fonts/arialbd.ttf'))

# Gerar em memória para download via Streamlit
buf = io.BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm)
story = [...]
doc.build(story)
pdf_bytes = buf.getvalue()

# No Streamlit:
st.download_button("Baixar PDF", data=pdf_bytes, file_name="arquivo.pdf", mime="application/pdf")
```

**Paleta ReportLab:**
```python
PRETO      = colors.HexColor('#1A1A1A')
CINZA_MEIO = colors.HexColor('#595959')
CINZA_PAR  = colors.HexColor('#F4F4F4')
CINZA_IMPAR= colors.HexColor('#EAEAEA')
```

---

## 6. Vídeos de Exercícios

Para adicionar links em `video_exercicios.py`:
1. Verificar o nome exato do exercício: `from video_exercicios import TODOS_EXERCICIOS`
2. Nomes usam `c/` (não "com"): `"Supino Reto c/ Barra"`, `"Tríceps Testa c/ Barra"`
3. Adicionar apenas em `_VIDEOS_CADASTRADOS` — nunca inventar ou supor URLs
4. `VIDEOS_EXERCICIOS` é gerado automaticamente via `.get(nome, "")`

A função `_salvar_videos()` em `app.py` só persiste entradas que diferem do base dict para não sobrescrever URLs com `""`.

---

## 7. Dependências Principais

| Biblioteca | Uso |
|---|---|
| `streamlit` | Interface web completa |
| `reportlab` | Geração de PDFs |
| `Pillow` | Processamento de imagens (fotos posturais) |
| `plotly` | Gráficos interativos (peso, medidas, receita) |
| `matplotlib` | Gráficos estáticos para PDFs de progresso |

Instalar: `pip install -r requirements.txt`

---

## 8. Erros Conhecidos e Soluções

| Erro | Causa | Solução |
|---|---|---|
| `StreamlitDuplicateElementId` | `st.plotly_chart` sem `key` único em loop | Sempre passar `key=f"nome_unico_{slug}"` |
| Acentos ausentes no PDF | Usando `Helvetica` em vez de Arial TTF | Usar `TTFont('ArialPT', 'C:/Windows/Fonts/arial.ttf')` |
| `streamlit-drawable-canvas` quebrando | Incompatível com Python 3.14+ | Não instalar nem usar esta biblioteca — o canvas postural é HTML/JS puro em `canvas_editor/index.html` |
| Vídeos não aparecem no treino do aluno | `videos_exercicios.json` com entradas `""` sobrescrevendo base dict | `_salvar_videos()` já corrigido para só salvar diferenças do base |
| Módulo `video_exercicios` não recarrega | Cache do módulo em `sys.modules` | Reiniciar o servidor Streamlit (`python -m streamlit run app.py`) |
| Streamlit não inicia via `streamlit run` diretamente | PATH do Windows | Sempre usar `python -m streamlit run app.py` |

---

## 9. O que NÃO Fazer

- **Não commitar** `config.py`, `dados_clientes/`, `videos_exercicios/` (estão no `.gitignore`)
- **Não instalar** `streamlit-drawable-canvas`
- **Não alterar** a paleta de cores preta/cinza
- **Não mudar** o formato de datas para padrão diferente de `DD/MM/AAAA`
- **Não criar** funcionalidade duplicada (ex: segundo formulário de anamnese)
- **Não salvar** entradas com `""` no `videos_exercicios.json`
- **Não usar** `Helvetica` como fonte principal em PDFs novos
- **Não commitar** sem descrição clara em português
- **Não fazer** `git push --force` para o master
