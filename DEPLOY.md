# Publicação do ConcursoAI no Streamlit Community Cloud

## 1. Pré-requisitos

- repositório atualizado no GitHub;
- arquivo `requirements.txt` na raiz;
- arquivo principal `app.py`;
- chave da API mantida fora do GitHub.

## 2. Criar o aplicativo

1. Acesse o Streamlit Community Cloud.
2. Escolha **Create app**.
3. Selecione o repositório `jhonyhv/concurso-ai`.
4. Escolha a branch desejada, preferencialmente `main`.
5. Informe `app.py` como arquivo principal.

## 3. Configurar a IA

Nas configurações avançadas do aplicativo, abra **Secrets** e adicione:

```toml
GROQ_API_KEY = "sua-chave"
GROQ_MODEL = "openai/gpt-oss-20b"
```

A chave não deve ser adicionada ao código, ao banco de dados nem ao GitHub.

## 4. Persistência dos dados

O ConcursoAI usa SQLite. Em hospedagens com sistema de arquivos temporário, alterações locais podem ser perdidas após reinicializações ou novos deploys.

Use a tela **Configurações > Backup** para baixar regularmente o banco. Para uso multiusuário ou persistência permanente, a próxima evolução recomendada é migrar os dados para PostgreSQL ou Supabase.

## 5. Atualizações

Depois de publicar, novos commits na branch configurada são aplicados automaticamente pelo Streamlit Community Cloud.
