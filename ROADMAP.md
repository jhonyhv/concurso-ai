# ConcursoAI — Roadmap acelerado

## Objetivo
Transformar o projeto em uma plataforma de preparação para o Banco do Brasil com catálogo confiável, revisão administrativa, simulados, análise de desempenho e experiência visual consistente.

## Fase 1 — Base visual v1.2
Status: em implementação

- nova identidade visual azul/amarelo inspirada no contexto bancário sem copiar identidade proprietária;
- sidebar mais limpa e agrupada por tarefa;
- cabeçalho compacto com contexto da página e versão;
- painel de foco no Dashboard com sequência, acertos, estudo e revisões;
- cartões, abas, botões e formulários com hierarquia visual consistente;
- responsividade desktop/mobile preservada;
- tema escuro mantido.

## Fase 2 — Arquitetura de fontes confiáveis
Status: próximo

Princípio central:

- edital = define matérias, tópicos, cargo, pesos e escopo;
- fonte oficial de conteúdo = fundamenta conceitos e regras;
- prova oficial = calibra linguagem, dificuldade e estilo;
- IA = elabora questão inédita, nunca inventa a fonte.

Fontes-alvo por domínio:

- Banco Central do Brasil: SFN, política monetária, SELIC, PIX, Open Finance, produtos e regulação bancária;
- CVM: mercado de capitais e valores mobiliários;
- Planalto / legislação oficial: CDC, LGPD e normas legais cobradas;
- ANPD: proteção de dados pessoais;
- CERT.br / NIC.br: fundamentos de segurança da informação quando aplicáveis;
- edital BB/Cesgranrio: matriz do conteúdo programático;
- provas oficiais: padrão de cobrança da banca.

## Fase 3 — Validação automática de questões
Status: próximo

Antes de uma questão entrar em `pending_review`:

1. estrutura A–E válida;
2. apenas uma alternativa correta;
3. enunciado e explicação mínimos;
4. verificação de suporte na fonte;
5. bloqueio de números, taxas, tarifas e regras não sustentadas;
6. validação matemática determinística para questões numéricas;
7. bloqueio de questões conceituais geradas somente a partir do edital;
8. deduplicação semântica e por hash;
9. score de qualidade e motivo de rejeição automática.

## Fase 4 — Catálogo de produção

- fila `pending_review` somente com itens aprovados pelos validadores automáticos;
- painel mostra fonte de conteúdo e fonte de edital separadamente;
- filtros por matéria, assunto, dificuldade e qualidade;
- ações em lote para aprovar/rejeitar;
- histórico de alterações da questão;
- indicador de cobertura do edital por tópico.

## Fase 5 — Experiência de estudo

- plano de estudo diário automático;
- trilha por matéria e tópico;
- simulados por banca, matéria e nível;
- caderno de erros inteligente;
- revisão espaçada ligada aos erros;
- Professor IA usando desempenho real do aluno;
- recomendações de próxima ação no Dashboard.

## Fase 6 — Analytics e produto

- mapa de domínio do edital;
- evolução semanal e mensal;
- taxa de acerto por tópico;
- tempo por questão;
- risco de esquecimento;
- previsão de cobertura do edital;
- score de prontidão para a prova;
- exportação de relatórios.

## Ordem de execução recomendada

1. Visual v1.2.
2. Registry de fontes oficiais de conteúdo.
3. Validador matemático e de grounding.
4. Coleta por tópicos do edital.
5. Painel de revisão v2 com fonte e score.
6. Cobertura do edital.
7. Plano de estudo inteligente.
8. Simulados adaptativos.
9. Analytics avançado.
10. Polimento mobile e publicação de portfólio.
