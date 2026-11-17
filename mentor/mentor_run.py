"""MENTOR: 완성된 diff를 agy(Gemini/Antigravity)에 던져 학습 브리핑을 생성한다.

director가 작업을 PASS로 끝낸 뒤 호출하는 "학습 코치" 단계.
agy 호출/파싱 방식은 ai-dev-director의 research_runner와 동일한 공식 stream-json 프로토콜을 따른다.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def resolve_agy() -> str:
    p = shutil.which("agy")
    if p:
        return p
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
    if cand.exists():
        return str(cand)
    raise SystemExit("agy CLI를 찾을 수 없습니다. 'agy login'/설치를 확인하세요.")


def get_diff(args) -> str:
    if args.diff_file:
        return Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
    if args.project:
        proj = args.project
        out = subprocess.run(["git", "-C", proj, "diff", "HEAD"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        diff = out.stdout
        if not diff.strip():
            # director가 커밋했을 수 있으니 마지막 커밋을 본다
            out = subprocess.run(["git", "-C", proj, "show", "HEAD", "--stat", "-p"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            diff = out.stdout
        return diff
    return sys.stdin.read()


def main() -> None:
    ap = argparse.ArgumentParser(description="MENTOR: diff -> agy 학습 브리핑")
    ap.add_argument("--project", help="git 프로젝트 경로 (diff HEAD 자동 계산)")
    ap.add_argument("--diff-file", help="diff 파일 경로 (직접 지정)")
    ap.add_argument("--out", help="브리핑 저장 경로 (기본: <project>/LEARNING.md)")
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    mentor = (HERE / "mentor.md").read_text(encoding="utf-8")
    profile = (HERE / "profile.md").read_text(encoding="utf-8")
    diff = get_diff(args)
    if not diff.strip():
        raise SystemExit("변경(diff)이 비어 있습니다. --project 또는 --diff-file을 확인하세요.")

    prompt = (
        f"{mentor}\n\n"
        f"# 학습자 프로필\n{profile}\n\n"
        f"# 이번 변경 (diff)\n```diff\n{diff}\n```\n\n"
        f"위 변경을 바탕으로, 위 출력 형식에 정확히 맞춰 학습 브리핑을 작성하라."
    )

    agy = str(Path(resolve_agy()).resolve())
    msg = {"event": "user", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}}
    ndjson = json.dumps(msg, ensure_ascii=False) + "\n"

    proc = subprocess.run(
        [agy, "--input-format", "stream-json", "--output-format", "stream-json", "--sandbox"],
        input=ndjson, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=args.timeout, cwd=str(HERE),
    )
    if proc.returncode != 0:
        sys.stderr.write((proc.stderr or proc.stdout or "agy 호출 실패") + "\n")
        raise SystemExit(f"agy exit {proc.returncode}")

    response = None
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "result" and isinstance(ev.get("result"), dict):
            res = ev["result"]
            if res.get("status") == "SUCCESS":
                response = res.get("response")
    if not response:
        sys.stderr.write("--- agy 원시 출력(디버그, 앞 3000자) ---\n")
        sys.stderr.write((proc.stdout or "")[:3000] + "\n")
        raise SystemExit("agy 응답에서 결과를 추출하지 못했습니다.")

    if args.out:
        out_path = Path(args.out)
    elif args.project:
        out_path = Path(args.project) / "LEARNING.md"
    else:
        out_path = HERE / "LEARNING.md"
    out_path.write_text(response, encoding="utf-8")
    print(response)
    sys.stderr.write(f"\n[저장됨: {out_path}]\n")


if __name__ == "__main__":
    main()
