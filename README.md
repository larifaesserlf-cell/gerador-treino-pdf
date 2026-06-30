# Studio Personal Training — Sistema de Gestão

Sistema web completo para personal trainers gerenciarem clientes, gerar planos de treino em PDF, acompanhar evolução física e controlar o financeiro da consultoria.

**App publicado:** https://2rve8kptjdtf3tcvekxhc7.streamlit.app

---

## Funcionalidades

### Área da Professora
- **Gerador de treino em PDF** — planos personalizados por sexo, objetivo, nível, divisão e periodização
- **Anamneses recebidas** — visualização e exportação em PDF das fichas dos alunos
- **Avaliação postural** — upload de fotos com marcação de pontos e laudos em PDF
- **Gestão de clientes** — cadastros, medidas corporais, evolução de peso, check-ins e feedbacks
- **Biblioteca de vídeos** — associa vídeos do YouTube a cada exercício do banco
- **Módulo financeiro** — contratos, registro de pagamentos, recibos PDF, despesas e relatório mensal

### Área do Aluno (com login)
- **Meu Treino** — visualização do treino gerado pela professora com vídeos de execução
- **Check-in** — registro diário de treino com calendário visual
- **Feedback semanal** — humor, dor muscular/articular, sono e observações

### Área do Aluno (sem login)
- **Anamnese** — ficha de anamnese completa com PAR-Q
- **Avaliação Postural** — upload de fotos posturais
- **Meu Progresso** — registro de medidas e peso com gráficos de evolução

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Rodar localmente

```bash
python -m streamlit run app.py
```

Acesse em: http://localhost:8501

---

## Acesso

| Área | Usuário | Senha |
|---|---|---|
| Professora | `admin` | `studio2026` |
| Aluno (exemplo) | `larissa` | `0000larissa` |

> As credenciais dos alunos são geradas automaticamente pela professora no perfil de cada cliente.

---

## Estrutura de pastas

```
treino-pdf/
├── app.py                    — aplicação principal (toda a lógica de UI e roteamento)
├── exercicios.py             — banco de exercícios, cardio, progressão e observações
├── video_exercicios.py       — mapeamento exercício → URL do YouTube
├── videos_exercicios.json    — overrides de vídeos salvos pela professora em tempo de execução
├── gerar_pdf.py              — geração do plano de treino em PDF (ReportLab)
├── gerar_pdf_anamnese.py     — geração da ficha de anamnese em PDF
├── gerar_pdf_postural.py     — geração do laudo postural em PDF
├── gerar_pdf_progresso.py    — geração do relatório de progresso em PDF
├── gerar_pdf_financeiro.py   — geração de recibos e relatório financeiro mensal em PDF
├── config.py                 — credenciais de e-mail (NÃO versionado — ver .gitignore)
├── requirements.txt          — dependências Python
├── canvas_editor/
│   └── index.html            — editor de marcação postural (HTML/JS standalone)
├── dados_clientes/           — dados dos alunos (NÃO versionado — ver .gitignore)
│   ├── cadastro_[slug].json
│   ├── anamnese_[slug]_[data].json
│   ├── medidas_[slug].json
│   ├── peso_[slug].json
│   ├── treino_[slug].json
│   ├── checkins_[slug].json
│   ├── feedback_[slug].json
│   ├── acesso_[slug].json
│   ├── financeiro_[slug].json
│   ├── pagamentos_[slug].json
│   └── despesas.json
└── README.md
```

---

## Deploy

O app está hospedado no **Streamlit Community Cloud**.  
Cada `git push origin master` atualiza o app publicado automaticamente em alguns minutos.
