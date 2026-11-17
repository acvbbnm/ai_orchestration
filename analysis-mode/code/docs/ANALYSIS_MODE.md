# IDA MCP analysis mode

This milestone adds six independent files. Apply these additions only when all six target paths are absent; do not overwrite existing files. Existing agents and run/mission/do commands are unchanged.

## Architecture and contract

`core.analysis_cli` → `run_analysis` → `ClaudeAnalyst` → subscription Claude CLI → configured IDA Pro MCP. The analysis function checks a nonblank goal and an existing, readable regular file, resolves the path, and passes both inputs to ANALYST. It never launches the target binary.

Claude receives the request as JSON in stdin, preserving spaces and Unicode without shell interpolation. Its text response must be exactly a JSON object containing `findings`, a list of objects with `location`, `kind`, `evidence`, and `confidence`. The first three fields require nonblank strings; confidence requires a finite number in [0, 1], excluding booleans and numeric strings. Unknown fields are rejected. Empty findings are valid. The function returns validated `Finding` objects using the Pydantic 1 API, including Pydantic 2's compatibility namespace.

Example output: `{"findings":[{"location":"0x401000","kind":"bounds","evidence":"unchecked copy","confidence":0.8}]}`.

## Usage and permissions

From the repository root:

```powershell
python -m core.analysis_cli analyze "C:\samples\sample file.exe" --goal "Inspect bounds checks" --timeout 300
```

A configured Claude subscription session and IDA Pro MCP plugin are prerequisites for live analysis. Executable selection follows explicit adapter argument, CLAUDE_BIN, then resolve_cli. The adapter uses the project's sanitized environment, an argument array, and shell=False. No direct API client or API key is introduced.

`--allowedTools` explicitly grants `mcp__plugin_ida-pro-mcp_idalib__*` and `Read`. `--tools Read` limits built-in tools, and `--permission-mode dontAsk` avoids interactive permission prompts. The prompt requires static inspection and forbids target execution, debugging, arbitrary code evaluation, and target modification. The MCP wildcard is not a read-only security boundary: the configured server must independently restrict executable or mutating operations when those guarantees are required. Read access is not confined to the target file by these flags.

## Errors and integration

Successful output is JSON on stdout, exit 0. Analysis errors are JSON on stderr with code/message: INVALID_INPUT exits 2; TIMEOUT, CLI_FAILED, INVALID_JSON, and SCHEMA_MISMATCH exit 1. Argparse syntax errors use its standard usage output and exit 2. Malformed, fenced, or partial responses fail closed. subprocess.run enforces the direct CLI timeout; descendant-process termination is not guaranteed by this adapter.

`register_analyze_subcommand(subparsers)` adds only analyze and sets `args.func` to its handler. A future, separately authorized director.py change must call this registration function on its existing argparse subparsers and dispatch the returned handler's integer status. Its actual parser and dispatch implementation must first be inspected. **director.py analyze is not connected in this milestone.**

## Verification

Tests mock subprocess execution and CLI discovery; they never launch Claude, IDA, external accounts, or target binaries. They cover invocation permissions, paths with spaces, input validation, schema boundaries, timeout/failure responses, CLI output/status, registration preservation, and the module entry point.

Supplied Director verification evidence (Windows, Python 3.13.15): `python -m pytest tests/` exited 2 during collection. Zero tests executed: 0 passed, 0 failed, 1 collection error, and 1 deselected. Collection failed because `tests/test_v020_provider_ops.py` imports the unavailable `requests` package. The 654 selected tests did not run; selection is not evidence of passing tests. Verification remains incomplete, and the previous `verification.passed=true` flag is unsupported.

Required verifier reruns, with the pre-existing collection failure excluded only from the regression invocation:

```powershell
python -m pytest -q tests/test_analysis_mode.py
python -m pytest -q tests/ --ignore=tests/test_v020_provider_ops.py
python -m py_compile agents/claude_analyst.py schemas/finding.py core/analysis_mode.py core/analysis_cli.py tests/test_analysis_mode.py
```

These three commands have not been executed in this tools-prohibited Builder response. The verifier must record each command's actual exit code and pytest pass/fail/skip/deselection counts before review can pass. Record the excluded module's missing-requests collection failure separately; do not modify requirements.txt or suppress other failures. No supplied evidence establishes an allowed-file cause for that baseline failure. The new tests, runnable regressions, and syntax validation remain unverified; reviewer finding P1 remains open.
