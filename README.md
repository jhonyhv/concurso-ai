# ConcursoAI — Banco do Brasil

Plataforma pessoal de preparação para o concurso do Banco do Brasil, desenvolvida em Python, Streamlit e SQLite.

## Recursos da versão 0.5

- dashboard de desempenho e tempo de estudo;
- plano semanal proporcional ao peso das matérias;
- banco de questões com filtros por concurso, banca, matéria, assunto e dificuldade;
- pesquisa por texto;
- questões favoritas;
- caderno de erros com controle de revisão;
- histórico e estatísticas por matéria;
- migração automática do banco SQLite sem apagar os dados existentes;
- registro de sessões de estudo;
- conteúdo programático inicial.

## Instalação no Windows

1. Instale o Python 3.11 ou superior.
2. Extraia a pasta do projeto.
3. Abra o PowerShell dentro da pasta.
4. Execute:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá em `http://localhost:8501`.

## Banco de dados

O banco fica em `data/bb_master.db`. Na primeira execução da versão 0.5, o aplicativo adiciona automaticamente as novas colunas e tabelas necessárias, preservando questões, tentativas e sessões já registradas.

## Próximas versões

- professor com IA;
- flashcards e revisão espaçada;
- simulados completos com cronômetro;
- importação de questões por CSV;
- autenticação e sincronização online.

## Aviso

O conteúdo programático incluído é apenas uma base inicial. O edital oficial vigente deve sempre ser a fonte principal.
