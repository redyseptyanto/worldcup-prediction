from pathlib import Path


def test_core_doc_claims_match_repo() -> None:
    root = Path(__file__).resolve().parent.parent
    required_files = [
        root / "README.md",
        root / "PRD.md",
        root / "AGENT.md",
        root / "Makefile",
        root / "requirements.txt",
        root / "src" / "config.py",
        root / "src" / "models" / "base.py",
        root / "src" / "simulation" / "tournament.py",
    ]
    for file_path in required_files:
        assert file_path.exists(), f"Missing documented file: {file_path}"


def test_make_targets_documented_in_readme_exist() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in [
        "collect-data",
        "engineer-features",
        "train-models",
        "simulate",
        "predict",
        "serve-api",
        "serve-dashboard",
        "ingest-result",
        "scheduler-run-now",
    ]:
        assert f"{target}:" in makefile
