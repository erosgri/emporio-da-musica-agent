from __future__ import annotations

from emporio_agent.config import Settings


def test_empty_openai_base_url_is_ignored() -> None:
    settings = Settings.model_validate({"openai_base_url": ""})

    assert settings.openai_base_url is None
    assert settings.uses_structured_output is True


def test_alternative_provider_disables_structured_output() -> None:
    settings = Settings.model_validate(
        {
            "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "model": "gemini-3.8-flash",
        }
    )

    assert settings.uses_structured_output is False
