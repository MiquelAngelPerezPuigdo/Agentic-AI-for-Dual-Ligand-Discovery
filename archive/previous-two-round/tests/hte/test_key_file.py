from pathlib import Path

import pytest

from hte.scoring import operator_api_key, score_candidates
from test_prompt_caching import inputs, install_mock


def test_environment_key_takes_precedence(tmp_path, monkeypatch):
    path = tmp_path / "anthropic.key"
    path.write_text("PASTE_YOUR_ANTHROPIC_API_KEY_HERE\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic_environment_key")
    assert operator_api_key(path) == "synthetic_environment_key"


def test_bad_key_files_never_echo_or_execute_contents(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    path = tmp_path / "anthropic.key"
    for contents in ["", "PASTE_YOUR_ANTHROPIC_API_KEY_HERE", "ANTHROPIC_API_KEY=sk-ant-fixture",
                     "sk-ant-fixture\nsecond-line", '"sk-ant-fixture"', "$(touch executed)"]:
        path.write_text(contents)
        with pytest.raises(ValueError) as error:
            operator_api_key(path)
        assert "sk-ant-fixture" not in str(error.value)
    assert not (tmp_path / "executed").exists()


def test_scoring_uses_file_key_without_export_or_persisting_it(tmp_path, monkeypatch):
    calls, _ = install_mock(monkeypatch)
    import anthropic
    mock_client = anthropic.Anthropic
    received = []

    def client(**kwargs):
        received.append(kwargs["api_key"])
        return mock_client(**kwargs)

    monkeypatch.setattr(anthropic, "Anthropic", client)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    fake_key = "sk-ant-SYNTHETIC_KEY_FILE_FIXTURE"
    Path("anthropic.key").write_text("\ufeff" + fake_key + "\n")
    config, inventory, pairs = inputs()
    output = tmp_path / "scoring"
    score_candidates(config, inventory, pairs, {}, [], output)
    assert received == [fake_key] and len(calls) == 3
    import os
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert all(fake_key not in path.read_text() for path in output.rglob("*") if path.is_file())
