from models.evaluation import Evaluation


def calculate_overall_score(evaluation: Evaluation) -> float:
    return evaluation.overall_score


def calculate_interview_score(
    evaluations: list[Evaluation],
) -> float:
    if not evaluations:
        return 0.0

    total = sum(
        evaluation.overall_score
        for evaluation in evaluations
    )

    return round(
        total / len(evaluations),
        2,
    )


def calculate_technical_score(
    evaluations: list[Evaluation],
) -> float:
    if not evaluations:
        return 0.0

    total = sum(
        (
            evaluation.scores.correctness
            + evaluation.scores.technical_depth
            + evaluation.scores.completeness
        )
        / 3
        for evaluation in evaluations
    )

    return round(
        total / len(evaluations),
        2,
    )


def calculate_communication_score(
    evaluations: list[Evaluation],
) -> float:
    if not evaluations:
        return 0.0

    total = sum(
        evaluation.scores.clarity
        for evaluation in evaluations
    )

    return round(
        total / len(evaluations),
        2,
    )
