def validate_interview_configuration(
    role: str,
    experience_level: str,
    difficulty: str,
    number_of_questions: int,
):
    if not role.strip():
        raise ValueError(
            "Job role cannot be empty."
        )

    if not experience_level.strip():
        raise ValueError(
            "Experience level cannot be empty."
        )

    if not difficulty.strip():
        raise ValueError(
            "Difficulty cannot be empty."
        )

    if not 1 <= number_of_questions <= 10:
        raise ValueError(
            "Number of questions must be between 1 and 10."
        )


def validate_question_set(questions):
    if not questions:
        raise ValueError(
            "Question generator returned no questions."
        )

    question_ids = [
        question.question_id
        for question in questions
    ]

    if len(question_ids) != len(set(question_ids)):
        raise ValueError(
            "Duplicate question IDs detected."
        )

    question_texts = [
        question.question.strip().lower()
        for question in questions
    ]

    if len(question_texts) != len(set(question_texts)):
        raise ValueError(
            "Duplicate questions detected."
        )


def validate_selected_option(
    selected_index,
    option_count: int = 4,
):
    if selected_index is None:
        raise ValueError(
            "Please select an option."
        )

    if not isinstance(selected_index, int) or isinstance(
        selected_index, bool
    ):
        raise ValueError(
            "Invalid option selected."
        )

    if not 0 <= selected_index < option_count:
        raise ValueError(
            "Invalid option selected."
        )
