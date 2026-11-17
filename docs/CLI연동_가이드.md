# CLI 연동 가이드

이 엔진은 **구독 CLI 세션만** 쓴다. API 키는 쓰지 않는다 (종량제 과금 없음).
엔진이 실행 시 환경에서 모든 `*_API_KEY`를 제거하고 로그인된 CLI만 호출한다.

## 역할 ↔ CLI

| 역할 | CLI | 구독 | 하는 일 |
|---|---|---|---|
| **HEAD** (지휘·계획·판정) | `claude` | Claude | 목표를 ORDER로 쪼개고 PASS/FAIL 판정 |
| **BUILDER** (구현) | `claude` | Claude | 파일 전체를 JSON으로 제출 |
| **REVIEWER** (검수) | `codex` | ChatGPT | 독립 검토 (BUILDER와 반드시 다른 공급자) |
| **MENTOR** (학습코치) | `agy` | Gemini | 완료 후 학습 브리핑 (저빈도) |

> - BUILDER는 코드 품질이 핵심이라 claude 유지.
> - REVIEWER는 "자기 코드 자기 검수" 방지를 위해 BUILDER와 **달라야** 함 → codex.
> - agy(Antigravity)는 한도가 빡빡해 빌드 루프엔 안 넣고, 저빈도 MENTOR로만 사용.

## 로그인 (최초 1회)
- `claude`  — 로그인됨
- `codex login`  — ChatGPT 계정
- `agy login`  — Google(Gemini) 계정

## 확인
```
claude --version
codex --version
agy --version
```
세 개 다 버전이 뜨면 연동 완료.

## 설정 위치
- 역할별 공급자: `ai-dev-director\config.yaml` 의 `head` / `builder` / `reviewer`
- MENTOR 학습자 프로필: `mentor\profile.md` (수준 바뀌면 여기만 수정)

## 참고: IDA Pro MCP
리버싱 분석용 IDA MCP가 claude에 연동돼 있다 (`mcp__plugin_ida-pro-mcp_idalib__*`).
헤드리스(idalib) 모드로, 바이너리를 열어 디컴파일·xref·데이터흐름 분석 가능.
단, 엔진/claude가 `uv`를 PATH에서 찾아야 하므로 **CLI는 새 터미널/재시작 후** 사용할 것.
