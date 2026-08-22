from pathlib import Path


def test_ac08_onprem_layout():
    root = Path("/workspace")
    assert (root / "docker-compose.yml").exists()
    compose = (root / "docker-compose.yml").read_text()
    assert "gemini" not in compose.lower()
    assert "firebase" not in compose.lower()
    assert "s3" not in compose.lower()
    assert "clamav" in compose
    assert "postgres" in compose
    assert "nginx" in compose
    env = (root / ".env.example").read_text()
    assert "GEMINI" not in env
    readme = (root / "README.md").read_text()
    assert "docker compose" in readme.lower() or "bootstrap" in readme
