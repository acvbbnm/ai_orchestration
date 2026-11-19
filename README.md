# AI 오케스트레이션 실험

설계·구현·검수를 여러 CLI 에이전트에 나눠 맡기고, 코드 변경과 테스트 기록으로 실행 결과를 검토한 실험입니다.

[실험 보고서](analysis-mode/REPORT.md) · [세 차례 실행 비교](AI오케스트레이션/03_실험기록과_실패지점.md) · [개선 설계](AI오케스트레이션/04_AS-IS_TO-BE_리포트.md)

## 실험 기록 읽기

같은 분석 모드 구현 과제를 세 번 실행했습니다. 오케스트레이터가 작업 지시, 구현 결과, 검수 의견을 파일로 넘기는 과정과 각 CLI의 종료 상태를 대조했습니다.

한 실행에서는 구현 파일이 생성됐지만 테스트 실행 건수가 0건이었습니다. 검수 의견과 별도로 실행된 테스트 수를 확인하고, 허용 경로 안의 변경만 승인하는 흐름을 개선안으로 정리했습니다.

![작업 지시와 결과가 역할 사이에서 오가는 구조](AI오케스트레이션/assets/diagrams/02_mapping.png)

## 로컬 실행 기록 확인

Windows와 Python이 필요합니다. 엔진은 [ai-dev-director](https://github.com/digilogd-cmd/ai-dev-director)를 별도로 설치합니다. 기존 실행이 있다면 [도구 안내](tools/README.md)에 따라 스크립트의 엔진·실습 폴더 경로를 맞춥니다.

~~~powershell
git clone https://github.com/acvbbnm/ai_orchestration.git
cd ai_orchestration
py -3.13 tools/harvest.py --list
py -3.13 tools/harvest.py --run latest --name analysis-review --no-git
~~~

두 번째 명령은 최근 실행의 보고서, 작업 결과물, 원본 실행 기록을 모읍니다. 복제 직후에는 저장소의 [예시 보고서](analysis-mode/REPORT.md)를 바로 열 수 있습니다.

[엔진 사용법](docs/엔진_사용법.md) · [오픈소스 출처 및 라이선스](AI오케스트레이션/06_사용한_오픈소스와_라이선스.md)
