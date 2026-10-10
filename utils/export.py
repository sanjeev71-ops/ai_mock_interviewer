"""Markdown export for the final interview report."""


def report_to_markdown(report, interview) -> str:
    lines = [
        "# AI Mock Interview Report",
        "",
        f"- Role: {interview.role}",
        f"- Experience: {interview.experience_level}",
        f"- Difficulty: {interview.difficulty}",
        f"- Session: {interview.session_id}",
        "",
        "## Final Performance",
        "",
        f"- Overall: {report.overall_score:.2f}/10",
        f"- Technical: {report.technical_score:.2f}/10",
        f"- Communication: {report.communication_score:.2f}/10",
        "",
        "## Topic Performance",
        "",
    ]

    if report.topic_performance:
        for topic, score in report.topic_performance.items():
            lines.append(f"- {topic}: {score:.2f}/10")
    else:
        lines.append("- No topic data.")

    lines += ["", "## Strengths", ""]

    lines += (
        [f"- {item}" for item in report.strengths]
        if report.strengths
        else ["- None recorded."]
    )

    lines += ["", "## Weaknesses", ""]

    lines += (
        [f"- {item}" for item in report.weaknesses]
        if report.weaknesses
        else ["- None recorded."]
    )

    lines += ["", "## Recommendations", ""]

    lines += (
        [f"- {item}" for item in report.recommendations]
        if report.recommendations
        else ["- None recorded."]
    )

    lines += ["", "## Question-by-Question", ""]

    for result in interview.results:
        question = result.question
        evaluation = result.evaluation
        letters = "ABCD"
        correct_letter = letters[question.correct_index]

        lines += [
            f"### Question {question.question_id} — {question.topic} "
            f"(Attempt {result.attempt})",
            "",
            question.question,
            "",
        ]

        for pos, option in enumerate(question.options):
            marker = " ✅" if pos == question.correct_index else ""
            lines.append(f"- {letters[pos]}. {option}{marker}")

        lines += [
            "",
            f"Selected: {result.candidate_answer}",
            f"Correct: {correct_letter}. "
            f"{question.options[question.correct_index]}",
            f"Outcome: "
            f"{'Correct' if evaluation.overall_score >= 10 else 'Wrong'}",
            "",
            f"Scores: correctness "
            f"{evaluation.scores.correctness}/10, "
            f"technical depth "
            f"{evaluation.scores.technical_depth}/10, "
            f"clarity {evaluation.scores.clarity}/10, "
            f"completeness "
            f"{evaluation.scores.completeness}/10, "
            f"overall {evaluation.overall_score}/10",
            "",
            f"Explanation: {question.explanation}",
            "",
            f"Feedback: {evaluation.feedback}",
            "",
        ]

    return "\n".join(lines)
