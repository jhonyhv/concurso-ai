from __future__ import annotations

import streamlit as st

from database.database import load_df
from database.remote_sync import sync_remote_questions


def render_collector_page() -> None:
    st.markdown("## 🌐 Coletor automático")
    st.caption("As questões publicadas pelo robô são sincronizadas do Supabase sem ação do estudante.")

    if st.button("Sincronizar catálogo agora", type="primary", use_container_width=True):
        with st.spinner("Sincronizando questões publicadas..."):
            try:
                result = sync_remote_questions(force=True)
                if result["configured"]:
                    st.success(f"{result['synced']} questão(ões) sincronizada(s).")
                else:
                    st.warning("Configure SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets.")
            except Exception as exc:
                st.error(f"Falha na sincronização: {exc}")

    stats = load_df(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN source_kind = 'ai_original' THEN 1 ELSE 0 END) AS generated,
               SUM(CASE WHEN source_kind = 'official' THEN 1 ELSE 0 END) AS official,
               MAX(imported_at) AS last_import
          FROM questions
         WHERE source_uid IS NOT NULL AND source_uid <> ''
        """
    ).iloc[0]
    cols = st.columns(4)
    cols[0].metric("Catálogo automático", int(stats["total"] or 0))
    cols[1].metric("Inéditas por IA", int(stats["generated"] or 0))
    cols[2].metric("Oficiais", int(stats["official"] or 0))
    cols[3].metric("Última sincronização", str(stats["last_import"] or "—")[:16])

    recent = load_df(
        """
        SELECT concurso AS Concurso, banca AS Banca, subject AS Matéria,
               assunto AS Assunto, source_kind AS Tipo, confidence AS Confiança,
               source_url AS Fonte
          FROM questions
         WHERE source_uid IS NOT NULL AND source_uid <> ''
         ORDER BY imported_at DESC, id DESC
         LIMIT 50
        """
    )
    if recent.empty:
        st.info("O catálogo remoto ainda não possui questões sincronizadas.")
    else:
        st.dataframe(recent, use_container_width=True, hide_index=True)

    st.info(
        "O GitHub Actions executa a coleta diariamente. Documentos são descobertos em fontes oficiais, "
        "classificados e convertidos em questões inéditas. Somente itens validados são publicados."
    )
