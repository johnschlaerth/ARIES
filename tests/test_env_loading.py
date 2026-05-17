import os

from aries.utils import load_dotenv_if_present


def test_dotenv_loader_reads_project_and_parent_env(tmp_path, monkeypatch):
    project = tmp_path / "aries_mvp"
    project.mkdir()
    parent_env = tmp_path / ".env"
    project_env = project / ".env"
    parent_env.write_text("OPENAI_API_KEY=parent_key\n", encoding="utf-8")
    project_env.write_text("ARIES_TEST_VALUE=project_value\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ARIES_TEST_VALUE", raising=False)

    loaded = load_dotenv_if_present(project)

    assert parent_env in loaded
    assert project_env in loaded
    assert os.environ["OPENAI_API_KEY"] == "parent_key"
    assert os.environ["ARIES_TEST_VALUE"] == "project_value"


def test_dotenv_loader_does_not_override_shell_env(tmp_path, monkeypatch):
    project = tmp_path / "aries_mvp"
    project.mkdir()
    (project / ".env").write_text("OPENAI_API_KEY=file_key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "shell_key")

    load_dotenv_if_present(project)

    assert os.environ["OPENAI_API_KEY"] == "shell_key"
