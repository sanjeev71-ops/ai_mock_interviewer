import json
from pathlib import Path
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

from database.database import Database
from config.settings import GROQ_MODEL
from interview.controller import InterviewController
from interview.state import InterviewState
from services.groq_service import FREE_CHAT_MODELS
from utils.export import report_to_markdown


# ==================================================
# PAGE CONFIG + THEME
# ==================================================

st.set_page_config(
    page_title="AI Mock Interview",
    page_icon="🎯",
    layout="wide",
)


def apply_gradient_theme():
    """Subtle dark gradient for main area + sidebar.

    Static CSS only (no user content), injected via
    unsafe_allow_html. Used as the fallback when the
    background video file is unavailable.
    """
    st.markdown(
        dedent(
            """
            <style>
            .stApp {
                background: linear-gradient(
                    135deg,
                    #0f172a 0%,
                    #1e1b4b 55%,
                    #312e81 100%
                );
                background-attachment: fixed;
                color: #f1f5f9;
            }

            section[data-testid="stSidebar"] > div {
                background: linear-gradient(
                    180deg,
                    rgba(15, 23, 42, 0.97) 0%,
                    rgba(30, 27, 75, 0.97) 60%,
                    rgba(49, 46, 129, 0.97) 100%
                );
            }

            .stApp h1,
            .stApp h2,
            .stApp h3 {
                color: #ffffff !important;
            }

            .stApp h1 {
                text-align: center !important;
            }

            .stApp .stCaption,
            .stApp [data-testid="stCaptionContainer"] {
                color: #cbd5e1 !important;
            }

            .stApp [data-testid="stMetricValue"],
            .stApp [data-testid="stMetricLabel"] {
                color: #f1f5f9 !important;
            }

            .stApp hr {
                border-color: rgba(
                    241, 245, 249, 0.2
                ) !important;
            }

            .stApp .stTextArea textarea {
                background-color: rgba(
                    15, 23, 42, 0.6
                );
                color: #f1f5f9;
            }

            .stApp .stTextArea textarea::placeholder {
                color: #94a3b8;
            }

            .stApp [data-testid="stBaseButton-primary"] {
                background-color: #000000 !important;
                border-color: #000000 !important;
                color: #ffffff !important;
            }

            .stApp [data-testid="stBaseButton-primary"]:hover {
                background-color: #1f1f1f !important;
                border-color: #1f1f1f !important;
                color: #ffffff !important;
            }

            .stApp div[data-baseweb="select"],
            .stApp .stNumberInput input,
            .stApp .stTextArea textarea {
                background-color: rgba(
                    255, 255, 255, 0.08
                ) !important;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(
                    255, 255, 255, 0.18
                ) !important;
                border-radius: 12px;
                color: #f1f5f9;
            }

            .stApp [data-testid="stSelectbox"] > div {
                background: rgba(
                    255, 255, 255, 0.08
                );
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                border: 1px solid rgba(
                    255, 255, 255, 0.20
                );
                border-radius: 12px;
            }

            .stApp [data-testid="stSelectbox"] > div:focus-within {
                border-color: rgba(
                    255, 255, 255, 0.45
                );
            }

            .stApp [data-testid="stNumberInput"] > div {
                background: rgba(
                    255, 255, 255, 0.08
                );
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                border: 1px solid rgba(
                    255, 255, 255, 0.20
                );
                border-radius: 12px;
            }

            .stApp [data-testid="stNumberInput"] > div:focus-within {
                border-color: rgba(
                    255, 255, 255, 0.45
                );
            }

            .stApp [data-testid="stNumberInput"] input,
            .stApp [data-testid="stNumberInput"] button,
            .stApp [data-testid="stNumberInput"] div {
                background: transparent !important;
                background-color: transparent !important;
                border-color: transparent !important;
                box-shadow: none !important;
                color: #f1f5f9;
            }

            .stApp [data-testid="stSelectbox"] div[data-baseweb="select"],
            .stApp [data-testid="stSelectbox"] div[data-baseweb="select"] div {
                background: transparent !important;
                background-color: transparent !important;
                border-color: transparent !important;
                box-shadow: none !important;
            }

            .stApp div[data-baseweb="select"] span {
                color: #f1f5f9;
            }

            .stApp div[data-baseweb="select"] svg {
                fill: #cbd5e1;
            }

            .stApp div[data-baseweb="select"],
            .stApp div[data-baseweb="select"] *,
            div[data-baseweb="popover"] ul[data-baseweb="menu"],
            div[data-baseweb="popover"] ul[data-baseweb="menu"] li,
            .stApp [data-testid="stNumberInput"] button {
                cursor: pointer !important;
            }

            div[data-baseweb="popover"] ul[data-baseweb="menu"] {
                background-color: rgba(
                    15, 23, 42, 0.88
                );
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
            }

            div[data-baseweb="popover"] ul[data-baseweb="menu"] li span {
                color: #f1f5f9;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


apply_gradient_theme()


# Background video source. Embedded as a data URI because
# Streamlit's static serving forces text/plain + nosniff
# for .mp4 (browsers refuse to play it as video).
VIDEO_PATH = Path(__file__).parent / "static" / "background.mp4"


@st.cache_data
def _video_data_uri(_mtime: float) -> str | None:
    """Base64-embed the background video (cached).

    _mtime busts the cache when the file is replaced.
    """
    import base64

    try:
        raw = VIDEO_PATH.read_bytes()
    except OSError:
        return None

    return "data:video/mp4;base64," + base64.b64encode(
        raw
    ).decode("ascii")


def apply_video_background(video_url: str):
    """Full-app looping video behind a dark overlay.

    The overlay (~72% dark) keeps white text readable on
    any frame. Sidebar and header are transparent so the
    video shows through everywhere uniformly.

    CSS and the <video> element are injected in two
    separate small static calls (plus the URI), so the
    stylesheet can never be corrupted by payload size.
    The gradient stays underneath as the base layer, so
    a missing/blocked video degrades to gradient, never
    to an unreadable page.
    """
    st.markdown(
        dedent(
            """
            <style>
            #bg-video {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                object-fit: cover;
                z-index: -2;
            }

            #bg-overlay {
                position: fixed;
                inset: 0;
                background: rgba(8, 10, 26, 0.72);
                z-index: -1;
            }

            .stApp {
                background: transparent;
            }

            section[data-testid="stSidebar"] > div {
                background: transparent;
            }

            [data-testid="stHeader"] {
                background: transparent;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        '<video autoplay muted loop playsinline id="bg-video">'
        + '<source src="'
        + video_url
        + '" type="video/mp4">'
        + "</video>"
        + '<div id="bg-overlay"></div>',
        unsafe_allow_html=True,
    )


try:
    _video_mtime = VIDEO_PATH.stat().st_mtime
except OSError:
    _video_mtime = 0.0

_video_uri = _video_data_uri(_video_mtime)

if _video_uri:
    apply_video_background(_video_uri)


TIMING_AS_YOU_GO = "as_you_go"
TIMING_AT_END = "at_end"


# ==================================================
# SESSION STATE
# ==================================================

if "controller" not in st.session_state:
    st.session_state.controller = (
        InterviewController()
    )


if "database" not in st.session_state:
    st.session_state.database = Database()


if "show_history" not in st.session_state:
    st.session_state.show_history = False


if "selected_history" not in st.session_state:
    st.session_state.selected_history = None


if "interview" not in st.session_state:
    st.session_state.interview = None


if "view_index" not in st.session_state:
    st.session_state.view_index = 0


if "eval_timing" not in st.session_state:
    st.session_state.eval_timing = TIMING_AS_YOU_GO


if "report" not in st.session_state:
    st.session_state.report = None


if "confirm_home" not in st.session_state:
    st.session_state.confirm_home = False


if "confirm_restart" not in st.session_state:
    st.session_state.confirm_restart = False


if "confirm_finish" not in st.session_state:
    st.session_state.confirm_finish = False


if "confirm_submit_test" not in st.session_state:
    st.session_state.confirm_submit_test = False


if "visited" not in st.session_state:
    st.session_state.visited = set()


if "expired_notice" not in st.session_state:
    st.session_state.expired_notice = False


# --------------------------------------------------
# STALE-SERVER GUARD
# --------------------------------------------------
# Streamlit reruns app.py on file changes but does NOT
# reload imported modules. If backend code changed on
# disk, the running server holds stale classes. Detect
# it here (before the sidebar or any screen runs) and
# say the fix plainly instead of raising TypeErrors
# like "unexpected keyword argument".


def _controller_is_current() -> bool:
    import inspect

    controller = st.session_state.controller

    for method in (
        "finish_interview",
        "enforce_expiry",
        "toggle_mark",
        "mark_skipped",
        "status_of",
    ):
        if not hasattr(controller, method):
            return False

    try:
        params = inspect.signature(
            controller.create_interview
        ).parameters
    except (TypeError, ValueError):
        return False

    return (
        "time_limit_minutes" in params and "model" in params
    )


if not _controller_is_current():
    st.error(
        "The app code was updated — please restart "
        "the Streamlit server: stop it with Ctrl+C "
        "and run `streamlit run app.py` again. "
        "A browser refresh is not enough."
    )
    st.stop()


# ==================================================
# HELPERS
# ==================================================

def reset_interview():
    st.session_state.interview = None
    st.session_state.view_index = 0
    st.session_state.report = None
    st.session_state.confirm_home = False
    st.session_state.confirm_restart = False
    st.session_state.confirm_finish = False
    st.session_state.confirm_submit_test = False
    st.session_state.show_history = False
    st.session_state.selected_history = None
    st.session_state.visited = set()
    st.session_state.expired_notice = False


def back_to_interview():
    st.session_state.show_history = False
    st.session_state.selected_history = None
    st.rerun()


def go_to(index):
    st.session_state.view_index = index
    st.rerun()


def _advance_view(interview):
    """Move view to the next question number.

    Falls back to the first unanswered question at the
    end of the list (or stays put when all answered).
    """
    controller = st.session_state.controller
    total = interview.number_of_questions

    nxt = st.session_state.view_index + 1

    if nxt < total:
        st.session_state.view_index = nxt
        return

    first = controller.first_unanswered_index(interview)

    if first is not None:
        st.session_state.view_index = first


def render_evaluation(evaluation):
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Correctness",
        f"{evaluation.scores.correctness}/10",
    )
    c2.metric(
        "Technical Depth",
        f"{evaluation.scores.technical_depth}/10",
    )
    c3.metric(
        "Clarity",
        f"{evaluation.scores.clarity}/10",
    )
    c4.metric(
        "Completeness",
        f"{evaluation.scores.completeness}/10",
    )

    st.metric(
        "Question Score",
        f"{evaluation.overall_score:.2f}/10",
    )


def summarize_feedback(feedback: str, limit: int = 280) -> str:
    """First ~2 lines / 280 chars for the compact view."""
    text = " ".join(feedback.split())
    if len(text) <= limit:
        return text

    cut = text[:limit].rsplit(" ", 1)[0]

    return cut + "…"


def render_question_options(
    question, selected_index: int | None = None
):
    """List A-D options, marking the correct one (✅)
    and the candidate's pick (👉). Works with both
    Question models and history dicts."""
    if isinstance(question, dict):
        import json as _json

        options = _json.loads(question.get("options") or "[]")
        correct_index = int(question.get("correct_index") or 0)
    else:
        options = question.options
        correct_index = question.correct_index

    letters = "ABCD"

    for pos, option in enumerate(options):
        marks = ""

        if pos == correct_index:
            marks += " ✅"

        if pos == selected_index:
            marks += " 👉"

        st.write(f"{letters[pos]}. {option}{marks}")


def confirm_block(flag_key, message, on_confirm):
    """Two-click destructive confirm. Returns True while armed."""
    if not st.session_state[flag_key]:
        return False

    st.warning(message)

    yes_col, no_col = st.columns(2)

    with yes_col:
        if st.button(
            "Yes, discard",
            key=f"{flag_key}_yes",
            use_container_width=True,
        ):
            st.session_state[flag_key] = False
            on_confirm()
            st.rerun()

    with no_col:
        if st.button(
            "Cancel",
            key=f"{flag_key}_no",
            use_container_width=True,
        ):
            st.session_state[flag_key] = False
            st.rerun()

    return True


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:
    st.title("AI Mock Interview")

    st.caption(
        "Technical Interview Evaluator"
    )

    if st.button(
        "Interview History",
        use_container_width=True,
    ):
        st.session_state.show_history = True
        st.session_state.selected_history = None
        st.rerun()

    if (
        st.session_state.interview is not None
        or st.session_state.show_history
    ):
        if confirm_block(
            "confirm_home",
            "Leave to menu? Current progress will be lost.",
            reset_interview,
        ):
            pass
        elif st.button(
            "🏠 Home", use_container_width=True
        ):
            st.session_state.confirm_home = True
            st.rerun()

    if st.session_state.interview:
        interview = st.session_state.interview
        controller = st.session_state.controller

        st.divider()

        st.write(f"**Role:** {interview.role}")
        st.write(
            f"**Experience:** "
            f"{interview.experience_level}"
        )
        st.write(
            f"**Difficulty:** "
            f"{interview.difficulty}"
        )
        st.write(
            f"**Questions:** "
            f"{interview.number_of_questions}"
        )
        st.write(
            f"**Answered:** "
            f"{controller.answered_count(interview)}"
        )
        st.write(
            "**Evaluation:** "
            + (
                "As you go"
                if st.session_state.eval_timing
                == TIMING_AS_YOU_GO
                else "At the end"
            )
        )
        st.write(
            f"**Model:** "
            f"{getattr(interview, 'model', '') or '—'}"
        )

        if interview.time_limit_minutes:
            left = controller.remaining_seconds(interview)

            if left is None:
                st.write("**Time:** No limit")
            else:
                minutes, seconds = divmod(left, 60)
                st.write(
                    f"**Time left:** "
                    f"{minutes:02d}:{seconds:02d}"
                )

                components.html(
                    f"""
                    <div id="tminus" style="
                        font-family: monospace;
                        font-size: 28px;
                        font-weight: bold;
                        color: #f1f5f9;
                        text-align: center;
                    "></div>
                    <script>
                    const deadline = Date.now() + ({left} * 1000);
                    const el = document.getElementById("tminus");
                    function tick() {{
                        const ms = Math.max(
                            0, deadline - Date.now()
                        );
                        const m = Math.floor(ms / 60000);
                        const s = Math.floor(
                            (ms % 60000) / 1000
                        );
                        el.textContent =
                            String(m).padStart(2, "0") + ":"
                            + String(s).padStart(2, "0");
                        el.style.color =
                            ms < 120000 ? "#f87171" : "#f1f5f9";
                    }}
                    tick();
                    setInterval(tick, 1000);
                    </script>
                    """,
                    height=45,
                )

        st.divider()
        st.subheader("Progress")

        can_jump = (
            interview.status == InterviewState.ASKING
        )

        for idx, question in enumerate(interview.questions):
            state = controller.status_of(
                interview, question.question_id
            )

            if state == "answered-marked":
                latest = controller.get_latest_result(
                    interview, question.question_id
                )
                icon = "🟣"
                suffix = (
                    f" — "
                    f"{latest.evaluation.overall_score}/10"
                )
            elif state == "answered":
                latest = controller.get_latest_result(
                    interview, question.question_id
                )
                icon = "✅"
                suffix = (
                    f" — "
                    f"{latest.evaluation.overall_score}/10"
                )
            elif state == "marked":
                icon = "🟣"
                suffix = " — review"
            elif state == "skipped":
                icon = "🟠"
                suffix = " — skipped"
            elif idx == st.session_state.view_index:
                icon = "◀"
                suffix = ""
            elif (
                question.question_id
                not in st.session_state.visited
            ):
                icon = "▫️"
                suffix = ""
            else:
                icon = "⬜"
                suffix = ""

            if st.button(
                f"{icon} Q{question.question_id} · "
                f"{question.topic}{suffix}",
                key=f"jump_{question.question_id}",
                use_container_width=True,
                disabled=not can_jump,
            ):
                go_to(idx)

        st.divider()

        answered = controller.answered_count(interview)
        unanswered = controller.unanswered_count(interview)
        marked = controller.marked_count(interview)

        if (
            interview.status != InterviewState.COMPLETED
            and answered > 0
        ):
            if confirm_block(
                "confirm_finish",
                f"Finish? {answered} answered · "
                f"{unanswered} unanswered · "
                f"{marked} marked for review.",
                lambda: controller.finish_interview(
                    st.session_state.interview
                ),
            ):
                pass
            elif st.button(
                "Finish Interview",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.confirm_finish = True
                st.rerun()

        st.divider()

        if confirm_block(
            "confirm_restart",
            "Start over? Current progress will be lost.",
            reset_interview,
        ):
            pass
        elif st.button(
            "Start New Interview",
            use_container_width=True,
        ):
            st.session_state.confirm_restart = True
            st.rerun()


# ==================================================
# HEADER (full width so the title truly centers)
# ==================================================

st.title(
    "AI Mock Interview & Evaluator"
)
st.markdown(
    "<p style='text-align: center; color: #cbd5e1;'>Technical interview powered by Groq</p>",
    unsafe_allow_html=True,
)


# ==================================================
# INTERVIEW HISTORY
# ==================================================

if st.session_state.show_history:
    st.title("Interview History")

    # ------------------------------------------
    # Selected interview
    # ------------------------------------------

    if st.session_state.selected_history:
        data = st.session_state.database.get_interview(
            st.session_state.selected_history
        )

        if data is None:
            st.error(
                "Interview could not be found."
            )
        else:
            interview = data["interview"]
            report = data["report"]

            st.subheader(interview["role"])
            st.caption(
                f"{interview['experience_level']} "
                f"• "
                f"{interview['difficulty']}"
            )

            if interview.get("model"):
                st.caption(f"Model: {interview['model']}")

            if interview.get("time_limit_minutes"):
                st.caption(
                    f"Time limit: "
                    f"{interview['time_limit_minutes']} min"
                )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Overall",
                f"{interview['overall_score']:.2f}/10",
            )
            c2.metric(
                "Technical",
                f"{interview['technical_score']:.2f}/10",
            )
            c3.metric(
                "Communication",
                f"{interview['communication_score']:.2f}/10",
            )

            st.divider()

            if report:
                strengths = json.loads(
                    report["strengths"]
                )
                weaknesses = json.loads(
                    report["weaknesses"]
                )
                recommendations = json.loads(
                    report["recommendations"]
                )
                topic_performance = json.loads(
                    report["topic_performance"]
                )

                st.subheader("Strengths")
                for item in strengths:
                    st.success(item)

                st.subheader("Weaknesses")
                for item in weaknesses:
                    st.warning(item)

                st.subheader("Recommendations")
                for item in recommendations:
                    st.info(item)

                if topic_performance:
                    topic_data = {
                        "Topic": list(
                            topic_performance.keys()
                        ),
                        "Score": list(
                            topic_performance.values()
                        ),
                    }

                    fig = px.bar(
                        topic_data,
                        x="Topic",
                        y="Score",
                        range_y=[0, 10],
                        title="Topic Performance",
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#f1f5f9",
                    )
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

                st.divider()

            st.subheader("Question Results")

            questions_by_id = {
                q["question_id"]: q
                for q in data["questions"]
            }

            results_by_question = {}
            for row in data["results"]:
                results_by_question.setdefault(
                    row["question_id"], []
                ).append(row)

            for question_id in sorted(results_by_question):
                attempts = results_by_question[
                    question_id
                ]
                question = questions_by_id.get(
                    question_id, {}
                )

                with st.expander(
                    f"Question {question_id}"
                    + (
                        f" — {question.get('topic', '')}"
                        if question.get("topic")
                        else ""
                    )
                    + f" ({len(attempts)} attempt(s))"
                ):
                    if question.get("question"):
                        st.markdown("**Question**")
                        st.write(question["question"])

                    if question.get("options"):
                        st.markdown("**Options**")
                        render_question_options(question)

                    if question.get("explanation"):
                        st.markdown("**Explanation**")
                        st.write(question["explanation"])

                    for attempt in attempts:
                        picked = (
                            attempt["candidate_answer"][:1]
                            if attempt["candidate_answer"]
                            else ""
                        )
                        picked_index = (
                            "ABCD".index(picked)
                            if picked in "ABCD"
                            else None
                        )

                        st.markdown(
                            f"**Attempt "
                            f"{attempt['attempt']} — "
                            f"{attempt['overall_score']:.2f}"
                            f"/10**"
                        )
                        st.markdown("**Your Pick**")
                        st.write(
                            attempt["candidate_answer"]
                        )
                        render_question_options(
                            question, picked_index
                        )

                        c1, c2, c3, c4 = st.columns(4)

                        c1.metric(
                            "Correctness",
                            f"{attempt['correctness']}/10",
                        )
                        c2.metric(
                            "Technical Depth",
                            f"{attempt['technical_depth']}/10",
                        )
                        c3.metric(
                            "Clarity",
                            f"{attempt['clarity']}/10",
                        )
                        c4.metric(
                            "Completeness",
                            f"{attempt['completeness']}/10",
                        )

                        st.markdown("**Feedback**")
                        st.write(attempt["feedback"])

                        strengths = json.loads(
                            attempt["strengths"]
                        )
                        weaknesses = json.loads(
                            attempt["weaknesses"]
                        )

                        if strengths:
                            st.markdown("**Strengths**")
                            for item in strengths:
                                st.write(f"• {item}")

                        if weaknesses:
                            st.markdown("**Weaknesses**")
                            for item in weaknesses:
                                st.write(f"• {item}")

                        st.divider()

            st.divider()

            if st.button("Back to History"):
                st.session_state.selected_history = None
                st.rerun()

    # ------------------------------------------
    # History list
    # ------------------------------------------

    else:
        interviews = st.session_state.database.get_interviews()

        if not interviews:
            st.info(
                "No previous interviews found."
            )
        else:
            st.subheader(
                f"{len(interviews)} "
                f"previous interview(s)"
            )

            for interview in interviews:
                with st.container(border=True):
                    col1, col2, col3 = st.columns(
                        [3, 2, 1]
                    )

                    with col1:
                        st.markdown(
                            f"### {interview['role']}"
                        )
                        st.write(
                            f"{interview['experience_level']} "
                            f"• "
                            f"{interview['difficulty']}"
                        )
                        st.caption(
                            interview["created_at"]
                        )

                    with col2:
                        st.metric(
                            "Score",
                            f"{interview['overall_score']:.2f}/10",
                        )

                    with col3:
                        if st.button(
                            "View",
                            key=(
                                f"view_"
                                f"{interview['session_id']}"
                            ),
                        ):
                            st.session_state[
                                "selected_history"
                            ] = interview["session_id"]
                            st.rerun()

        st.divider()

        if st.button("Back to Interview"):
            back_to_interview()

    st.stop()


# ==================================================
# SETUP
# ==================================================

if st.session_state.interview is None:
    st.subheader(
        "Interview Setup"
    )

    st.caption(
        "Questions are generated according to the "
        "selected role, experience level, difficulty, "
        "and topic coverage."
    )

    col1, col2 = st.columns(2)

    with col1:
        role = st.selectbox(
            "Job Role",
            [
                "Python Developer",
                "Java Developer",
                "Web Developer",
                "Data Scientist",
                "Machine Learning Engineer",
                "Software Developer",
            ],
        )

        experience = st.selectbox(
            "Experience Level",
            [
                "Beginner",
                "Junior",
                "Intermediate",
                "Advanced",
            ],
        )

    with col2:
        difficulty = st.selectbox(
            "Interview Difficulty",
            [
                "Easy",
                "Medium",
                "Hard",
            ],
        )

        number_of_questions = st.number_input(
            "Number of Questions",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )

    model_choice = st.selectbox(
        "AI Model",
        FREE_CHAT_MODELS,
        index=(
            FREE_CHAT_MODELS.index(GROQ_MODEL)
            if GROQ_MODEL in FREE_CHAT_MODELS
            else 0
        ),
        help=(
            "If the selected model fails, the app "
            "automatically tries the next one."
        ),
    )

    timing_choice = st.radio(
        "When do you want to see evaluations?",
        [
            "As you go — after each answer",
            "At the end — all together",
        ],
        index=(
            0
            if st.session_state.eval_timing
            == TIMING_AS_YOU_GO
            else 1
        ),
    )

    time_choice = st.selectbox(
        "Time Limit",
        [
            "No time limit",
            "10 minutes",
            "15 minutes",
            "20 minutes",
            "30 minutes",
            "45 minutes",
            "60 minutes",
        ],
        help=(
            "The whole test must be finished in time. "
            "When time runs out, the interview ends "
            "immediately."
        ),
    )

    st.divider()

    if st.button(
        "Start Interview",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner(
            "Generating technical questions..."
        ):
            try:
                interview = (
                    st.session_state.controller
                    .create_interview(
                        role=role,
                        experience_level=experience,
                        difficulty=difficulty,
                        number_of_questions=
                            number_of_questions,
                        model=model_choice,
                        time_limit_minutes=(
                            None
                            if time_choice == "No time limit"
                            else int(
                                time_choice.split()[0]
                            )
                        ),
                    )
                )

                st.session_state.interview = interview
                st.session_state.view_index = 0
                st.session_state.report = None
                st.session_state.visited = {1}
                st.session_state.expired_notice = False
                st.session_state.eval_timing = (
                    TIMING_AS_YOU_GO
                    if timing_choice.startswith("As you go")
                    else TIMING_AT_END
                )

                st.rerun()

            except Exception as error:
                st.error(
                    "We could not generate a valid "
                    "interview. Please try again."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(
                        str(error)
                    )


# ==================================================
# ACTIVE INTERVIEW
# ==================================================

else:
    interview = st.session_state.interview
    controller = st.session_state.controller

    # Streamlit reruns do not reload imported modules: if the
    # code changed on disk (new session fields), the running
    # server holds a stale InterviewSession. Fail loudly with
    # the actual fix instead of a cryptic AttributeError.
    for _attr in (
        "model",
        "marked_for_review",
        "skipped",
        "time_limit_minutes",
        "started_at",
    ):
        if not hasattr(interview, _attr):
            st.error(
                "The app code was updated — please restart "
                "the Streamlit server: stop it with Ctrl+C "
                "and run `streamlit run app.py` again."
            )
            st.stop()

    # Server-side timer enforcement: finish the moment
    # time runs out (the on-screen draft is discarded).
    if controller.enforce_expiry(interview):
        st.session_state.expired_notice = True
        st.rerun()

    # ----------------------------------------------
    # COMPLETED
    # ----------------------------------------------

    if interview.status == InterviewState.COMPLETED:
        if st.session_state.expired_notice:
            st.warning(
                "⏰ Time expired — the interview was "
                "finished automatically."
            )
        else:
            st.success(
                "Interview completed."
            )

        if st.session_state.report is None:
            with st.spinner(
                "Generating final report..."
            ):
                try:
                    report = controller.generate_report(
                        interview
                    )
                    st.session_state.report = report

                    try:
                        st.session_state.database.save_interview(
                            interview,
                            report,
                        )
                    except Exception as db_error:
                        st.warning(
                            "Report generated, but saving "
                            "to history failed: "
                            f"{db_error}"
                        )

                    st.rerun()
                except Exception as error:
                    st.error(
                        f"Could not generate report: "
                        f"{error}"
                    )

        else:
            report = st.session_state.report

            st.subheader(
                "Final Performance"
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Overall Score",
                f"{report.overall_score:.2f}/10",
            )
            c2.metric(
                "Technical Score",
                f"{report.technical_score:.2f}/10",
            )
            c3.metric(
                "Communication",
                f"{report.communication_score:.2f}/10",
            )

            st.divider()

            st.subheader(
                "Topic Performance"
            )

            if report.topic_performance:
                topic_data = {
                    "Topic": list(
                        report.topic_performance.keys()
                    ),
                    "Score": list(
                        report.topic_performance.values()
                    ),
                }

                fig = px.bar(
                    topic_data,
                    x="Topic",
                    y="Score",
                    range_y=[0, 10],
                    title="Performance by Topic",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#f1f5f9",
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            st.subheader(
                "Strengths"
            )
            for strength in report.strengths:
                st.success(strength)

            st.subheader(
                "Weaknesses"
            )
            for weakness in report.weaknesses:
                st.warning(weakness)

            st.subheader(
                "Recommendations"
            )
            for recommendation in report.recommendations:
                st.info(recommendation)

            st.subheader(
                "Question Results"
            )

            for question in interview.questions:
                attempts = controller.attempts_for(
                    interview, question.question_id
                )

                if not attempts:
                    with st.expander(
                        f"Question "
                        f"{question.question_id}"
                        f" — "
                        f"{question.topic} "
                        f"(not answered)"
                    ):
                        st.markdown("**Question**")
                        st.write(question.question)
                        st.info("No answer was submitted.")

                    continue

                latest = attempts[-1]

                with st.expander(
                    f"Question "
                    f"{question.question_id}"
                    f" — "
                    f"{question.topic} "
                    f"({latest.evaluation.overall_score}/10, "
                    f"{len(attempts)} attempt(s))"
                ):
                    st.markdown("**Question**")
                    st.write(question.question)

                    st.markdown("**Options**")
                    render_question_options(question)

                    for attempt in attempts:
                        picked = (attempt.candidate_answer[:1]
                                  if attempt.candidate_answer
                                  else "")
                        picked_index = (
                            "ABCD".index(picked)
                            if picked in "ABCD"
                            else None
                        )

                        st.markdown(
                            f"**Attempt {attempt.attempt} "
                            f"— "
                            f"{attempt.evaluation.overall_score}"
                            f"/10**"
                        )
                        st.markdown("**Your Pick**")
                        st.write(attempt.candidate_answer)
                        render_question_options(
                            question, picked_index
                        )
                        st.markdown("**Explanation**")
                        st.write(question.explanation)
                        st.markdown("**Evaluation**")
                        render_evaluation(attempt.evaluation)
                        st.divider()

            st.divider()

            markdown = report_to_markdown(report, interview)

            st.download_button(
                "Download Report (Markdown)",
                data=markdown,
                file_name=(
                    f"interview_{interview.session_id[:8]}.md"
                ),
                mime="text/markdown",
                use_container_width=True,
            )

            if confirm_block(
                "confirm_restart",
                "Start over? This report will be cleared.",
                reset_interview,
            ):
                pass
            elif st.button(
                "Start New Interview",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.confirm_restart = True
                st.rerun()

    # ----------------------------------------------
    # ASKING
    # ----------------------------------------------

    elif interview.status == InterviewState.ASKING:
        total_questions = interview.number_of_questions

        # Free navigation: any question viewable, no
        # answer required to move.
        st.session_state.view_index = min(
            max(st.session_state.view_index, 0),
            total_questions - 1,
        )
        view_index = st.session_state.view_index
        question = interview.questions[view_index]
        is_current = (
            view_index
            == interview.current_question_index
        )

        st.session_state.visited.add(question.question_id)

        answered = controller.answered_count(interview)

        st.progress(answered / total_questions)
        st.caption(
            f"Question {question.question_id} "
            f"of {total_questions} "
            f"· Answered {answered}"
        )

        if interview.time_limit_minutes:
            left = controller.remaining_seconds(interview)

            if left is not None:
                minutes, seconds = divmod(left, 60)
                st.caption(
                    f"⏱ {minutes:02d}:{seconds:02d} left"
                )

        st.divider()

        back_col, fwd_col, _ = st.columns([1, 1, 4])

        with back_col:
            if st.button(
                "◀ Back",
                use_container_width=True,
                disabled=view_index == 0,
            ):
                go_to(view_index - 1)

        with fwd_col:
            if st.button(
                "Forward ▶",
                use_container_width=True,
                disabled=view_index >= total_questions - 1,
            ):
                go_to(view_index + 1)

        st.divider()

        attempts = controller.attempts_for(
            interview, question.question_id
        )

        marked = (
            question.question_id
            in interview.marked_for_review
        )

        if question.question_id in interview.skipped:
            st.warning("⏭ Skipped — answer it anytime.")

        if marked:
            st.info("⚑ Marked for review.")

        st.subheader(question.question)
        st.caption(f"Topic: {question.topic}")

        if attempts:
            st.info(
                f"Answered {len(attempts)} time(s) — "
                f"latest score: "
                f"{attempts[-1].evaluation.overall_score}/10. "
                f"Submitting again saves a new attempt; "
                f"only the latest counts."
            )

        st.divider()

        option_labels = [
            f"{letter}. {text}"
            for letter, text in zip(
                "ABCD", question.options
            )
        ]

        selected_label = st.radio(
            "Choose one option",
            option_labels,
            index=None,
            key=f"answer_{question.question_id}",
        )

        selected_index = (
            option_labels.index(selected_label)
            if selected_label is not None
            else None
        )

        submit_col, skip_col, mark_col = st.columns(3)

        with submit_col:
            submit = st.button(
                "Submit Answer",
                type="primary",
                use_container_width=True,
            )

        with skip_col:
            skip = st.button(
                "Skip ⏭",
                use_container_width=True,
            )

        with mark_col:
            mark_label = (
                "⚑ Unmark" if marked else "⚑ Mark"
            )
            mark = st.button(
                mark_label,
                use_container_width=True,
            )

        if mark:
            controller.toggle_mark(
                interview, question.question_id
            )
            st.rerun()

        if skip:
            controller.mark_skipped(
                interview, question.question_id
            )

            if view_index + 1 < total_questions:
                go_to(view_index + 1)
            else:
                nxt = controller.first_unanswered_index(
                    interview
                )
                go_to(
                    nxt
                    if nxt is not None
                    else view_index
                )

        if submit:
            if selected_index is None:
                st.warning(
                    "Please select an option "
                    "before submitting."
                )
            else:
                try:
                    if is_current:
                        controller.submit_answer(
                            interview,
                            selected_index,
                        )
                    else:
                        controller.submit_answer_for(
                            interview,
                            question.question_id,
                            selected_index,
                        )

                        # At-the-end timing skips the feedback
                        # screen: advance immediately.
                    if (
                        st.session_state.eval_timing
                        == TIMING_AT_END
                    ):
                        controller.next_question(
                            interview
                        )
                        _advance_view(interview)

                    st.rerun()

                except Exception as error:
                    st.error(str(error))

        st.divider()

        answered = controller.answered_count(interview)

        if answered > 0:
            if confirm_block(
                "confirm_submit_test",
                f"Submit the whole test? "
                f"{answered} answered · "
                f"{controller.unanswered_count(interview)} "
                f"unanswered · "
                f"{controller.marked_count(interview)} "
                f"marked for review.",
                lambda: controller.finish_interview(
                    st.session_state.interview
                ),
            ):
                pass
            elif st.button(
                "Submit Test ✅",
                use_container_width=True,
            ):
                st.session_state.confirm_submit_test = True
                st.rerun()

    # ----------------------------------------------
    # FEEDBACK
    # ----------------------------------------------

    elif interview.status == InterviewState.FEEDBACK:
        result = interview.pending_result

        if result is None:
            st.error(
                "Evaluation result is missing."
            )
        else:
            question_number = result.question.question_id

            st.progress(
                question_number
                / interview.number_of_questions
            )
            st.caption(
                f"Question {question_number} "
                f"evaluation"
            )

            st.divider()

            was_correct = (
                result.evaluation.overall_score >= 10
            )
            correct_letter = "ABCD"[
                result.question.correct_index
            ]

            if was_correct:
                st.success("✅ Correct!")
            else:
                st.error(
                    f"❌ Wrong — correct answer: "
                    f"{correct_letter}. "
                    f"{result.question.options[result.question.correct_index]}"
                )

            st.metric(
                "Question Score",
                f"{result.evaluation.overall_score:.2f}/10",
            )

            evaluation = result.evaluation

            st.markdown(
                f"Correctness {evaluation.scores.correctness}/10"
                f" · Depth "
                f"{evaluation.scores.technical_depth}/10"
                f" · Clarity {evaluation.scores.clarity}/10"
                f" · Completeness "
                f"{evaluation.scores.completeness}/10"
            )

            st.caption(
                summarize_feedback(
                    result.question.explanation
                )
            )

            with st.expander("Your answer"):
                st.write(result.candidate_answer)

            with st.expander("Explanation"):
                st.write(result.question.explanation)

            st.divider()

            if st.button(
                "Next Question",
                type="primary",
                use_container_width=True,
            ):
                controller.next_question(interview)

                _advance_view(interview)

                st.rerun()
