from __future__ import annotations

import hmac
from typing import Any

import streamlit as st

from database.database import load_df
from database.remote_sync import sync_remote_questions
from services.supabase_review import (
    admin_password,
    count_questions,
    fetch_questions,
    review_admin_configured,
    update_question,
)

STATUS_LABELS = {
    "pending_review": "Pendentes",
    "published": "Publicadas",
    "rejected": "Rejeitadas",
}
DIFFICULTIES = ["Fácil", "Média", "Difícil"]


def _render_catalog_tab() -> None:
    st.caption("Somente questões aprovadas e publicadas são sincronizadas para estudantes e simulados.")

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
    cols[0].metric("Catálogo publicado", int(stats["total"] or 0))
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
        st.info("O catálogo remoto ainda não possui questões publicadas sincronizadas.")
    else:
        st.dataframe(recent, use_container_width=True, hide_index=True)


def _authenticate_reviewer() -> bool:
    if not review_admin_configured():
        st.warning(
            "A revisão administrativa ainda não está configurada. Adicione ADMIN_PASSWORD e "
            "SUPABASE_SERVICE_ROLE_KEY aos Secrets do Streamlit Cloud."
        )
        return False

    st.session_state.setdefault("review_admin_authenticated", False)
    if st.session_state.review_admin_authenticated:
        left, right = st.columns([4, 1])
        left.success("Acesso administrativo liberado nesta sessão.")
        if right.button("Sair", key="review_logout", use_container_width=True):
            st.session_state.review_admin_authenticated = False
            st.rerun()
        return True

    with st.form("review_login"):
        password = st.text_input("Senha administrativa", type="password")
        submitted = st.form_submit_button("Entrar na revisão", type="primary", use_container_width=True)
    if submitted:
        expected = admin_password()
        if expected and hmac.compare_digest(password, expected):
            st.session_state.review_admin_authenticated = True
            st.rerun()
        st.error("Senha administrativa incorreta.")
    return False


def _validate_question(statement: str, options: dict[str, str], answer: str) -> list[str]:
    errors: list[str] = []
    if len(statement.strip()) < 25:
        errors.append("O enunciado precisa ter pelo menos 25 caracteres.")
    missing = [letter for letter in "ABCDE" if not options.get(letter, "").strip()]
    if missing:
        errors.append("Preencha todas as alternativas: " + ", ".join(missing) + ".")
    normalized = [value.strip().casefold() for value in options.values() if value.strip()]
    if len(normalized) != len(set(normalized)):
        errors.append("Existem alternativas duplicadas.")
    if answer not in options or not options.get(answer, "").strip():
        errors.append("Selecione um gabarito válido.")
    return errors


def _question_payload(
    *,
    subject: str,
    topic: str,
    subtopic: str,
    difficulty: str,
    statement: str,
    options: dict[str, str],
    answer: str,
    explanation: str,
    tags_text: str,
    cargo: str,
    year: int,
    status: str,
) -> dict[str, Any]:
    tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
    return {
        "subject": subject.strip() or "Conhecimentos Gerais",
        "topic": topic.strip() or "Geral",
        "subtopic": subtopic.strip(),
        "difficulty": difficulty,
        "statement": statement.strip(),
        "options": {letter: value.strip() for letter, value in options.items()},
        "answer": answer,
        "explanation": explanation.strip(),
        "tags": tags[:20],
        "cargo": cargo.strip(),
        "year": int(year) if year else None,
        "status": status,
    }


def _render_question_editor(question: dict[str, Any]) -> None:
    question_id = int(question["id"])
    options = question.get("options") or {}
    if not isinstance(options, dict):
        options = {}
    tags = question.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    title = str(question.get("statement") or "Questão sem enunciado")
    with st.expander(f"#{question_id} · {title[:105]}", expanded=False):
        meta = st.columns(4)
        meta[0].caption(f"Órgão: {question.get('organization') or '—'}")
        meta[1].caption(f"Banca: {question.get('bank') or '—'}")
        meta[2].caption(f"Tipo: {question.get('source_kind') or '—'}")
        meta[3].caption(f"Confiança: {float(question.get('confidence') or 0):.0%}")
        source_url = str(question.get("source_url") or "")
        if source_url:
            st.link_button("Abrir fonte oficial", source_url)

        with st.form(f"review_question_{question_id}"):
            row = st.columns([2, 2, 2, 1])
            subject = row[0].text_input("Matéria", value=str(question.get("subject") or ""))
            topic = row[1].text_input("Assunto", value=str(question.get("topic") or ""))
            subtopic = row[2].text_input("Subassunto", value=str(question.get("subtopic") or ""))
            current_difficulty = str(question.get("difficulty") or "Média")
            difficulty = row[3].selectbox(
                "Dificuldade",
                DIFFICULTIES,
                index=DIFFICULTIES.index(current_difficulty) if current_difficulty in DIFFICULTIES else 1,
            )

            statement = st.text_area("Enunciado", value=title, height=150)
            edited_options: dict[str, str] = {}
            for letter in "ABCDE":
                edited_options[letter] = st.text_area(
                    f"Alternativa {letter}",
                    value=str(options.get(letter) or ""),
                    height=75,
                )

            answer_value = str(question.get("answer") or "A")
            answer = st.selectbox(
                "Gabarito",
                list("ABCDE"),
                index=list("ABCDE").index(answer_value) if answer_value in "ABCDE" else 0,
            )
            explanation = st.text_area(
                "Explicação",
                value=str(question.get("explanation") or ""),
                height=130,
            )
            extra = st.columns([2, 1])
            tags_text = extra[0].text_input("Tags separadas por vírgula", value=", ".join(map(str, tags)))
            cargo = extra[1].text_input("Cargo", value=str(question.get("cargo") or ""))
            year = st.number_input(
                "Ano — use 0 quando não informado",
                min_value=0,
                max_value=2100,
                value=int(question.get("year") or 0),
                step=1,
            )

            actions = st.columns(3)
            save = actions[0].form_submit_button("Salvar edição", use_container_width=True)
            approve = actions[1].form_submit_button("Aprovar e publicar", type="primary", use_container_width=True)
            reject = actions[2].form_submit_button("Rejeitar", use_container_width=True)

        if not (save or approve or reject):
            return

        target_status = str(question.get("status") or "pending_review")
        if approve:
            target_status = "published"
        elif reject:
            target_status = "rejected"

        if not reject:
            errors = _validate_question(statement, edited_options, answer)
            if errors:
                for error in errors:
                    st.error(error)
                return

        payload = _question_payload(
            subject=subject,
            topic=topic,
            subtopic=subtopic,
            difficulty=difficulty,
            statement=statement,
            options=edited_options,
            answer=answer,
            explanation=explanation,
            tags_text=tags_text,
            cargo=cargo,
            year=int(year),
            status=target_status,
        )
        try:
            update_question(question_id, payload)
            action_label = "publicada" if target_status == "published" else "rejeitada" if target_status == "rejected" else "salva"
            st.session_state.review_flash = f"Questão #{question_id} {action_label} com sucesso."
            st.rerun()
        except Exception as exc:
            st.error(f"Não foi possível atualizar a questão: {exc}")


def _render_review_tab() -> None:
    st.caption(
        "Revise enunciado, alternativas, gabarito e explicação. Questões pendentes não aparecem para estudantes."
    )
    if not _authenticate_reviewer():
        return

    flash = st.session_state.pop("review_flash", "")
    if flash:
        st.success(flash)

    try:
        pending = count_questions("pending_review")
        published = count_questions("published")
        rejected = count_questions("rejected")
    except Exception as exc:
        st.error(f"Falha ao consultar o Supabase: {exc}")
        return

    metrics = st.columns(3)
    metrics[0].metric("Aguardando revisão", pending)
    metrics[1].metric("Publicadas", published)
    metrics[2].metric("Rejeitadas", rejected)

    selected_status = st.selectbox(
        "Fila exibida",
        list(STATUS_LABELS),
        format_func=lambda value: STATUS_LABELS[value],
    )
    limit = st.slider("Quantidade carregada", 5, 100, 20, 5)

    try:
        questions = fetch_questions(selected_status, limit=limit)
    except Exception as exc:
        st.error(f"Falha ao carregar as questões: {exc}")
        return

    if not questions:
        st.info(f"Não há questões em: {STATUS_LABELS[selected_status]}.")
        return

    for question in questions:
        _render_question_editor(question)

    if selected_status == "published":
        st.info(
            "Após rejeitar uma questão já publicada, use a aba Catálogo e clique em "
            "“Sincronizar catálogo agora” para removê-la do banco local."
        )


def render_collector_page() -> None:
    st.markdown("## 🌐 Coletor e revisão")
    st.caption(
        "O GitHub Actions coleta fontes oficiais. Novas questões entram em revisão e só chegam aos simulados após aprovação."
    )

    catalog_tab, review_tab = st.tabs(["📚 Catálogo", "🛡️ Revisão administrativa"])
    with catalog_tab:
        _render_catalog_tab()
    with review_tab:
        _render_review_tab()

    st.info(
        "A coleta automática continua diária. O fluxo agora é: coletar → revisar → aprovar → sincronizar."
    )
