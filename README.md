# Gerador de Plano de Treino em PDF

Gera fichas de treino personalizadas em PDF, prontas para entregar ao cliente.

## Pré-requisitos

- Python 3.8 ou superior

## Instalação

```bash
pip install reportlab
```

## Como rodar — Interface Web (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abrirá automaticamente no navegador em `http://localhost:8501`.  
Preencha o formulário e clique em **Gerar Treino em PDF** para baixar a ficha.

## Como rodar — Terminal (CLI legado)

```bash
cd treino-pdf
python main.py
```

O script fará perguntas no terminal e, ao final, salvará um arquivo `.pdf`
na mesma pasta com o nome do cliente e a data (ex: `joao_silva_2026-06-24.pdf`).

## O que o PDF contém

| Seção | Descrição |
|---|---|
| Cabeçalho | Nome do cliente, objetivo, data de geração |
| Perfil do cliente | Todos os dados coletados + IMC calculado |
| Plano de treino | Tabelas por treino (A/B/C/D) com exercícios, séries, reps e método |
| Cardio / aeróbico | Protocolo específico para o objetivo |
| Progressão de carga | Regras conforme o nível de experiência |
| Observações gerais | Aquecimento, intervalos, nutrição, sono etc. |

## Divisões selecionadas automaticamente

| Frequência | Nível | Divisão |
|---|---|---|
| 2x/semana | qualquer | A/B |
| 3x/semana | iniciante | Full Body |
| 3x/semana | intermediário / avançado | A/B/C |
| 4x ou mais | qualquer | A/B/C/D |

## Estrutura de arquivos

```
treino-pdf/
├── app.py          — interface web Streamlit
├── main.py         — script CLI legado (entrada via terminal)
├── gerar_pdf.py    — geração e layout do PDF com ReportLab
├── exercicios.py   — banco de exercícios, cardio, progressão e observações
├── requirements.txt
└── README.md       — este arquivo
```

## Personalizando

- **Nome da consultoria**: edite a variável `NOME_CONSULTORIA` em `gerar_pdf.py`.
- **Exercícios**: adicione ou substitua entradas no dicionário `EXERCICIOS` em `exercicios.py`.
- **Cores**: ajuste as constantes no topo de `gerar_pdf.py` (`PRETO`, `CINZA_PAR` etc.).
