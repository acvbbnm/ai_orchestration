import argparse
import json
import runpy
import subprocess
import sys
from unittest.mock import Mock

import pytest

import agents.claude_analyst as adapter_module
from agents.claude_analyst import AnalystError, ClaudeAnalyst
from core.analysis_cli import main, register_analyze_subcommand
from core.analysis_mode import AnalysisError, run_analysis
from schemas.finding import Finding


GOOD = {"location": "0x401000", "kind": "bounds", "evidence": "unchecked copy", "confidence": 0.8}


@pytest.fixture(autouse=True)
def cli_stub(monkeypatch):
    runner = Mock(return_value=subprocess.CompletedProcess(
        [], 0, json.dumps({"findings": [GOOD]}), ""))
    monkeypatch.delenv("CLAUDE_BIN", raising=False)
    monkeypatch.setattr(adapter_module, "resolve_cli", lambda name: "C:/Claude Tools/claude.exe")
    monkeypatch.setattr(adapter_module, "get_sanitized_env", lambda: {"SAFE": "1"})
    monkeypatch.setattr(adapter_module.subprocess, "run", runner)
    return runner


@pytest.fixture
def binary(tmp_path):
    path = tmp_path / "sample with spaces.bin"
    path.write_bytes(b"not an executable")
    return path


def test_success_and_invocation(binary, cli_stub):
    findings = run_analysis(binary, " inspect copies ", timeout=12)
    assert len(findings) == 1 and isinstance(findings[0], Finding)
    assert findings[0].dict() == GOOD
    argv = cli_stub.call_args.args[0]
    kwargs = cli_stub.call_args.kwargs
    assert isinstance(argv, list) and argv[0] == "C:/Claude Tools/claude.exe"
    assert argv[argv.index("--allowedTools") + 1:] == ["mcp__plugin_ida-pro-mcp_idalib__*", "Read"]
    assert argv[argv.index("--tools") + 1] == "Read"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert kwargs["shell"] is False and kwargs["timeout"] == 12
    assert kwargs["env"] == {"SAFE": "1"}
    payload = json.loads(kwargs["input"].split("\nINPUT:\n", 1)[1])
    assert payload == {"binary_path": str(binary.resolve()), "goal": "inspect copies"}
    assert str(binary) not in argv
    assert binary.read_bytes() == b"not an executable"
    cli_stub.assert_called_once()


@pytest.mark.parametrize("goal", ["", " \n", None, 123])
def test_invalid_goal(binary, cli_stub, goal):
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, goal)
    assert error.value.code == "INVALID_INPUT"
    cli_stub.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "directory", "empty", "null", "nul"])
def test_invalid_path(tmp_path, cli_stub, kind):
    path = {"missing": tmp_path / "missing", "directory": tmp_path,
            "empty": "", "null": None, "nul": "a\x00b"}[kind]
    with pytest.raises(AnalysisError) as error:
        run_analysis(path, "inspect")
    assert error.value.code == "INVALID_INPUT"
    cli_stub.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "5"])
def test_invalid_timeout(binary, cli_stub, timeout):
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, "inspect", timeout=timeout)
    assert error.value.code == "INVALID_INPUT"
    cli_stub.assert_not_called()


@pytest.mark.parametrize("failure,code", [
    (subprocess.TimeoutExpired("claude", 1), "TIMEOUT"),
    (FileNotFoundError("missing CLI"), "CLI_FAILED"),
    (PermissionError("denied"), "CLI_FAILED"),
])
def test_execution_errors(binary, cli_stub, failure, code):
    cli_stub.side_effect = failure
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, "inspect")
    assert error.value.code == code


def test_missing_cli(binary, cli_stub, monkeypatch):
    monkeypatch.setattr(adapter_module, "resolve_cli", lambda name: None)
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, "inspect")
    assert error.value.code == "CLI_FAILED"
    cli_stub.assert_not_called()


def test_nonzero_exit(binary, cli_stub):
    cli_stub.return_value = subprocess.CompletedProcess([], 7, '{"findings": []}', "failure")
    with pytest.raises(AnalysisError, match="code 7") as error:
        run_analysis(binary, "inspect")
    assert error.value.code == "CLI_FAILED"


@pytest.mark.parametrize("text", ["", "not JSON", '```json\n{"findings": []}\n```'])
def test_invalid_json(binary, cli_stub, text):
    cli_stub.return_value.stdout = text
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, "inspect")
    assert error.value.code == "INVALID_JSON"


@pytest.mark.parametrize("payload", [None, [], {}, {"findings": None}, {"findings": {}},
    {"findings": [], "extra": 1}, {"findings": [None]}, {"findings": [{}]},
    {"findings": [GOOD, {**GOOD, "evidence": " "}]}])
def test_schema_errors(binary, cli_stub, payload):
    cli_stub.return_value.stdout = json.dumps(payload)
    with pytest.raises(AnalysisError) as error:
        run_analysis(binary, "inspect")
    assert error.value.code == "SCHEMA_MISMATCH"


@pytest.mark.parametrize("field,value", [
    ("location", ""), ("kind", " \n"), ("evidence", 7), ("evidence", None),
    ("confidence", -0.1), ("confidence", 1.1), ("confidence", True),
    ("confidence", "0.5"), ("confidence", float("nan")),
    ("confidence", float("inf")), ("extra", "unexpected"),
])
def test_finding_validation(field, value):
    with pytest.raises(ValueError):
        Finding(**{**GOOD, field: value})


@pytest.mark.parametrize("confidence", [0, 1, 0.5])
def test_confidence_boundaries(confidence):
    assert Finding(**{**GOOD, "confidence": confidence}).confidence == confidence


def test_empty_findings(binary, cli_stub):
    cli_stub.return_value.stdout = '{"findings": []}'
    assert run_analysis(binary, "inspect") == []


def test_registration_preserves_existing_command(binary, capsys):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    existing = lambda args: 23
    subparsers.add_parser("run").set_defaults(func=existing)
    register_analyze_subcommand(subparsers)
    old = parser.parse_args(["run"])
    assert old.func is existing and old.func(old) == 23
    args = parser.parse_args(["analyze", str(binary), "--goal", "inspect"])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out) == {"findings": [GOOD]}


@pytest.mark.parametrize("mode,exit_code,code", [
    ("input", 2, "INVALID_INPUT"), ("json", 1, "INVALID_JSON"),
    ("timeout", 1, "TIMEOUT"), ("exit", 1, "CLI_FAILED"),
    ("schema", 1, "SCHEMA_MISMATCH"),
])
def test_cli_errors(binary, cli_stub, capsys, mode, exit_code, code):
    if mode == "json":
        cli_stub.return_value.stdout = "broken"
    elif mode == "timeout":
        cli_stub.side_effect = subprocess.TimeoutExpired("claude", 1)
    elif mode == "exit":
        cli_stub.return_value.returncode = 9
    elif mode == "schema":
        cli_stub.return_value.stdout = "{}"
    goal = " " if mode == "input" else "inspect"
    assert main([str_arg for str_arg in ["analyze", str(binary), "--goal", goal]]) == exit_code
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"]["code"] == code


def test_required_cli_arguments(cli_stub):
    with pytest.raises(SystemExit) as error:
        main(["analyze", "sample.bin"])
    assert error.value.code == 2
    cli_stub.assert_not_called()


def test_module_entrypoint(binary, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["analysis_cli", "analyze", str(binary), "--goal", "inspect"])
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        with pytest.raises(SystemExit) as error:
            runpy.run_module("core.analysis_cli", run_name="__main__")
    assert error.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"findings": [GOOD]}
