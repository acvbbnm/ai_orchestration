# 02. ai-dev-director 구조와 각 .py 동작 원리

## 2.1 무엇인가
`ai-dev-director` — **구독 CLI 전용** 멀티 에이전트 오케스트레이터(Windows 우선, Python). 환경의 API 키는 **CLI 호출 전에 제거**해서 "구독 세션으로만 돈다"는 정책을 강제한다. 콘솔(TRINITY, 포트 8081)에서 진행을 본다.

## 2.2 역할 구성 (내가 세팅한 모델)

| 역할 | 하는 일 | 내가 배정한 모델(의도) |
|---|---|---|
| **HEAD** | 목표 해석 → 작업 분해 → 지시(order) → 최종 판정 | codex / gpt-6-astra (현존 최강 = 계획·판정) |
| **BUILDER** | order 받아 파일을 통째로 구현해 JSON으로 반환 | claude / opus (코딩 최강) |
| **REVIEWER** | diff·검증결과를 **독립 검수**(P0/P1/P2) | antigravity(gemini) / hydrogen |
| **MENTOR** | 개발 끝나면 **나의 학습 포인트**를 잡아 보고 | agy(gemini) / hydrogen |

> 설계자(HEAD)와 빌더는 **달라도 된다** — 오히려 분리가 정상이다. 설계·판정은 사고력, 구현은 코딩력이 중요하므로.

## 2.3 실행 흐름 (상태 기계)

```
PLANNING → ORDER_READY → (baseline gate) → BUILDING → VERIFYING → REVIEWING → DECIDING
                                              ↑___________ 수정 루프 ___________|
                                                     (PASS면 적용 / 예산 소진이면 중단)
```

- **프로파일**: quick{max_steps 2}, standard{6}, deep{12}.
- **auto_apply: on_pass** — PASS한 결과물만 프로젝트에 자동 반영(사람이 바꾼 파일은 덮지 않음, 삭제 안 함).
- **failover**: 한 provider가 실패하면 다른 provider로 대행(NORMAL/DEGRADED/STOP 모드).

## 2.4 각 .py가 동작하는 원리 (핵심 파일)

### 진입·오케스트레이션
- **`director.py`** — CLI 진입점. 서브커맨드 `run`(단발), `mission`/`do`(다단계 목표), (실험으로 추가한) `analyze`. `do <goal> -p <경로> --profile <quick|standard|deep>`.
- **`core/orchestrator.py`** — 상태 기계의 심장. `run_baseline_if_required()`(빌더 전 깨끗한 worktree에서 기준선 측정), `validate_post_build()`(**스코프 가드 → 검증 → 기준선 회귀 게이트**). 여기서 PASS/FAIL이 갈린다.
- **`core/mission.py`** — 다단계 미션 러너. 단계별 order를 만들고 결과를 누적한다.
- **`core/state_machine.py`** — 상태 전이와 감사 로그(audit) 기록.

### 검증·안전
- **`core/verifier.py`** — build/test/lint 명령을 실제로 실행. `passed = build ∧ test ∧ lint`(각 exit_code==0). pytest 출력에서 통과/실패 수를 파싱. **주의: 이 파일 자체엔 "기존 실패 관용" 개념이 없다** — 그 판단은 orchestrator/autopilot에 있다.
- **`core/autopilot.py`** — 위반 분류(triage), `only_preexisting_failures()`(기준선에서 이미 깨진 테스트는 "회귀 아님"으로 관용), 돈 이동 코드 탐지 등 "HEAD 대리 판단".
- **`core/safety.py` (SafetyPolicy)** — **스코프 가드**. order의 allowed_paths 밖, 보호 경로(director.py, config.yaml, .git 등), 제어판 파일을 건드리면 차단.
- **`core/builder_context.py`** — BUILDER에게 줄 **컨텍스트 조립**. 참조 문서를 모아 단일 "컨텍스트 예산" 안에서 프롬프트를 만든다. **모델 무관 공통 로직**(모델별 토큰예산/시스템프롬프트 분기 없음).

### 에이전트 어댑터 (각 CLI를 "어떻게 구동하나" = 하네스)
- **`agents/codex_head.py`** — HEAD. `codex exec --sandbox read-only -`(프롬프트를 stdin으로). 응답은 stream-json 이벤트를 파싱.
- **`agents/proposal_builder.py` / `antigravity_builder.py`** — BUILDER. claude=`claude --print --output-format json`, agy=`agy --input-format stream-json --mode accept-edits --sandbox`. 결과를 **"파일 전체를 담은 JSON"** 으로 받아 director가 검증 후 기록.
- **`agents/codex_reviewer.py` / `claude_reviewer.py`** — REVIEWER. 역시 1회성 호출.
- **`core/role_settings.py`** — 역할별 설정. **여기 `model='cli-default'` 로 하드코딩** → codex/claude는 `--model`을 안 넘기고 **CLI 계정 기본 모델**로 돈다. (모델 지정이 실제로 적용되는 건 agy 경로뿐: `core/research_runner.py`에서 `--model gemini-...-hydrogen`.)

### 콘솔·기록
- **`companion_server.py` / `dashboard_server.py`** — TRINITY 콘솔(8081) 백엔드. 진행 상황을 브라우저로.
- **실행 기록 저장 위치**:
  - `runs/RUN-<id>/` — 단계별 포렌식 JSON(`order`, `builder_cli`, `review`, `decision`, `verification`, `repair_history`, `logs/run.log`).
  - `data/missions/MSN-<id>.json` + `data/director.db` — 미션 상태.
  - `director-lab/.director_worktrees/RUN-<id>/` — **실제 코드 결과물**(숨김 worktree).
  - ⚠️ 위 셋 모두 `.gitignore` 대상("runtime state is never source") → **그대로는 공유 불가**. (이래서 `tools/harvest.py`를 만들었다 — 04 참조.)

## 2.5 한눈에 — "구동 방식"은 모델별로 다르나?

| 역할 | 실제 CLI 구동 | 모델 플래그 |
|---|---|---|
| HEAD | `codex exec --sandbox read-only -` | ❌ 없음(기본 모델) |
| BUILDER(claude) | `claude --print --output-format json` | ❌ 없음(기본 모델) |
| BUILDER/MENTOR(agy) | `agy ... --mode accept-edits --sandbox` | ✅ `--model` 적용 |
| REVIEWER | `codex exec ...` / `claude --print` | ❌ 없음 |

→ **하네스(구동 방식)는 provider별로 맞춤**이지만, **모델 선택은 codex/claude엔 적용 안 됨**. 컨텍스트 조립도 모델 무관 공통. (상세: 04의 "모델별 컨텍스트 점검".)

→ 다음: [03 실험·테스트·실패지점](03_실험_테스트_실패지점.md)
