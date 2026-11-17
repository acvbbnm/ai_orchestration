# AI DEV 자동개발 + 학습 엔진

AI CLI들을 한 회사처럼 돌려 **목표 한 줄 → 검증된 코드 → 학습 브리핑**까지 이어주는 개인 작업 엔진.
(보안학과·SOC 배경에서 개발 역량을 바텀업으로 키우기 위한 포트폴리오 프로젝트)

## 빠른 시작
1. **`START.bat`** 더블클릭 → TRINITY 콘솔(http://127.0.0.1:8081)이 열린다.
2. 콘솔 입력창에 목표를 넣으면 HEAD→BUILDER→REVIEWER가 협업한다.
3. 작업이 끝나면 **학습 브리핑** 생성:
   ```powershell
   powershell mentor\learn.ps1 -Project "C:\path\to\your-project"
   ```
   → 그 프로젝트에 `LEARNING.md`가 생긴다.
4. 끄려면 **`STOP.bat`**.

## 흐름
```
목표 → HEAD(claude) → BUILDER(claude) → 테스트 → REVIEWER(codex) → HEAD 판정(PASS)
                                                                        │
                                                              MENTOR(agy) → 학습 브리핑
```

## 구조
| 경로 | 내용 |
|---|---|
| `START.bat` / `STOP.bat` | 엔진 시작 / 중지 |
| `mentor/` | 학습 코치 — 완료 후 공부할 포인트 브리핑 (agy) |
| `docs/CLI연동_가이드.md` | 3개 CLI와 역할, 로그인, 확인 |
| `docs/모델선택_가이드.md` | 역할별 모델 선택·토큰 절약 |
| 엔진 본체 | `C:\Users\user\ai-dev-director-inspect` 에 설치 (ai-dev-director, MIT) |

## 구성 요약
- 종량제 API 미사용 — 구독 CLI(claude / codex / agy) 로그인 세션만 사용
- IDA Pro MCP 연동됨 (리버싱 분석 — `mcp__...idalib__*` 툴)
- 자세한 건 `docs/` 참고
