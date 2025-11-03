from mentorium_core import ProgressReport, ParentProfile


def test_progress_report_summary() -> None:
    report = ProgressReport(
        learner_id="demo",
        parent=ParentProfile(parent_chat_id="demo", parent_email="demo@example.com"),
        reporting_period="неделю",
        strengths=["Хорошо справился с проектом по Midjourney"],
        focus_areas=["Повторить работу в Google Colab"],
        upcoming_milestones=["Запланировать консультацию с наставником"],
    )

    summary = report.summary()

    assert "Mentorium" in summary
    assert "Повторить" in summary
