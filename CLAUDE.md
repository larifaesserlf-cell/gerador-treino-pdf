# CLAUDE.md — Contexto técnico para o Claude Code

Este arquivo documenta a arquitetura e convenções do projeto para uso em futuras sessões do Claude Code.

## Visão geral

App Streamlit single-file (`app.py`) com roteamento por `st.session_state['area']`:

| Valor da `area` | Tela |
|---|---|
| `None` | Home (escolha de área) |
| `'aluno'` | Área do aluno sem login (Anamnese, Postural, Progresso) |
| `'aluno_login'` | Formulário de login do aluno |
| `'aluno_logado'` | Área do aluno logado (Meu Treino, Check-in, Feedback) |
| `'professora'` | Área da professora (autenticada) |

O roteamento principal fica nas últimas linhas de `app.py`.

## Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Toda a UI, roteamento, lógica de negócio, leitura/escrita de JSON |
| `exercicios.py` | Dicts `EXERCICIOS`, `DESCRICOES_TREINO`, `CARDIO`, `PROGRESSAO`, `PERIODIZACAO`, `OBSERVACOES` |
| `video_exercicios.py` | Dict `VIDEOS_EXERCICIOS` (nome → URL YouTube). Apenas links confirmados. `_VIDEOS_CADASTRADOS` é o dict de fábrica; `videos_exercicios.json` armazena overrides em runtime |
| `gerar_pdf.py` | Plano de treino em PDF (ReportLab) |
| `gerar_pdf_anamnese.py` | Ficha de anamnese em PDF |
| `gerar_pdf_postural.py` | Laudo de avaliação postural em PDF |
| `gerar_pdf_progresso.py` | Relatório de progresso (peso + medidas) em PDF |
| `gerar_pdf_financeiro.py` | Recibo de pagamento e relatório financeiro mensal em PDF |
| `config.py` | `EMAIL_REMETENTE`, `EMAIL_SENHA` — **nunca commitar** (no .gitignore) |

## Dados persistidos

Todos os dados de clientes ficam em `dados_clientes/` (no .gitignore — nunca versionado).

| Arquivo | Conteúdo |
|---|---|
| `cadastro_[slug].json` | Nome, nascimento, WhatsApp, e-mail, foto |
| `anamnese_[slug]_[ts].json` | Ficha de anamnese completa |
| `medidas_[slug].json` | Lista de registros de medidas corporais |
| `peso_[slug].json` | Lista de registros de peso isolado |
| `treino_[slug].json` | Último treino gerado (dados + exercícios + descrições) |
| `checkins_[slug].json` | Lista de check-ins diários |
| `feedback_[slug].json` | Lista de feedbacks semanais |
| `acesso_[slug].json` | Usuário e senha do aluno |
| `financeiro_[slug].json` | Contrato: tipo, valor, datas, status |
| `pagamentos_[slug].json` | Lista de pagamentos registrados |
| `despesas.json` | Lista global de despesas da consultoria |
| `videos_exercicios.json` | Overrides de vídeos salvos via painel da professora |

O slug é gerado por `_slug(nome)`: ASCII lowercase, underscores, sem acentos.

## Convenções

- **Identidade visual:** sidebar `#1A1A1A` (escura), fundo principal `#FFFFFF`, destaque `#7C4DFF` (roxo), texto `#1A1A1A`, secundário `#666666`, bordas `#E8E8E8`, cards `#FAFAFA`
- **Datas:** exibidas sempre como `DD/MM/AAAA`; armazenadas internamente em ISO `YYYY-MM-DD`
- **PDFs:** ReportLab com fonte Arial TTF (fallback Helvetica). Cabeçalho `#1A1A1A`, títulos de seção `#7C4DFF`, linhas `#FAFAFA`/`#FFFFFF`, bordas `#E8E8E8`
- **Vídeos:** `_carregar_videos()` em `app.py` faz merge `{**_base, **runtime}`. `_salvar_videos()` só persiste entradas que diferem do base para não sobrescrever com `""`
- **Nomes de exercícios:** usam `c/` (não "com"), ex: `"Supino Reto c/ Barra"` — verificar em `TODOS_EXERCICIOS` antes de cadastrar
- **Plotly:** já importado condicionalmente (`_HAS_PLOTLY`). Usar `go.Figure()` e `st.plotly_chart(..., key=...)`
- **Formulários:** usar `st.form` + `st.form_submit_button` para evitar reruns parciais
- **Navegação intra-tab:** session state + `st.rerun()`. Padrão: `if st.session_state.get('chave'): _funcao(); return`

## Funcionalidades implementadas

### Área do Aluno (sem login)
- Ficha de anamnese completa com PAR-Q e exportação PDF
- Upload e submissão de fotos posturais
- Registro de medidas corporais e peso com gráficos
- Geração de PDF de progresso

### Área do Aluno (com login)
- Login por usuário/senha gerados pela professora
- Visualização do treino atual com botões "▶ Ver execução" (vídeos YouTube embed)
- Check-in diário (treinou / descansou) com calendário visual do mês
- Feedback semanal (humor, dor muscular, dor articular, sono, observações)

### Área da Professora
- **Gerador de Treino:** formulário completo → PDF download + envio por e-mail
- **Anamneses Recebidas:** lista, visualização detalhada, PDF
- **Avaliação Postural:** upload de fotos por cliente, editor de marcação de pontos (canvas HTML), laudo PDF
- **Gestão de Clientes:** lista de clientes, perfil individual com 7 abas:
  - Dados Pessoais (foto, edição, criação de acesso)
  - Treino (visualização do treino gerado)
  - Medidas e Evolução (registro e tabela)
  - Progresso (gráficos plotly, comparativo, PDF)
  - Check-ins (calendário, gráfico de treinos por tipo)
  - Feedbacks (cards com cor por alerta, gráfico humor/dor)
  - **Financeiro** (contrato, status de pagamento)
- **Biblioteca de Vídeos:** adicionar/remover URLs YouTube por exercício
- **Módulo Financeiro** (aba principal):
  - Visão geral: cards de receita + tabela de status por cliente + gráfico mensal
  - Registrar pagamento + download de recibo PDF
  - Histórico de pagamentos por cliente
  - Gestão de despesas por categoria
  - Relatório mensal PDF

## Deploy

```
git push origin master
```
O Streamlit Community Cloud detecta o push e reimplanta automaticamente.
App publicado: https://2rve8kptjdtf3tcvekxhc7.streamlit.app

## Pendências / melhorias futuras

- Adicionar mais vídeos ao `video_exercicios.py` (a professora fornece os links manualmente)
- Notificações de vencimento de contrato por WhatsApp/e-mail
- Exportação de dados de clientes em CSV
- Múltiplos períodos de treino por cliente (histórico de planos)
- App mobile-first (layout responsivo)
