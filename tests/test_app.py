from pathlib import Path
from streamlit.testing.v1 import AppTest


def click(app, label):
    return next(b for b in app.button if b.label == label).click().run(timeout=45)


def test_ui_step_commit_resume_and_comparison():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    click(app, "创建 / 重置实验")
    click(app, "下一阶段")
    assert len(app.session_state.runtime.events) == 1
    click(app, "运行剩余阶段")
    assert app.session_state.runtime.status == "committed"
    click(app, "恢复任务并运行测试")
    assert app.session_state.continuation["status"] == "passed"
    click(app, "运行三组对照")
    assert len(app.session_state.comparison) == 3
    assert not app.exception
    app.session_state.case.close()


def test_ui_rejected_candidate_disables_resume():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    app.selectbox[0].select("丢失早期约束").run()
    click(app, "创建 / 重置实验")
    click(app, "运行剩余阶段")
    assert app.session_state.runtime.status == "rejected"
    assert next(b for b in app.button if b.label == "恢复任务并运行测试").disabled
    assert not app.exception
    app.session_state.case.close()
