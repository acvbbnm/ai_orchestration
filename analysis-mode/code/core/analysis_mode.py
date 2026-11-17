"""Validate inputs and findings without executing the analysis target."""
import os
from pathlib import Path

from agents.claude_analyst import AnalystError, ClaudeAnalyst
from schemas.finding import Finding


class AnalysisError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def run_analysis(binary_path, goal, *, analyst=None, timeout=300):
    """Return validated Finding objects; an empty list means no findings."""
    if not isinstance(goal, str) or not goal.strip():
        raise AnalysisError("INVALID_INPUT", "goal must be a nonempty string")
    try:
        raw_path = os.fspath(binary_path)
        if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
            raise ValueError("binary_path must be a nonempty filesystem path")
        path = Path(raw_path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError("binary_path must identify a regular file")
        with path.open("rb") as stream:
            stream.read(0)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise AnalysisError("INVALID_INPUT", f"Invalid binary path: {exc}") from exc
    try:
        adapter = ClaudeAnalyst(timeout=timeout) if analyst is None else analyst
        data = adapter.analyze(str(path), goal.strip())
    except AnalystError as exc:
        raise AnalysisError(exc.code, str(exc)) from exc
    if not isinstance(data, dict) or set(data) != {"findings"}:
        raise AnalysisError("SCHEMA_MISMATCH", "Expected an object containing only findings")
    if not isinstance(data["findings"], list):
        raise AnalysisError("SCHEMA_MISMATCH", "findings must be a list")
    findings = []
    for index, item in enumerate(data["findings"]):
        if not isinstance(item, dict):
            raise AnalysisError("SCHEMA_MISMATCH", f"findings[{index}] must be an object")
        try:
            findings.append(Finding(**item))
        except ValueError as exc:
            raise AnalysisError("SCHEMA_MISMATCH", f"Invalid findings[{index}]: {exc}") from exc
    return findings
