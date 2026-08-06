# Changelog

## 0.5.0 — Banco de Questões

### Adicionado

- migração automática do SQLite sem perda dos dados existentes;
- filtros por concurso, banca, matéria, assunto e dificuldade;
- pesquisa por texto no enunciado, explicação, assunto e tags;
- questões favoritas;
- caderno de erros com status pendente/revisada;
- histórico de tentativas por questão;
- estatísticas gerais e por matéria;
- suporte a alternativa E e metadados de questões;
- índices no banco para melhorar as consultas.

### Alterado

- lógica da página de questões removida do `app.py` e organizada em `services/questions.py`;
- documentação atualizada para a versão 0.5.
