# Changelog

## 1.0.0-beta
- Coletor automático agendado por GitHub Actions.
- Descoberta de documentos em fontes oficiais.
- Extração de HTML/PDF e geração de questões inéditas por IA.
- Catálogo central no Supabase e sincronização automática no aplicativo.
- Deduplicação por hash e publicação apenas de itens validados.
- Painel de acompanhamento do catálogo automático.


## v0.9.0 — 06/08/2026

### Professor IA
- integração opcional com a API Groq;
- seleção entre modo automático, online e local;
- contexto baseado em desempenho, assuntos fracos e caderno de erros;
- formatos de resposta para explicação, plano, revisão e resposta objetiva;
- teste de conexão e histórico técnico de uso;
- fallback automático para o modo local.

### Interface
- tema escuro funcional;
- cabeçalho com página atual, data em português e revisões pendentes;
- indicador de versão e estado;
- refinamentos de responsividade, botões, chat e cartões.

### Segurança e dados
- chave da IA armazenada somente em segredo ou variável de ambiente;
- download e restauração de backup SQLite;
- validação de integridade antes da restauração;
- novas tabelas e migrações sem apagar dados existentes.

### Deploy
- configuração do Streamlit;
- modelo de arquivo de segredos;
- guia `DEPLOY.md` para Streamlit Community Cloud;
- aviso sobre persistência do SQLite em ambientes temporários.

## v0.8.0 — 06/08/2026

- dashboard e menu completo;
- metas, calendário e revisão espaçada;
- flashcards, simulados e Professor IA local;
- estatísticas, desempenho e configurações;
- compatibilidade com a base v0.5.
