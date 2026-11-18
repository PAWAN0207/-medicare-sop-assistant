"""The .env loader: file values are used, real environment variables always win."""
import os

from sopassist.config import load_dotenv


def test_loads_values_and_respects_existing_env(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nPROVIDER=openai_compat\nLLM_API_KEY="abc123"\nLLM_MODEL=m1  # inline\nTOP_K=9\n\nbad line\n')
    monkeypatch.delenv("SOPASSIST_NO_DOTENV", raising=False)
    for k in ("PROVIDER", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TOP_K", "3")                    # already set -> must not be overridden
    assert load_dotenv(f) is True
    assert os.environ["PROVIDER"] == "openai_compat"
    assert os.environ["LLM_API_KEY"] == "abc123"        # quotes stripped
    assert os.environ["LLM_MODEL"] == "m1"              # inline comment stripped
    assert os.environ["TOP_K"] == "3"
    for k in ("PROVIDER", "LLM_API_KEY", "LLM_MODEL"):  # monkeypatch cannot undo direct writes
        os.environ.pop(k, None)


def test_missing_file_and_opt_out(tmp_path, monkeypatch):
    monkeypatch.delenv("SOPASSIST_NO_DOTENV", raising=False)
    assert load_dotenv(tmp_path / "nope.env") is False
    f = tmp_path / ".env"
    f.write_text("SHOULD_NOT_LOAD=1\n")
    monkeypatch.setenv("SOPASSIST_NO_DOTENV", "1")
    assert load_dotenv(f) is False
    assert "SHOULD_NOT_LOAD" not in os.environ
