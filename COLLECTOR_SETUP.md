# Configuração do coletor e da revisão

## 1. Criar as tabelas no Supabase

Abra **SQL Editor**, cole o conteúdo de `supabase/schema.sql` e execute.

## 2. Secrets do Streamlit Cloud

Em **App settings > Secrets**, configure:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
SUPABASE_SERVICE_ROLE_KEY = "sua-chave-secreta"
ADMIN_PASSWORD = "uma-senha-forte-e-exclusiva"
```

- `SUPABASE_ANON_KEY` é usada para baixar somente questões publicadas.
- `SUPABASE_SERVICE_ROLE_KEY` é usada no servidor para aprovar, editar e rejeitar questões.
- `ADMIN_PASSWORD` protege a tela administrativa.
- Nunca publique esses valores no GitHub, em prints ou mensagens.

A chave secreta fica armazenada nos Secrets privados do Streamlit Cloud e nunca é enviada ao navegador.

## 3. Secrets do GitHub Actions

Em **Settings > Secrets and variables > Actions**, adicione:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GROQ_API_KEY`
- `GROQ_MODEL` com o valor `openai/gpt-oss-20b`

## 4. Executar o coletor

Abra **Actions > Coletar questões > Run workflow**.

As questões inéditas passam a ser gravadas com o status `pending_review`. Uma questão já aprovada ou rejeitada não volta para a fila em coletas futuras.

## 5. Revisar e publicar

No aplicativo:

1. abra **Coletor automático**;
2. entre na aba **Revisão administrativa**;
3. informe a senha definida em `ADMIN_PASSWORD`;
4. revise enunciado, alternativas, gabarito e explicação;
5. clique em **Aprovar e publicar** ou **Rejeitar**;
6. abra a aba **Catálogo** e clique em **Sincronizar catálogo agora**.

Somente itens com status `published` aparecem para estudantes e simulados.

## Fontes oficiais do Banco do Brasil

A fonte principal é o índice oficial da Fundação Cesgranrio da Seleção Externa Banco do Brasil 2022/001:

```text
https://www.cesgranrio.org.br/concurso/banco-do-brasil-bb-01-2022/
```

O coletor seleciona automaticamente:

- Edital nº 01 — 2022/001;
- Prova A — Agente Comercial — Gabarito 1;
- Prova B — Agente Comercial — Gabarito 1;
- Prova C — Agente Comercial — Gabarito 1;
- gabaritos oficiais ou alterados das provas A, B e C.

Documentos de Agente de Tecnologia, páginas de convocação, posse, notícias e versões duplicadas das provas são ignorados.

Na geração, a IA recebe um edital e até duas provas aprovadas pelo filtro de qualidade. As questões resultantes são inéditas e permanecem pendentes até a revisão administrativa.

## Funcionamento diário

O workflow roda diariamente às 06:17 UTC. Ele:

1. consulta as fontes oficiais configuradas em `collector/config.py`;
2. encontra páginas, editais, provas e gabaritos;
3. extrai texto de HTML e PDF;
4. gera questões inéditas com a IA;
5. valida alternativas, resposta e duplicidade;
6. envia somente questões novas para a fila de revisão;
7. preserva decisões anteriores de aprovação ou rejeição.

## Adicionar novos concursos

Inclua outra entrada `SourceConfig` em `collector/config.py`.
