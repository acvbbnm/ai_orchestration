#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
watch_live.py — director 미션을 실시간으로 "관전"한다.

8081 TRINITY 콘솔이 안 뜰 때(HTTP 400 등) 대신 쓰는 경량 실시간 뷰어.
director는 진행 중 runs/RUN-<id>/ 폴더에 단계별 JSON과 logs/run.log 를 실시간으로 쓴다.
이 스크립트는 가장 최근(활성) 런을 자동으로 따라가며:

  - logs/run.log 의 새 줄을 실시간 tail
  - order/builder_cli/review/decision/verification JSON 이 생기거나 바뀌면
    "누가 → 누구에게 무엇을" 형태의 사람용 이벤트로 번역해 출력

새 미션이 시작되면(= 더 최근 런 폴더가 생기면) 자동으로 그쪽으로 전환한다(--run latest 기본).
Ctrl+C 로 종료.

사용:
  python watch_live.py                 # 최신 활성 런 자동 추적
  python watch_live.py --run RUN-...    # 특정 런 고정
  python watch_live.py --interval 0.5
"""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path

# 윈도우 cp949 콘솔에서도 한글/기호가 안 깨지고 안 터지게 UTF-8 강제
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

ENGINE = Path(r"C:\Users\user\ai-dev-director-inspect")

# 이모지는 일부 콘솔(cp949)에서 UnicodeEncodeError 를 내므로 ASCII 마커 사용
ROLE = {
    "order":          ("[HEAD]",      "작업 분해·지시 (-> BUILDER)"),
    "builder_cli":    ("[BUILDER]",   "구현 CLI 호출"),
    "review":         ("[REVIEWER]",  "독립 검수"),
    "decision":       ("[HEAD/판정]", "최종 판정"),
    "verification":   ("[VERIFY]",    "테스트/빌드 검증"),
    "repair_history": ("[REPAIR]",    "수리 루프"),
}
WATCH = list(ROLE.keys())

def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def runs_dir() -> Path:
    return ENGINE / "runs"

def newest_run() -> Path | None:
    rd = runs_dir()
    if not rd.exists():
        return None
    ds = [d for d in rd.iterdir() if d.is_dir() and d.name.startswith("RUN-")]
    return max(ds, key=lambda d: d.stat().st_mtime) if ds else None

def resolve(arg: str) -> Path | None:
    if arg in ("latest", "last"):
        return newest_run()
    cand = runs_dir() / arg
    if cand.exists():
        return cand
    for d in (runs_dir().iterdir() if runs_dir().exists() else []):
        if d.is_dir() and arg in d.name:
            return d
    return None

def summarize(kind: str, data) -> str:
    if not isinstance(data, dict):
        return ""
    if kind == "order":
        return "  목표: " + str(data.get("goal", ""))[:110]
    if kind == "builder_cli":
        inv = data.get("invocation_command", "")
        if isinstance(inv, list):
            inv = " ".join(inv)
        exe = str(inv).split()[0] if inv else "?"
        note = "  (!) codex (claude에서 failover!)" if exe == "codex" else ""
        return f"  실행: {exe} · {data.get('prompt_chars','?')}자 · exit={data.get('exit_code','?')}{note}"
    if kind == "review":
        v = data.get("verdict", "?")
        return f"  판정: {v} · P1 {len(data.get('p1',[]) or [])}건 / P2 {len(data.get('p2',[]) or [])}건"
    if kind == "decision":
        return f"  결정: {data.get('decision','?')} — {str(data.get('rationale',''))[:90]}"
    if kind == "verification":
        tc = data.get("test_counts", {})
        return f"  passed={data.get('passed','?')} · {json.dumps(tc, ensure_ascii=False)}"
    if kind == "repair_history":
        n = len(data) if isinstance(data, list) else "?"
        return f"  수리 시도 기록: {n}"
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="latest")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    print("=" * 64)
    print(" director 실시간 관전  (Ctrl+C 종료)")
    print("=" * 64)

    cur: Path | None = None
    log_pos = 0
    seen_mtime: dict[str, float] = {}

    try:
        while True:
            run = resolve(args.run) if args.run in ("latest", "last") else (cur or resolve(args.run))
            if run is None:
                print("… 활성 런 대기 중 (runs/ 비어있음)")
                time.sleep(max(1.0, args.interval)); continue

            if run != cur:
                cur = run
                log_pos = 0
                seen_mtime = {}
                print("\n" + "─" * 64)
                print(f"▶ 추적 시작: {cur.name}")
                print("─" * 64)

            # 1) 단계 JSON 변화 감지
            for kind in WATCH:
                fp = cur / f"{kind}.json"
                if not fp.exists():
                    continue
                m = fp.stat().st_mtime
                if seen_mtime.get(kind) == m:
                    continue
                seen_mtime[kind] = m
                label, desc = ROLE[kind]
                ts = time.strftime("%H:%M:%S")
                print(f"\n[{ts}] {label} — {desc}")
                body = summarize(kind, load(fp))
                if body:
                    print(body)

            # 2) run.log tail
            lp = cur / "logs" / "run.log"
            if lp.exists():
                try:
                    with lp.open("r", encoding="utf-8", errors="replace") as f:
                        f.seek(log_pos)
                        chunk = f.read()
                        log_pos = f.tell()
                    for line in chunk.splitlines():
                        if line.strip():
                            print("   | " + line)
                except Exception:
                    pass

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[관전 종료]")

if __name__ == "__main__":
    main()
