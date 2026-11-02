from __future__ import annotations

from pathlib import Path

import pytest

from emporio_agent.bootstrap import Application, build_application
from emporio_agent.config import PROJECT_ROOT, Settings


@pytest.fixture(scope="session")
def application(tmp_path_factory: pytest.TempPathFactory) -> Application:
    processed_dir = tmp_path_factory.mktemp("processed")
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        artifacts_dir=PROJECT_ROOT / "artefatos_projeto",
        processed_dir=Path(processed_dir),
    )
    return build_application(settings, force_ingestion=True)
