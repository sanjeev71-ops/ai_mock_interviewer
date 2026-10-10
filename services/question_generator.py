import time

from models.question import Question, QuestionSet
from services.groq_service import GroqService

from utils.topic_blueprints import ROLE_TOPICS
from utils.difficulty import DIFFICULTY_GUIDELINES
from utils.topic_distribution import (
    build_topic_distribution,
)
from utils.duplicate_detection import (
    has_duplicate_questions,
)


class QuestionGenerator:
    # Groq free-tier OTPM quota rejects large single
    # requests, so big interviews are generated in
    # batches that each fit under the token cap.
    BATCH_SIZE = 5
    MAX_TOKENS_PER_BATCH = 1000
    INTER_BATCH_PAUSE_SECONDS = 8

    def __init__(self, groq=None):
        self.groq = groq or GroqService()

    def generate(
        self,
        role: str,
        experience_level: str,
        difficulty: str,
        number_of_questions: int,
        max_attempts: int = 3,
    ) -> QuestionSet:
        if role not in ROLE_TOPICS:
            raise ValueError(
                f"Unsupported role: {role}"
            )

        if difficulty not in DIFFICULTY_GUIDELINES:
            raise ValueError(
                f"Unsupported difficulty: {difficulty}"
            )

        topics = ROLE_TOPICS[role]

        topic_distribution = (
            build_topic_distribution(
                topics,
                number_of_questions,
            )
        )

        difficulty_info = (
            DIFFICULTY_GUIDELINES[difficulty]
        )

        batches = [
            topic_distribution[index:index + self.BATCH_SIZE]
            for index in range(
                0, len(topic_distribution), self.BATCH_SIZE
            )
        ]

        all_questions: list[Question] = []
        last_error = None

        for batch_number, batch_topics in enumerate(batches):
            id_start = (
                batch_number * self.BATCH_SIZE + 1
            )

            batch_set = None

            for _ in range(max_attempts):
                try:
                    data = self.groq.generate_json(
                        self._system_prompt(),
                        self._batch_prompt(
                            role=role,
                            experience_level=experience_level,
                            difficulty=difficulty,
                            difficulty_info=difficulty_info,
                            batch_topics=batch_topics,
                            id_start=id_start,
                        ),
                        max_tokens=(
                            self.MAX_TOKENS_PER_BATCH
                        ),
                    )

                    batch_set = (
                        QuestionSet.model_validate(data)
                    )

                    self.validate_questions(
                        batch_set,
                        role,
                        experience_level,
                        difficulty,
                        batch_topics,
                        id_start=id_start,
                    )

                    break

                except Exception as error:
                    last_error = error
                    batch_set = None

            if batch_set is None:
                raise RuntimeError(
                    "Unable to generate a valid interview "
                    f"after {max_attempts} attempts: {last_error}"
                )

            all_questions.extend(batch_set.questions)

            if batch_number < len(batches) - 1:
                time.sleep(self.INTER_BATCH_PAUSE_SECONDS)

        try:
            self.validate_combined(all_questions)
        except ValueError as error:
            raise RuntimeError(
                "Generated questions failed final "
                f"validation: {error}"
            )

        return QuestionSet(questions=all_questions)

    # ------------------------------------------
    # Prompts
    # ------------------------------------------

    @staticmethod
    def _system_prompt() -> str:
        return """
You are a senior technical interviewer.

Generate high-quality multiple-choice technical
interview questions.

Return ONLY valid JSON.

Do not use markdown.

Do not mark the correct option in any way.
"""

    @staticmethod
    def _batch_prompt(
        role: str,
        experience_level: str,
        difficulty: str,
        difficulty_info: dict,
        batch_topics: list[str],
        id_start: int,
    ) -> str:
        count = len(batch_topics)
        id_end = id_start + count - 1

        first_topic_line = (
            f"{id_start}. Question {id_start} must cover:\n"
            f"   {batch_topics[0]}"
        )

        topic_lines = "\n".join(
            f"{id_start + offset}. Question "
            f"{id_start + offset} must cover:\n"
            f"   {topic}"
            for offset, topic in enumerate(batch_topics)
        )

        return f"""
Create a technical interview.

ROLE:
{role}

EXPERIENCE LEVEL:
{experience_level}

DIFFICULTY:
{difficulty}

DIFFICULTY GUIDELINES:
{difficulty_info["description"]}

EXPECTED COMPLEXITY:
{difficulty_info["expected_complexity"]}

Generate exactly {count} questions with IDs
{id_start} to {id_end}.

The questions MUST use the following topics
in the specified order:

{topic_lines}

Requirements:

1. Generate exactly {count} questions.

2. Question IDs must be sequential:
   {id_start}, {id_start + 1}, ...
   up to {id_end}.

3. {first_topic_line}

4. Continue following the topic order above.

5. Every question must match:
   - role
   - experience level
   - difficulty
   - assigned topic

6. Questions must test actual technical
   knowledge.

7. Avoid trivial questions when difficulty
   is Medium or Hard.

8. Avoid extremely advanced questions when
   difficulty is Easy.

9. Do not repeat questions.

10. Do not create questions that test
    exactly the same concept.

11. Each question should contain one
    interview question only.

12. expected_concepts must contain at most 5
    short phrases with the important concepts
    that a strong answer should address.

13. Each question MUST have exactly 4 answer
    options (A, B, C, D).

14. Exactly one option is correct. The other
    three must be plausible distractors a
    candidate could genuinely confuse.

15. Vary the position of the correct option
    across questions. Do not make every
    answer A.

16. correct_index is 0 for A, 1 for B,
    2 for C, 3 for D.

17. explanation must justify the correct
    option in at most 3 short sentences.
    Do not reveal the correct option inside
    the question text.

18. Do not provide expected answers outside
    the options.

19. Do not reveal expected_concepts in
    question text.

Return:

{{
    "questions": [
        {{
            "question_id": {id_start},
            "question": "...",
            "topic": "...",
            "difficulty": "{difficulty}",
            "expected_concepts": [
                "...",
                "..."
            ],
            "options": [
                "...",
                "...",
                "...",
                "..."
            ],
            "correct_index": 0,
            "explanation": "..."
        }}
    ]
}}
"""

    # ------------------------------------------
    # Quality validation
    # ------------------------------------------

    def validate_questions(
        self,
        question_set: QuestionSet,
        role: str,
        experience_level: str,
        difficulty: str,
        expected_topics: list[str],
        id_start: int = 1,
    ):
        questions = question_set.questions

        # --------------------------------------
        # Count
        # --------------------------------------

        if len(questions) != len(
            expected_topics
        ):
            raise ValueError(
                "Incorrect number of questions generated."
            )

        # --------------------------------------
        # IDs
        # --------------------------------------

        expected_ids = list(
            range(
                id_start,
                id_start + len(questions),
            )
        )

        actual_ids = [
            question.question_id
            for question in questions
        ]

        if actual_ids != expected_ids:
            raise ValueError(
                "Question IDs are not sequential."
            )

        # --------------------------------------
        # Topics
        # --------------------------------------

        for index, question in enumerate(
            questions
        ):
            expected_topic = (
                expected_topics[index]
            )

            if question.topic.lower() != (
                expected_topic.lower()
            ):
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has incorrect topic. "
                    f"Expected: {expected_topic}, "
                    f"Got: {question.topic}"
                )

        # --------------------------------------
        # Difficulty
        # --------------------------------------

        for question in questions:
            if question.difficulty.lower() != (
                difficulty.lower()
            ):
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has incorrect difficulty."
                )

        # --------------------------------------
        # Empty question
        # --------------------------------------

        for question in questions:
            if not question.question.strip():
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"is empty."
                )

            if not question.expected_concepts:
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has no expected concepts."
                )

        # --------------------------------------
        # Options (exactly 4, distinct, non-empty)
        # --------------------------------------

        for question in questions:
            options = question.options or []

            if len(options) != 4:
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"must have exactly 4 options."
                )

            if any(
                not option.strip() for option in options
            ):
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has an empty option."
                )

            normalized_options = [
                option.strip().lower()
                for option in options
            ]

            if len(normalized_options) != len(
                set(normalized_options)
            ):
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has duplicate options."
                )

            if not question.explanation.strip():
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"has no explanation."
                )

        # --------------------------------------
        # Exact duplicates
        # --------------------------------------

        normalized_questions = [
            question.question.strip().lower()
            for question in questions
        ]

        if len(normalized_questions) != len(
            set(normalized_questions)
        ):
            raise ValueError(
                "Duplicate questions detected."
            )

        # --------------------------------------
        # Near duplicates (keyword overlap)
        # --------------------------------------

        if has_duplicate_questions(
            questions,
            threshold=0.65,
        ):
            raise ValueError(
                "Questions are too similar to each other."
            )

        # --------------------------------------
        # Very short questions
        # --------------------------------------

        for question in questions:
            if len(
                question.question.split()
            ) < 5:
                raise ValueError(
                    f"Question "
                    f"{question.question_id} "
                    f"is suspiciously short."
                )

    def validate_combined(
        self,
        questions: list[Question],
    ) -> None:
        """Cross-batch checks over the full set."""
        expected_ids = list(
            range(1, len(questions) + 1)
        )

        actual_ids = [
            question.question_id
            for question in questions
        ]

        if actual_ids != expected_ids:
            raise ValueError(
                "Combined question IDs are not sequential."
            )

        normalized = [
            question.question.strip().lower()
            for question in questions
        ]

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Duplicate questions detected "
                "across batches."
            )

        if has_duplicate_questions(
            questions,
            threshold=0.65,
        ):
            raise ValueError(
                "Questions are too similar to each other."
            )
