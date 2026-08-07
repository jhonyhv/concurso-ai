from __future__ import annotations

from datetime import date, timedelta
import html

import pandas as pd
import streamlit as st

from components.cards import metric_card, progress_row
from components.charts import PLOT_CONFIG, accuracy_evolution_chart
from database.database import get_settings, load_df
from services.reviews import get_due_count, sync_reviews
from utils.helpers import format_duration

MONTHS_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _go(page: str) -> None:
    st.session_state.current_page = page
    st.rerun()


def _study_days() -> set[date]:
    frame = load_df("SELECT DISTINCT session_date FROM study_sessions")
    if frame.empty:
        return set()
    return {pd.to_datetime(value).date() for value in frame["session_date"].dropna()}


def _streaks() -> tuple[int, int]:
    days = _study_days()
    if not days:
        return 0, 0
    current_day = date.today()
    if current_day not in days and current_day - timedelta(days=1) in days:
        current_day -= timedelta(days=1)
    current = 0
    probe = current_day
    while probe in days:
        current += 1
        probe -= timedelta(days=1)

    ordered = sorted(days)
    best = run = 1
    for previous, next_day in zip(ordered, ordered[1:]):
        if next_day == previous + timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return current, best


def _accuracy_last_days(days: int = 7) -> pd.DataFrame:
    start = date.today() - timedelta(days=days - 1)
    raw = load_df(
        """
        SELECT date(attempted_at) AS day,
               ROUND(100.0 * AVG(correct), 1) AS accuracy
          FROM attempts
         WHERE date(attempted_at) >= ?
         GROUP BY date(attempted_at)
         ORDER BY day
        """,
        (start.isoformat(),),
    )
    values = {row.day: float(row.accuracy) for row in raw.itertuples(index=False)}
    rows = []
    for offset in range(days):
        current = start + timedelta(days=offset)
        rows.append({"Dia": current.strftime("%d/%m"), "Acertos": values.get(current.isoformat(), 0.0)})
    return pd.DataFrame(rows)


def _calendar_html() -> str:
    sessions = load_df(
        """
        SELECT session_date, SUM(minutes) AS minutes
          FROM study_sessions
         GROUP BY session_date
        """
    )
    minutes = {pd.to_datetime(row.session_date).date(): int(row.minutes) for row in sessions.itertuples(index=False)}
    start = date.today() - timedelta(days=34)
    cells = []
    for offset in range(35):
        day = start + timedelta(days=offset)
        total = minutes.get(day, 0)
        level = 0 if total == 0 else 1 if total < 30 else 2 if total < 60 else 3 if total < 120 else 4
        today_class = " today" if day == date.today() else ""
        cells.append(
            f'<span class="heat-cell level-{level}{today_class}" title="{day.strftime("%d/%m/%Y")}: {total} min"></span>'
        )
    return "".join(cells)


def _daily_goal_data() -> tuple[list[tuple[str, int, int]], float]:
    settings = get_settings()
    today = date.today().isoformat()
    questions = int(load_df("SELECT COUNT(*) AS total FROM attempts WHERE date(attempted_at) = ?", (today,)).iloc[0]["total"])
    minutes = int(load_df("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE session_date = ?", (today,)).iloc[0]["total"])
    reviews = int(load_df("SELECT COUNT(*) AS total FROM reviews WHERE date(last_reviewed_at) = ?", (today,)).iloc[0]["total"])
    cards = int(load_df("SELECT COUNT(*) AS total FROM flashcard_reviews WHERE date(reviewed_at) = ?", (today,)).iloc[0]["total"])
    items = [
        ("Questões", questions, int(settings["daily_questions_goal"])),
        ("Tempo de estudo", minutes, int(settings["daily_minutes_goal"])),
        ("Revisões", reviews, int(settings["daily_reviews_goal"])),
        ("Flashcards", cards, int(settings["daily_flashcards_goal"])),
    ]
    completed = sum(1 for _, current, target in items if current >= target)
    return items, 100 * completed / len(items)


def _mission_copy(due_reviews: int, total_attempts: int, accuracy: float) -> tuple[str, str, str]:
    if due_reviews > 0:
        return (
            "ZERAR A FILA DE REVISÃO",
            f"Você tem {due_reviews} revisão(ões) pedindo atenção hoje.",
            "Revisar primeiro protege o que você já aprendeu antes de avançar no edital.",
        )
    if total_attempts < 20:
        return (
            "CONSTRUIR SUA LINHA DE BASE",
            "Seu diagnóstico ainda está começando.",
            "Responda questões para o ConcursoAI identificar seus pontos fortes e gargalos reais.",
        )
    if accuracy < 70:
        return (
            "RECUPERAR PONTOS FRACOS",
            f"Seu aproveitamento recente está em {accuracy:.0f}%.",
            "Priorize os assuntos com menor acerto antes de aumentar o volume de estudo.",
        )
    return (
        "AMPLIAR COBERTURA DO EDITAL",
        f"Seu aproveitamento recente está em {accuracy:.0f}%.",
        "O desempenho está consistente. Agora vale avançar para tópicos ainda pouco praticados.",
    )


def _render_mission(
    name: str,
    goal_progress: float,
    goal_items: list[tuple[str, int, int]],
    due_reviews: int,
    total_attempts: int,
    accuracy: float,
) -> None:
    eyebrow, title, detail = _mission_copy(due_reviews, total_attempts, accuracy)
    safe_name = html.escape(name)
    completed = sum(1 for _, current, target in goal_items if current >= target)
    task_html = "".join(
        f'<span class="mission-task {"done" if current >= target else ""}">'
        f'<b>{"✓" if current >= target else "•"}</b>{html.escape(label)} <small>{current}/{target}</small></span>'
        for label, current, target in goal_items
    )
    st.markdown(
        f"""
        <section class="mission-shell">
          <div class="mission-copy">
            <div class="mission-eyebrow">{eyebrow}</div>
            <h2>{safe_name}, seu próximo avanço começa aqui.</h2>
            <p><strong>{html.escape(title)}</strong> {html.escape(detail)}</p>
            <div class="mission-tasks">{task_html}</div>
          </div>
          <div class="mission-progress-wrap">
            <div class="mission-ring" style="--progress:{max(0.0, min(goal_progress, 100.0)):.1f};">
              <div><strong>{goal_progress:.0f}%</strong><span>meta do dia</span></div>
            </div>
            <small>{completed} de {len(goal_items)} objetivos concluídos</small>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _panel_header(title: str, subtitle: str = "", badge: str = "") -> None:
    subtitle_html = f"<span>{html.escape(subtitle)}</span>" if subtitle else ""
    badge_html = f'<b class="command-panel-badge">{html.escape(badge)}</b>' if badge else ""
    st.markdown(
        f'<div class="command-panel-header"><div><h3>{title}</h3>{subtitle_html}</div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def _coach_message(
    due_reviews: int,
    accuracy: float,
    total_attempts: int,
    performance: pd.DataFrame,
) -> tuple[str, str, str]:
    if due_reviews:
        return "Revisão primeiro", f"Existem {due_reviews} itens vencendo hoje.", "Alta prioridade"
    if total_attempts < 20:
        return "Calibrar diagnóstico", "Faça pelo menos 20 questões para ativar recomendações mais precisas.", "Começar agora"
    if not performance.empty:
        weakest = performance.sort_values("Acertos").iloc[0]
        if float(weakest["Acertos"]) < 70:
            return (
                "Atacar o maior gargalo",
                f'{weakest["Matéria"]} está com {float(weakest["Acertos"]):.0f}% de acerto.',
                "Foco recomendado",
            )
    if accuracy >= 80:
        return "Aumentar dificuldade", "Seu desempenho recente permite incluir questões mais exigentes.", "Bom momento"
    return "Manter consistência", "Continue alternando questões, revisão e estudo focado.", "Ritmo saudável"


def render_dashboard() -> None:
    sync_reviews()
    settings = get_settings()
    name = str(settings.get("user_name", "Aluno"))
    current_streak, best_streak = _streaks()
    due_reviews = get_due_count()
    last7 = (date.today() - timedelta(days=6)).isoformat()

    total_attempts = int(load_df("SELECT COUNT(*) AS total FROM attempts").iloc[0]["total"])
    week_attempts = load_df(
        "SELECT COUNT(*) AS total, COALESCE(100.0 * AVG(correct), 0) AS accuracy FROM attempts WHERE date(attempted_at) >= ?",
        (last7,),
    ).iloc[0]
    week_accuracy = float(week_attempts["accuracy"])
    week_minutes = int(load_df("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE session_date >= ?", (last7,)).iloc[0]["total"])

    performance = load_df(
        """
        SELECT q.subject AS Matéria,
               COUNT(a.id) AS Questões,
               ROUND(100.0 * AVG(a.correct), 1) AS Acertos
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
         GROUP BY q.subject
         ORDER BY Acertos DESC, Questões DESC
        """
    )
    reviews = load_df(
        """
        SELECT subject, topic, due_date, source
          FROM reviews
         WHERE status IN ('pendente', 'agendada')
         ORDER BY date(due_date), id
         LIMIT 4
        """
    )
    goal_items, goal_progress = _daily_goal_data()

    _render_mission(
        name=name,
        goal_progress=goal_progress,
        goal_items=goal_items,
        due_reviews=due_reviews,
        total_attempts=total_attempts,
        accuracy=week_accuracy,
    )

    quick1, quick2, quick3, quick_space = st.columns([1, 1, 1, 2.6], gap="small")
    with quick1:
        if st.button("⚡ Revisar agora", key="quick_review", use_container_width=True, type="primary"):
            _go("Revisões")
    with quick2:
        if st.button("◎ Fazer questões", key="quick_questions", use_container_width=True):
            _go("Questões")
    with quick3:
        if st.button("✦ Professor IA", key="quick_ai", use_container_width=True):
            _go("Professor IA")
    with quick_space:
        st.markdown('<div class="quick-context">Ações rápidas para manter o ritmo de hoje</div>', unsafe_allow_html=True)

    metrics = st.columns(4, gap="medium")
    with metrics[0]:
        metric_card("Aproveitamento", f"{week_accuracy:.0f}%", "Últimos 7 dias", "◎", "green")
    with metrics[1]:
        metric_card("Questões", str(total_attempts), "Respondidas", "▤", "blue")
    with metrics[2]:
        metric_card("Tempo focado", format_duration(week_minutes), "Últimos 7 dias", "◷", "purple")
    with metrics[3]:
        metric_card("Sequência", f"{current_streak} dias", f"Recorde: {best_streak} dias", "↗", "orange")

    pulse, coach = st.columns([1.65, 1], gap="medium")
    with pulse:
        with st.container(border=True):
            _panel_header("Pulso de desempenho", "Seu aproveitamento ao longo dos últimos 7 dias", "7 DIAS")
            if total_attempts == 0:
                st.markdown(
                    """
                    <div class="command-empty chart-empty">
                      <div class="empty-orbit">↗</div>
                      <strong>Seu gráfico começa com a primeira questão.</strong>
                      <span>Responda questões para visualizar tendência, consistência e evolução.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.plotly_chart(
                    accuracy_evolution_chart(_accuracy_last_days()),
                    use_container_width=True,
                    config=PLOT_CONFIG,
                )

    with coach:
        with st.container(border=True):
            coach_title, coach_text, coach_badge = _coach_message(
                due_reviews, week_accuracy, total_attempts, performance
            )
            _panel_header("Coach de aprovação", "Recomendação calculada a partir do seu uso", "IA READY")
            st.markdown(
                f"""
                <div class="coach-card">
                  <div class="coach-orb">✦</div>
                  <div class="coach-badge">{html.escape(coach_badge)}</div>
                  <h4>{html.escape(coach_title)}</h4>
                  <p>{html.escape(coach_text)}</p>
                  <div class="coach-foot"><span>CONCURSOAI</span><b>próxima melhor ação →</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Abrir Professor IA", key="coach_ai", use_container_width=True):
                _go("Professor IA")

    lower_left, lower_center, lower_right = st.columns([1.1, 1, 1], gap="medium")

    with lower_left:
        with st.container(border=True):
            _panel_header("Domínio por matéria", "Onde você ganha e perde pontos")
            if performance.empty:
                st.markdown(
                    '<div class="command-empty"><strong>Sem diagnóstico ainda.</strong><span>Seu mapa de domínio aparecerá após responder questões.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                for row in performance.head(5).itertuples(index=False):
                    score = float(row.Acertos)
                    tone = "green" if score >= 75 else "blue" if score >= 60 else "yellow" if score >= 45 else "red"
                    progress_row(str(row.Matéria), score, tone)
            if st.button("Explorar desempenho  →", key="dashboard_subjects", use_container_width=True):
                _go("Desempenho")

    with lower_center:
        with st.container(border=True):
            month_label = f"{MONTHS_PT[date.today().month].upper()} {date.today().year}"
            _panel_header("Consistência", "35 dias de estudo", month_label)
            st.markdown(
                '<div class="heat-weekdays"><span>D</span><span>S</span><span>T</span><span>Q</span><span>Q</span><span>S</span><span>S</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="heatmap reference-heatmap">{_calendar_html()}</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="heat-legend reference-heat-legend"><span class="level-4"></span> 2h+ <span class="level-3"></span> 1h+ <span class="level-2"></span> 30m+ <span class="level-0"></span> sem estudo</div>',
                unsafe_allow_html=True,
            )
            if st.button("Abrir calendário  →", key="dashboard_calendar", use_container_width=True):
                _go("Calendário")

    with lower_right:
        with st.container(border=True):
            _panel_header("Fila inteligente", "O que revisar em seguida", f"{due_reviews} HOJE")
            if reviews.empty:
                st.markdown(
                    '<div class="command-empty"><strong>Fila limpa.</strong><span>As próximas revisões aparecerão automaticamente aqui.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                dot_classes = ["blue", "yellow", "green", "purple"]
                for index, row in enumerate(reviews.itertuples(index=False)):
                    due_date = pd.to_datetime(row.due_date).date()
                    if due_date <= date.today():
                        when = "Hoje"
                    elif due_date == date.today() + timedelta(days=1):
                        when = "Amanhã"
                    else:
                        when = due_date.strftime("%d/%m")
                    topic = html.escape(str(row.topic or row.subject))
                    subject = html.escape(str(row.subject))
                    st.markdown(
                        f"""
                        <div class="command-review-row">
                          <span class="command-review-dot {dot_classes[index % len(dot_classes)]}"></span>
                          <div><strong>{topic}</strong><small>{subject}</small></div>
                          <b>{when}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            if st.button("Abrir revisões  →", key="dashboard_reviews", use_container_width=True):
                _go("Revisões")
