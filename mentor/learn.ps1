# MENTOR 래퍼: director가 끝낸 프로젝트의 diff를 뽑아 학습 브리핑을 생성한다.
# 사용법:  .\learn.ps1 -Project "C:\path\to\project"
#          .\learn.ps1 -DiffFile "C:\path\to\change.diff"
param(
    [string]$Project,
    [string]$DiffFile,
    [string]$Out
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "mentor_run.py"
$argList = @($script)
if ($Project)  { $argList += @("--project", $Project) }
if ($DiffFile) { $argList += @("--diff-file", $DiffFile) }
if ($Out)      { $argList += @("--out", $Out) }
py -3.13 @argList
