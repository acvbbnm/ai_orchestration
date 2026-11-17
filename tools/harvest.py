#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
harvest.py — ai-dev-director 미션 결과물을 사람이 읽고 공유할 수 있게 "수확"한다.

director는 실행 기록을 엔진 폴더(runs/, data/) 안에 생 JSON으로만 쌓고,
코드 결과물은 숨김 worktree(.director_worktrees/RUN-*)에 남긴다. 둘 다 .gitignore 대상이라
공유가 안 된다. 이 스크립트는 하나의 RUN을 받아서:

  Desktop/프로젝트/<name>/
     code/      <- worktree에서 회수한 실제 결과물 파일
     record/    <- order/builder/review/decision/verification 등 생 기록 복사(감사용)
     REPORT.md  <- 생 JSON을 번역한 사람용 리포트(협업 흐름 + 모델별 컨텍스트 점검)

으로 모으고 git commit 한다. 성공/실패 상관없이 수확한다(실패한 실험도 포트폴리오 가치가 있음).

사용:
  python harvest.py --run latest --name analysis-mode
  python harvest.py --run RUN-261117232513-2D1EC4F77CE54D67AAA6656D2B45733E --name analysis-mode
  python harvest.py --list        # 수확 가능한 런 목록
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, datetime
from pathlib import Path

ENGINE = Path(r"C:\Users\user\ai-dev-director-inspect")
LAB    = Path(r"C:\Users\user\Desktop\프로젝트\director-lab")
OUTROOT = Path(r"C:\Users\user\Desktop\프로젝트")

def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def runs_dir() -> Path:
    return ENGINE / "runs"

def list_runs():
    rd = runs_dir()
    if not rd.exists():
        return []
    items = [d for d in rd.iterdir() if d.is_dir() and d.name.startswith("RUN-")]
    return sorted(items, key=lambda d: d.stat().st_mtime, reverse=True)

def resolve_run(arg: str) -> Path | None:
    rd = runs_dir()
    if arg in ("latest", "last"):
        rs = list_runs()
        return rs[0] if rs else None
    cand = rd / arg
    if cand.exists():
        return cand
    # allow suffix / partial match
    for d in list_runs():
        if arg in d.name:
            return d
    return None

def find_mission(run_id: str):
    """RUN-id 를 base_worktree 로 쓰는 미션 JSON 을 찾는다."""
    md = ENGINE / "data" / "missions"
    if not md.exists():
        return None
    for f in md.glob("MSN-*.json"):
        d = load(f)
        if not isinstance(d, dict):
            continue
        bw = str(d.get("base_worktree") or "")
        if run_id in bw:
            return d
    return None

def worktree_for(run_id: str) -> Path:
    return LAB / ".director_worktrees" / run_id

def changed_files(wt: Path):
    """worktree 에서 baseline 대비 변경/추가/미추적 파일 경로(상대) 목록."""
    if not wt.exists():
        return []
    try:
        out = subprocess.run(
            ["git", "-C", str(wt), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout
    except Exception:
        return []
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # 'XY path'  (XY = 2 status chars, then space)
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename
            path = path.split(" -> ", 1)[1]
        if path and not path.startswith(".director_worktrees"):
            files.append(path)
    return files

def copy_deliverable(wt: Path, rels, dest: Path):
    copied = []
    for rel in rels:
        src = wt / rel
        if not src.exists() or not src.is_file():
            continue
        tgt = dest / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
        try:
            lines = len(src.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            lines = 0
        copied.append((rel, lines))
    return copied

def copy_records(run: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for p in run.iterdir():
        if p.is_file():
            shutil.copy2(p, dest / p.name)
            names.append(p.name)
    logs = run / "logs"
    if logs.exists():
        (dest / "logs").mkdir(exist_ok=True)
        for p in logs.iterdir():
            if p.is_file():
                shutil.copy2(p, dest / "logs" / p.name)
    return names

def fmt_list(items, bullet="-"):
    if not items:
        return "  _(없음)_"
    return "\n".join(f"{bullet} {x}" for x in items)

def tail(text: str, n: int):
    ls = text.splitlines()
    return "\n".join(ls[-n:]) if len(ls) > n else text

def build_report(name, run, mission, order, builder, review, decision,
                 verification, provenance, run_log, copied, run_id):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    goal = (order or {}).get("goal") or (mission or {}).get("goal") or "N/A"
    status = (mission or {}).get("status", "N/A")
    profile = (mission or {}).get("profile", "N/A")
    verdict = (decision or {}).get("decision") or (review or {}).get("verdict") or "N/A"
    rationale = (decision or {}).get("rationale", "")
    next_steps = (decision or {}).get("next_steps", []) or []

    # BUILDER 컨텍스트 지표
    inv = (builder or {}).get("invocation_command", "")
    if isinstance(inv, list):
        inv = " ".join(inv)
    ctx_files = (builder or {}).get("context_files", [])
    prompt_chars = (builder or {}).get("prompt_chars", "N/A")
    _att = (builder or {}).get("attempts")
    if isinstance(_att, list):
        attempts = (builder or {}).get("attempt_number", len(_att))
    else:
        attempts = (builder or {}).get("attempt_number", _att if _att is not None else "N/A")
    has_model = "있음 (--model)" if "--model" in str(inv) else "없음 → CLI 기본 모델"
    omitted = (builder or {}).get("omitted_files", [])

    # REVIEWER findings
    p0 = (review or {}).get("p0", []) or []
    p1 = (review or {}).get("p1", []) or []
    p2 = (review or {}).get("p2", []) or []
    rsummary = (review or {}).get("summary", "")

    # verification
    passed = (verification or {}).get("passed", "N/A")
    tcounts = (verification or {}).get("test_counts", {})
    preexist = (verification or {}).get("preexisting_failures", [])
    missing = (verification or {}).get("required_outputs_missing", [])

    def jdump(x, limit=1500):
        s = json.dumps(x, ensure_ascii=False, indent=2)
        return s if len(s) <= limit else s[:limit] + "\n… (생략)"

    md = f"""# {name} — AI 협업 개발 기록

> 수확 시각: {now} · 런: `{run_id}` · 미션: `{(mission or {}).get('mission_id','N/A')}`
> 프로필: **{profile}** · 미션 상태: **{status}** · 최종 판정: **{verdict}**

## 🎯 목표 (HEAD가 받은 지시)
{goal}

---

## 협업 흐름 — 누가 무엇을 했나

### 1) HEAD (codex / gpt-6-astra) — 작업 분해·지시
- **스코프 가드**
  - 허용 경로(allowed_paths): {', '.join((order or {}).get('allowed_paths', []) or ['N/A'])}
  - 보호 경로(protected_paths): {', '.join((order or {}).get('protected_paths', []) or ['N/A'])}
  - 필수 산출물(required_outputs): {', '.join((order or {}).get('required_outputs', []) or ['N/A'])}
- **인수 기준(acceptance_criteria)**
{fmt_list((order or {}).get('acceptance_criteria', []) or [])}
- 위험도: {(order or {}).get('risk_level','N/A')} · 사람 승인 필요: {(order or {}).get('requires_human_approval','N/A')}

### 2) BUILDER (claude / opus) — 구현
- **실제 CLI 호출**(모델/플래그가 그대로 보임):
```
{inv or 'N/A'}
```
- 주입된 컨텍스트 파일 수: **{len(ctx_files) if isinstance(ctx_files, list) else ctx_files}개** · 프롬프트 크기: **{prompt_chars}자** · 시도 횟수: **{attempts}**
- **모델 플래그(--model): {has_model}** · 실제 실행 바이너리: **{str(inv).split()[0] if inv else 'N/A'}** _(의도=claude와 다르면 failover 발생)_
- 생략된 파일(omitted, 너무 커서 제외): {', '.join(omitted) if omitted else '없음'}

### 3) REVIEWER (antigravity / gemini-hydrogen) — 독립 검수
- 판정(verdict): **{(review or {}).get('verdict','N/A')}**
- P0(치명): {len(p0)}건 / P1(필수): {len(p1)}건 / P2(권고): {len(p2)}건
- 요약: {rsummary or 'N/A'}

### 4) HEAD — 최종 판정
- **결정: {verdict}**
- 근거: {rationale or 'N/A'}
- 다음 단계:
{fmt_list(next_steps)}

---

## ✅ 검증 결과
- 통과(passed): **{passed}**
- 테스트 카운트: `{json.dumps(tcounts, ensure_ascii=False)}`
- 누락된 필수 산출물: {', '.join(missing) if missing else '없음'}
- 기존(사전) 실패: {', '.join(preexist) if preexist else '없음'}

---

## 🧪 모델별 컨텍스트 엔지니어링 점검
| 역할 | 모델(의도) | 주입 컨텍스트 | 프롬프트 크기 | 비고 |
|---|---|---|---|---|
| HEAD | codex / gpt-6-astra | 목표+프로젝트 트리 | — | 계획·판정 |
| BUILDER | claude / opus | {len(ctx_files) if isinstance(ctx_files, list) else ctx_files}개 파일 | {prompt_chars}자 | `--allowedTools` 등 위 CLI 호출 참조 |
| REVIEWER | antigravity / gemini-hydrogen | diff + 기준 | — | 독립 검수 |

> ⚠️ 위 "모델(의도)"는 config.yaml 설정값이다. **CLI가 실제로 그 모델로 호출됐는지**는
> BUILDER의 CLI 호출 줄에 `--model`이 있는지로만 확인 가능하다(codex/claude는 director가
> `--model`을 안 넘겨서 CLI 계정 기본 모델이 쓰임 — 이 점이 점검 포인트).

---

## 📦 결과물 파일 (code/)
{fmt_list([f"`{rel}` — {lines}줄" for rel, lines in copied]) if copied else "  _(worktree에서 회수한 파일 없음)_"}

---

## 🕒 타임라인 (run.log 끝부분)
```
{tail(run_log, 40) if run_log else 'N/A'}
```

---

## 🔎 원본 기록
감사·재현용 생 JSON은 `record/` 폴더에 그대로 복사돼 있다
(order.json, builder_cli.json, review.json, decision.json, verification.json, repair_history.json, logs/run.log 등).
"""
    return md

def git_commit(outroot: Path, name: str, verdict: str):
    def g(*args):
        return subprocess.run(["git", "-C", str(outroot), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    # repo 없으면 init
    if not (outroot / ".git").exists():
        g("init")
    g("add", name)
    msg = f"harvest: {name} ({verdict})\n\nAI 협업 개발 결과물 수확 (director 런 아카이브)"
    r = g("commit", "-m", msg)
    return (r.returncode == 0, (r.stdout + r.stderr).strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="latest", help="RUN-id 또는 'latest'")
    ap.add_argument("--name", help="세부프로젝트 폴더명 (미지정 시 런 날짜 기반)")
    ap.add_argument("--list", action="store_true", help="수확 가능한 런 목록만 출력")
    ap.add_argument("--no-git", action="store_true", help="git commit 건너뛰기")
    args = ap.parse_args()

    if args.list:
        for d in list_runs():
            m = find_mission(d.name)
            st = (m or {}).get("status", "?")
            print(f"{d.name}  [{st}]  {(m or {}).get('goal','')[:60]}")
        return

    run = resolve_run(args.run)
    if not run:
        print(f"[!] 런을 못 찾음: {args.run}", file=sys.stderr); sys.exit(1)
    run_id = run.name
    mission = find_mission(run_id)
    wt = worktree_for(run_id)

    order        = load(run / "order.json")
    builder      = load(run / "builder_cli.json")
    review       = load(run / "review.json")
    decision     = load(run / "decision.json")
    verification = load(run / "verification.json")
    provenance   = load(run / "provenance.json")
    run_log = ""
    lp = run / "logs" / "run.log"
    if lp.exists():
        run_log = lp.read_text(encoding="utf-8", errors="replace")

    name = args.name or f"run-{run_id.split('-')[1]}"
    dest = OUTROOT / name
    dest.mkdir(parents=True, exist_ok=True)

    rels = changed_files(wt)
    copied = copy_deliverable(wt, rels, dest / "code")
    copy_records(run, dest / "record")

    report = build_report(name, run, mission, order, builder, review, decision,
                          verification, provenance, run_log, copied, run_id)
    (dest / "REPORT.md").write_text(report, encoding="utf-8")

    verdict = (decision or {}).get("decision") or (review or {}).get("verdict") or "N/A"
    print(f"[+] 수확 완료: {dest}")
    print(f"    code/   : {len(copied)}개 파일")
    print(f"    record/ : 원본 기록 복사")
    print(f"    REPORT.md: 생성")
    print(f"    판정: {verdict}")

    if not args.no_git:
        ok, out = git_commit(OUTROOT, name, verdict)
        print(f"[git] commit {'OK' if ok else 'SKIP/FAIL'}: {out[:200]}")

if __name__ == "__main__":
    main()
