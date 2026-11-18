# tools — director 가시화 도구

director는 실행 기록을 **엔진 폴더(`ai-dev-director-inspect/runs/`, `data/`)** 안에 생 JSON으로만 쌓고,
코드 결과물은 **숨김 worktree(`director-lab/.director_worktrees/RUN-*`)** 에 남긴다.
둘 다 `.gitignore` 대상이라 그대로는 공유가 안 되고, 콘솔엔 성공/실패 요약만 보인다.

이 폴더의 두 스크립트가 그 간극을 메운다.

---

## 1) harvest.py — 결과물 수확(아카이브)

하나의 RUN을 받아서 `Desktop/프로젝트/<name>/` 로 모으고 git commit 한다.
성공/실패 상관없이 수확한다(실패한 실행도 원인 분석 자료가 됨).

```bash
python tools/harvest.py --list                      # 수확 가능한 런 목록 + 상태
python tools/harvest.py --run latest --name 작업명    # 최신 런 수확
python tools/harvest.py --run RUN-26... --name analysis-mode
python tools/harvest.py --run latest --name 작업명 --no-git   # 커밋 생략
```

만들어지는 구조:

```
Desktop/프로젝트/<name>/
   code/      <- worktree에서 회수한 실제 결과물 파일 (상대경로 보존)
   record/    <- order/builder_cli/review/decision/verification 등 생 기록 복사(감사·재현용)
   REPORT.md  <- 생 JSON 번역: 협업 흐름(HEAD/BUILDER/REVIEWER) + 모델별 컨텍스트 점검 + 테스트 결과
```

**REPORT.md 가 핵심** — "내가 뭘 만들었나 / 각 역할이 뭘 했나 / 왜 통과·실패했나"를 한 장으로 보여준다.
빌더 섹션의 `실제 실행 바이너리`가 `claude`가 아니라 `codex`면 **failover**가 일어난 것.

## 2) watch_live.py — 실시간 관전

8081 TRINITY 콘솔이 안 뜰 때 대신 쓰는 경량 실시간 뷰어.
진행 중인 런의 단계별 JSON과 `logs/run.log`를 실시간으로 사람이 읽는 이벤트로 번역해 보여준다.

```bash
python tools/watch_live.py              # 최신 활성 런 자동 추적 (새 미션 시작되면 자동 전환)
python tools/watch_live.py --run RUN-... # 특정 런 고정
python tools/watch_live.py --interval 0.5
```

출력 예:

```
[HEAD]     — 작업 분해·지시     목표: ...
[BUILDER]  — 구현 CLI 호출       실행: codex · 103865자 · exit=0  (!) codex (claude에서 failover!)
[REVIEWER] — 독립 검수           판정: pass · P1 0건 / P2 0건
[VERIFY]   — 테스트/빌드 검증     passed=False · {"passed":123,"failed":1,"total":124}
   | 2026-11-18 00:06:30 [WARNING] Builder attempt 1/3 on ANTHROPIC failed: Invalid control character ...
```

Ctrl+C 로 종료. 경로 상수(ENGINE/LAB/OUTROOT)는 각 스크립트 상단에서 바꾼다.
