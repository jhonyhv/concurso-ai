# Configuração do coletor automático

## 1. Criar as tabelas no Supabase

Abra **SQL Editor**, cole o conteúdo de `supabase/schema.sql` e execute.

## 2. Secrets do Streamlit Cloud

Adicione somente as credenciais de leitura pública:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-anon"
```

Nunca coloque a chave `service_role` no Streamlit.

## 3. Secrets do GitHub Actions

Em **Settings > Secrets and variables > Actions**, adicione:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GROQ_API_KEY`
- `GROQ_MODEL` com o valor `openai/gpt-oss-20b`

A chave `service_role` fica somente no GitHub Actions, responsável pela gravação no catálogo.

## 4. Primeira execução

Abra **Actions > Coletar questões > Run workflow**.

Depois, no aplicativo, abra **Coletor automático** e clique em **Sincronizar catálogo agora**.

## Funcionamento diário

O workflow roda diariamente às 06:17 UTC. Ele:

1. consulta as fontes oficiais configuradas em `collector/config.py`;
2. encontra páginas, editais, provas e gabaritos;
3. extrai texto de HTML e PDF;
4. gera questões inéditas com a IA sem reproduzir questões protegidas;
5. valida alternativas, resposta e duplicidade;
6. publica no Supabase;
7. o Streamlit sincroniza automaticamente o catálogo.

## Adicionar novos concursos

Inclua outra entrada `SourceConfig` em `collector/config.py`. O estudante não precisa fazer nada.
