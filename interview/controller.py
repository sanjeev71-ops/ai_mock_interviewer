import uuid
from datetime import datetime, timedelta, timezone

from models.evaluation import Evaluation
from models.interview import (
    InterviewSession,
    QuestionResult,
)

from services.groq_service import GroqService
from services.question_generator import QuestionGenerator
from services.evaluator import AnswerEvaluator
from services.report_generator import ReportGenerator

from config.settings import GROQ_MODEL

from interview.state import InterviewState

from interview.validation import (
    validate_interview_configuration,
    validate_question_set,
    validate_selected_option,
)


class InterviewController:
    def __init__(self):
        self.groq = GroqService()

        self.question_generator = (
            QuestionGenerator(groq=self.groq)
        )

        self.evaluator = AnswerEvaluator(groq=self.groq)

        self.report_generator = (
            ReportGenerator(groq=self.groq)
        )

    def _configure_model(
        self,
        model: str | None,
    ) -> GroqService:
        """Fresh shared service so the picked model leads
        the failover chain for this interview."""
        groq = GroqService(model=model or GROQ_MODEL)

        self.groq = groq

        self.question_generator = (
            QuestionGenerator(groq=groq)
        )

        self.evaluator = AnswerEvaluator(groq=groq)

        self.report_generator = (
            ReportGenerator(groq=groq)
        )

        return groq

    # ------------------------------------------
    # Create interview
    # ------------------------------------------

    def create_interview(
        self,
        role: str,
        experience_level: str,
        difficulty: str,
        number_of_questions: int,
        model: str | None = None,
        time_limit_minutes: int | None = None,
    ):
        validate_interview_configuration(
            role,
            experience_level,
            difficulty,
            number_of_questions,
        )

        groq = self._configure_model(model)

        question_set = (
            self.question_generator.generate(
                role=role,
                experience_level=experience_level,
                difficulty=difficulty,
                number_of_questions=
                    number_of_questions,
            )
        )

        validate_question_set(
            question_set.questions
        )

        return InterviewSession(
            session_id=str(
                uuid.uuid4()
            ),

            role=role,

            experience_level=
                experience_level,

            difficulty=difficulty,

            number_of_questions=
                number_of_questions,

            model=(
                groq.active_model or groq.model
            ),

            time_limit_minutes=time_limit_minutes,

            started_at=datetime.now(timezone.utc).isoformat(),

            questions=
                question_set.questions,

            current_question_index=0,

            status=InterviewState.ASKING,
        )

    # ------------------------------------------
    # Get current question
    # ------------------------------------------

    def get_current_question(
        self,
        session: InterviewSession,
    ):
        if session.status != InterviewState.ASKING:
            return None

        if (
            session.current_question_index
            >= len(session.questions)
        ):
            return None

        return session.questions[
            session.current_question_index
        ]

    # ------------------------------------------
    # Attempt history (latest attempt wins)
    # ------------------------------------------

    def get_question_by_id(
        self,
        session: InterviewSession,
        question_id: int,
    ):
        for question in session.questions:
            if question.question_id == question_id:
                return question

        raise ValueError(
            f"Question {question_id} not found."
        )

    def attempts_for(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> list[QuestionResult]:
        return [
            result
            for result in session.results
            if result.question.question_id == question_id
        ]

    def get_latest_result(
        self,
        session: InterviewSession,
        question_id: int,
    ):
        attempts = self.attempts_for(session, question_id)

        if not attempts:
            return None

        return attempts[-1]

    def is_answered(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> bool:
        return (
            self.get_latest_result(session, question_id)
            is not None
        )

    def latest_results(
        self,
        session: InterviewSession,
    ) -> list[QuestionResult]:
        """Latest attempt per question, in question order."""
        ordered = []

        for question in session.questions:
            result = self.get_latest_result(
                session, question.question_id
            )

            if result is not None:
                ordered.append(result)

        return ordered

    def answered_count(
        self,
        session: InterviewSession,
    ) -> int:
        return len(self.latest_results(session))

    def first_unanswered_index(
        self,
        session: InterviewSession,
    ):
        for index, question in enumerate(session.questions):
            if not self.is_answered(
                session, question.question_id
            ):
                return index

        return None

    # ------------------------------------------
    # Submit answer
    # ------------------------------------------

    def submit_answer(
        self,
        session: InterviewSession,
        selected_index: int | None,
    ):
        if session.status != InterviewState.ASKING:
            raise ValueError(
                "An answer cannot be submitted "
                "in the current interview state."
            )

        question = self.get_current_question(
            session
        )

        if question is None:
            raise ValueError(
                "No active question."
            )

        return self._evaluate_and_store(
            session,
            question,
            selected_index,
        )

    def submit_answer_for(
        self,
        session: InterviewSession,
        question_id: int,
        selected_index: int | None,
    ):
        """Answer a specific (viewed) question.

        Used for re-attempts of already-answered questions.
        Same ASKING -> EVALUATING -> FEEDBACK transitions.
        """
        if session.status != InterviewState.ASKING:
            raise ValueError(
                "An answer cannot be submitted "
                "in the current interview state."
            )

        question = self.get_question_by_id(
            session, question_id
        )

        return self._evaluate_and_store(
            session,
            question,
            selected_index,
        )

    def _evaluate_and_store(
        self,
        session: InterviewSession,
        question,
        selected_index: int | None,
    ):
        """Score MCQ answers deterministically in Python.

        No LLM call: correctness is exact (selected option
        vs correct option). The explanation generated with
        the question becomes the feedback.
        """
        validate_selected_option(
            selected_index,
            option_count=len(question.options),
        )

        session.status = (
            InterviewState.EVALUATING
        )

        correct = selected_index == question.correct_index
        score = 10.0 if correct else 0.0
        letter = "ABCD"[selected_index]
        correct_letter = "ABCD"[question.correct_index]

        evaluation = Evaluation(
            scores={
                "correctness": score,
                "technical_depth": score,
                "clarity": score,
                "completeness": score,
            },
            strengths=(
                [f"Correct answer: {letter}"]
                if correct
                else []
            ),
            weaknesses=(
                []
                if correct
                else [
                    f"Correct answer was {correct_letter}: "
                    f"{question.options[question.correct_index]}"
                ]
            ),
            feedback=question.explanation,
        )

        result = QuestionResult(
            question=question,

            candidate_answer=(
                f"{letter}. "
                f"{question.options[selected_index]}"
            ),

            evaluation=evaluation,

            attempt=(
                len(
                    self.attempts_for(
                        session, question.question_id
                    )
                )
                + 1
            ),
        )

        session.results.append(result)

        self._clear_skipped(session, question.question_id)

        session.pending_result = result

        session.status = (
            InterviewState.FEEDBACK
        )

        return result

    # ------------------------------------------
    # Move to next question
    # ------------------------------------------

    def next_question(
        self,
        session: InterviewSession,
    ):
        if session.status != InterviewState.FEEDBACK:
            raise ValueError(
                "Cannot move to the next question "
                "from the current state."
            )

        session.pending_result = None

        # Land on the first unanswered question so
        # re-attempts of earlier questions resume
        # correctly. For a purely sequential interview
        # this is exactly current_index + 1.
        first_unanswered = self.first_unanswered_index(
            session
        )

        if first_unanswered is None:
            session.current_question_index = (
                session.number_of_questions
            )
            session.status = (
                InterviewState.COMPLETED
            )
        else:
            session.current_question_index = (
                first_unanswered
            )
            session.status = (
                InterviewState.ASKING
            )

    # ------------------------------------------
    # Generate final report
    # ------------------------------------------

    def generate_report(
        self,
        session: InterviewSession,
    ):
        if session.status != InterviewState.COMPLETED:
            raise ValueError(
                "Interview is not completed."
            )

        return self.report_generator.generate(
            session
        )

    # ------------------------------------------
    # Review flags (free navigation)
    # ------------------------------------------

    def status_of(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> str:
        """answered-marked / answered / marked / skipped / todo."""
        self.get_question_by_id(session, question_id)

        answered = self.is_answered(session, question_id)
        marked = question_id in session.marked_for_review

        if answered and marked:
            return "answered-marked"

        if answered:
            return "answered"

        if marked:
            return "marked"

        if question_id in session.skipped:
            return "skipped"

        return "todo"

    def toggle_mark(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> bool:
        self.get_question_by_id(session, question_id)

        if question_id in session.marked_for_review:
            session.marked_for_review.remove(question_id)
            return False

        session.marked_for_review.append(question_id)
        return True

    def mark_skipped(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> None:
        self.get_question_by_id(session, question_id)

        if (
            not self.is_answered(session, question_id)
            and question_id not in session.skipped
        ):
            session.skipped.append(question_id)

    def _clear_skipped(
        self,
        session: InterviewSession,
        question_id: int,
    ) -> None:
        if question_id in session.skipped:
            session.skipped.remove(question_id)

    def marked_count(
        self,
        session: InterviewSession,
    ) -> int:
        return len(session.marked_for_review)

    def unanswered_count(
        self,
        session: InterviewSession,
    ) -> int:
        return (
            session.number_of_questions
            - self.answered_count(session)
        )

    # ------------------------------------------
    # Explicit finish (works with skips left)
    # ------------------------------------------

    def finish_interview(
        self,
        session: InterviewSession,
        allow_empty: bool = False,
    ) -> None:
        if session.status not in (
            InterviewState.ASKING,
            InterviewState.FEEDBACK,
        ):
            raise ValueError(
                "Interview cannot be finished "
                "from the current state."
            )

        if (
            not allow_empty
            and self.answered_count(session) == 0
        ):
            raise ValueError(
                "Answer at least one question "
                "before finishing."
            )

        session.pending_result = None
        session.current_question_index = (
            session.number_of_questions
        )
        session.status = InterviewState.COMPLETED

    # ------------------------------------------
    # Whole-test timer
    # ------------------------------------------

    def deadline(
        self,
        session: InterviewSession,
    ):
        if not session.time_limit_minutes:
            return None

        if not session.started_at:
            return None

        try:
            start = datetime.fromisoformat(
                session.started_at
            )
        except ValueError:
            return None

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        return start + timedelta(
            minutes=session.time_limit_minutes
        )

    def remaining_seconds(
        self,
        session: InterviewSession,
    ) -> int | None:
        limit_at = self.deadline(session)

        if limit_at is None:
            return None

        left = (
            limit_at - datetime.now(timezone.utc)
        ).total_seconds()

        return max(0, int(left))

    def is_expired(
        self,
        session: InterviewSession,
    ) -> bool:
        return self.remaining_seconds(session) == 0 and (
            self.deadline(session) is not None
        )

    def enforce_expiry(
        self,
        session: InterviewSession,
    ) -> bool:
        """Finish immediately when time runs out.

        The on-screen draft (if any) is discarded.
        Returns True when it just expired the session.
        """
        if session.status == InterviewState.COMPLETED:
            return False

        if not self.is_expired(session):
            return False

        session.pending_result = None
        session.current_question_index = (
            session.number_of_questions
        )
        session.status = InterviewState.COMPLETED

        return True
