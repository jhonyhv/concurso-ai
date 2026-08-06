# ConcursoAI — Banco do Brasil Edition

Plataforma pessoal de preparação para concursos, desenvolvida em Python, Streamlit e SQLite.

## Versão 0.9

A v0.9 consolida os recursos anteriores e adiciona acabamento visual, IA online opcional, tema escuro, backup e preparação para publicação.

### Recursos principais

- dashboard responsivo com metas, sequência, evolução e calendário;
- banco de questões com filtros, favoritos e caderno de erros;
- simulados com histórico e aproveitamento;
- flashcards e revisão espaçada;
- metas diárias, calendário e registro de estudos;
- estatísticas e diagnóstico por matéria;
- Professor IA em modo local ou online;
- backup e restauração do banco SQLite;
- tema claro e escuro;
- arquivos preparados para Streamlit Community Cloud.

## Professor IA online

A integração online usa a API Groq e mantém a chave fora do código e do banco.

Crie `.streamlit/secrets.toml` com:

```toml
GROQ_API_KEY = "sua-chave"
GROQ_MODEL = "openai/gpt-oss-20b"
```

Sem a chave, o Professor IA continua funcionando no modo local.

## Instalação no Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Também é possível executar `run_windows.bat`.

## Atualização preservando dados

Use o ZIP de atualização e extraia sobre a pasta atual. Ele não contém `.git` nem `data/bb_master.db`.

Na primeira execução, o sistema realiza a migração do SQLite automaticamente.

## Publicação

Consulte [`DEPLOY.md`](DEPLOY.md). Antes de publicar, considere que o SQLite pode não oferecer persistência permanente em hospedagens com disco temporário. Faça backups regulares pela tela **Configurações > Backup**.
