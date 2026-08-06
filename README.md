# ConcursoAI — Banco do Brasil Edition

Plataforma pessoal de preparação para o concurso do Banco do Brasil, desenvolvida em Python, Streamlit e SQLite.

## Versão 0.8 completa

Esta entrega reúne as sprints **v0.6, v0.7 e v0.8**.

### v0.6 — Interface e dashboard

- dashboard inspirado na referência visual enviada;
- menu lateral organizado por Estudos, IA, Análises e Outros;
- cards de sequência, questões, taxa de acertos e tempo de estudo;
- evolução de acertos nos últimos sete dias;
- calendário de estudos em formato heatmap;
- desempenho por matéria;
- meta diária e próximas revisões.

### v0.7 — Metas e revisão espaçada

- metas diárias configuráveis;
- calendário com intensidade de estudo;
- agenda de revisões;
- algoritmo de revisão espaçada;
- integração automática com o caderno de erros;
- histórico de estudos e revisões.

### v0.8 — Flashcards, simulados e Professor IA

- criação e biblioteca de flashcards;
- cartões gerados a partir do caderno de erros;
- revisão de flashcards com cálculo da próxima data;
- simulados por matéria e quantidade de questões;
- histórico de simulados;
- Professor IA em modo local, conectado ao banco de questões e ao desempenho;
- estatísticas e diagnóstico de prioridades.

## Recursos preservados da v0.5

- banco de questões com filtros avançados;
- pesquisa por texto;
- favoritos;
- caderno de erros;
- histórico de respostas;
- migração automática do SQLite sem apagar os dados existentes.

## Instalação no Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Também é possível executar `run_windows.bat`.

## Atualização preservando seus dados

Use o ZIP de atualização e extraia sobre a pasta atual. Ele não contém a pasta `.git` nem o arquivo `data/bb_master.db`.

Na primeira execução, o sistema cria automaticamente as novas tabelas necessárias.

## Observação sobre o Professor IA

O tutor desta versão trabalha em modo local. Ele usa questões, explicações, erros, estatísticas e matérias armazenados no seu próprio banco, sem enviar dados para serviços externos.
