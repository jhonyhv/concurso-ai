from __future__ import annotations

from collector.models import SourceConfig

SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        source_id="bb_concurso",
        name="Concurso Banco do Brasil",
        organization="Banco do Brasil",
        bank="Cesgranrio",
        contest="Banco do Brasil",
        page_url="https://www.bb.com.br/site/concurso-bb/convocacao-e-posse-de-novos-funcionarios/",
        allowed_domains=("bb.com.br", "www.bb.com.br", "cesgranrio.org.br", "www.cesgranrio.org.br"),
        mode="generate_original",
        license_name="fonte_oficial_sem_licenca_de_reproducao_confirmada",
        max_documents=8,
        default_subject="Conhecimentos Bancários",
        style_notes=(
            "Questões inéditas para Agente Comercial do Banco do Brasil, estilo Cesgranrio, "
            "com enunciado contextualizado, cinco alternativas plausíveis e apenas uma correta."
        ),
    ),
    SourceConfig(
        source_id="cnu_oficial",
        name="Concurso Público Nacional Unificado",
        organization="Ministério da Gestão e da Inovação em Serviços Públicos",
        bank="Fundação Cesgranrio",
        contest="Concurso Público Nacional Unificado",
        page_url="https://www.gov.br/gestao/pt-br/concursonacional/caderno-de-provas-e-gabaritos",
        allowed_domains=("gov.br", "www.gov.br"),
        mode="generate_original",
        license_name="CC-BY-ND-3.0",
        enabled=False,
        max_documents=12,
        default_subject="Conhecimentos Gerais",
        style_notes="Questões inéditas no padrão de concursos federais, com cinco alternativas.",
    ),
)


def enabled_sources() -> list[SourceConfig]:
    return [source for source in SOURCES if source.enabled]
