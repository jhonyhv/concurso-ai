# Changelog

## 1.2.0-beta
- Nova camada visual isolada em `assets/refresh.css` para permitir evolução rápida sem reescrever o tema-base.
- Sidebar reorganizada por Estudos, Inteligência, Análises e Gestão.
- Identidade visual refinada em azul e amarelo, com marca tipográfica do ConcursoAI.
- Cabeçalho mais compacto com contexto da página, data, versão e revisões pendentes.
- Novo Painel de Foco no Dashboard com sequência, acertos, tempo de estudo e revisões do dia.
- Cartões, abas, botões, formulários e containers com hierarquia, sombras e espaçamento mais consistentes.
- Responsividade preservada e compatibilidade mantida com o tema escuro.
- Adicionado `ROADMAP.md` com a sequência acelerada de evolução do produto e da arquitetura de fontes.

## 1.1.6-beta
- Migração da geração da Groq de `json_object` para Structured Outputs com `json_schema` e `strict: true`.
- Esquema rígido para enunciado, alternativas A-E, gabarito, explicação, matéria, assunto, dificuldade, tags, cargo e ano.
- Nova tentativa automática quando a API devolver `json_validate_failed` ou outro erro transitório de geração estruturada.
- Segundo lote reduzido para uma única questão com contexto menor.
- Regras reforçadas para impedir que valores hipotéticos sejam apresentados como tarifas, produtos, benefícios ou condições do Banco do Brasil.
- Números fictícios ficam permitidos somente em problemas explicitamente hipotéticos de Matemática, Matemática Financeira, Probabilidade ou Estatística.

## 1.1.5-beta
- Ativação do modo JSON nativo da Groq com `response_format=json_object`.
- Resposta padronizada no formato `{ "questions": [...] }`.
- Validação explícita de conteúdo vazio, resposta truncada e `finish_reason=length`.
- Nova tentativa automática com lote e contexto menores quando o JSON vier inválido ou incompleto.
- Compatibilidade mantida com respostas antigas em formato de array.
- Uso de raciocínio oculto e esforço baixo para reduzir consumo de tokens na geração estruturada.

## 1.1.4-beta
- Seleção automática de trechos relevantes do conteúdo programático do edital.
- Contexto enviado à Groq limitado a 7.000 caracteres.
- Geração limitada a até três questões por requisição para respeitar o TPM disponível.
- Limite de saída reduzido para 2.400 tokens.
- Nova tentativa automática com contexto e saída menores quando a Groq responder HTTP 413.
- Logs mostram quantidade de questões, tamanho do trecho e limite de saída enviados à IA.

## 1.1.3-beta
- Fonte principal alterada para a página oficial do concurso no Banco do Brasil.
- Uso direto do PDF oficial do Edital nº 01 hospedado em `bb.com.br`.
- Remoção da dependência da página da Cesgranrio, que retornava HTTP 403 no GitHub Actions.
- O workflow agora falha quando nenhuma fonte é extraída ou nenhuma questão é gerada.
- Logs distinguem questões geradas de questões realmente novas inseridas no catálogo.

## 1.1.2-beta
- Fonte principal alterada para o índice oficial da Cesgranrio do Banco do Brasil 2022/001.
- Descoberta do Edital nº 01, provas A/B/C e gabaritos oficiais de Agente Comercial.
- Exclusão automática dos documentos de Agente de Tecnologia e páginas administrativas.
- Seleção de apenas um caderno por prova para evitar versões duplicadas com alternativas reordenadas.
- Preferência pelos gabaritos alterados/finais quando disponíveis.
- Geração baseada em um edital e até duas provas oficiais para combinar conteúdo programático e padrão da banca.

## 1.1.1-beta
- Bloqueio de páginas de convocação, posse, transparência, notícias e outras fontes inadequadas.
- Geração restrita a editais, conteúdos programáticos, provas e normativos com texto suficiente.
- Remoção do fallback que combinava páginas curtas e irrelevantes.
- Validação de tamanho, confiança, diversidade textual e sinais de conteúdo de concurso.
- Instruções mais rigorosas para impedir fatos, valores, tarifas e regras não sustentados pela fonte.
- Indicadores de versão do cabeçalho e da barra lateral sincronizados com o arquivo `VERSION`.

## 1.1.0-beta
- Novas questões geradas pela IA entram como `pending_review`.
- Painel administrativo protegido por senha no Streamlit.
- Edição de matéria, assunto, alternativas, gabarito, explicação, tags, cargo e ano.
- Ações para aprovar, publicar ou rejeitar questões.
- Contadores de pendentes, publicadas e rejeitadas.
- Preservação das decisões de revisão em coletas futuras.
- Remoção local de questões que deixarem de estar publicadas.
- Compatibilidade com as novas chaves `sb_publishable_` e `sb_secret_` do Supabase.
- Validação de sintaxe Python antes da execução do coletor.

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
- seleção entre modo automático e local;
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
