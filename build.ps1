<#
.SYNOPSIS
  打包統計學考試用的隨身碟環境（需要網路，執行一次即可）。

.DESCRIPTION
  產生 build\STAT_EXAM\，內含 WinPython（Python + JupyterLab + 套件）、可攜式 VS Code、
  statkit、範本、筆記、講義、作業與離線文件。完成後把整個 STAT_EXAM 資料夾複製到隨身碟。
  可以重複執行：已下載的檔案會沿用，workspace 的內容會重新複製（exam\ 與 data\ 裡你自己的檔案不會被刪）。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File build.ps1
  powershell -ExecutionPolicy Bypass -File build.ps1 -SkipDocs
#>
param(
    [string]$Out = "$PSScriptRoot\build\STAT_EXAM",
    [string]$WinPyUrl = "https://github.com/winpython/winpython/releases/download/17.12.20260522/WinPython/WinPython64-3.13.15.0dot.zip",
    [string]$VSCodeUrl = "https://update.code.visualstudio.com/latest/win32-x64-archive/stable",
    [string]$FontUrl = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf",
    [switch]$SkipVSCode,
    [switch]$SkipDocs,
    [switch]$SkipCheck,
    [switch]$NoLocalSettings      # 不同步這台電腦的 VS Code 設定，只用考試設定
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Repo = $PSScriptRoot
$Dl = Join-Path $Repo "build\downloads"
New-Item -ItemType Directory -Force $Dl, $Out | Out-Null

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

function Get-File($url, $name) {
    $path = Join-Path $Dl $name
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "下載 $name ..."
        Invoke-WebRequest $url -OutFile "$path.part"
        Move-Item -LiteralPath "$path.part" $path
    }
    return $path
}

function Run {
    # 執行外部程式，失敗就停止（用 $args，避免 -m 之類的參數被 PowerShell 吃掉）
    $exe, $rest = $args
    & $exe @rest
    if ($LASTEXITCODE -ne 0) { throw "指令失敗（exit $LASTEXITCODE）：$($args -join ' ')" }
}

function Use-PortableEnv($winPy) {
    # 跟 tools\env.bat 一樣的環境變數，讓打包時建立的快取/設定都放在 WinPython\settings
    $env:PYTHONNOUSERSITE = "1"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:MPLCONFIGDIR = "$winPy\settings\.matplotlib"
    $env:JUPYTER_CONFIG_DIR = "$winPy\settings\.jupyter"
    $env:JUPYTER_DATA_DIR = "$winPy\settings\jupyter_data"
    $env:IPYTHONDIR = "$winPy\settings\.ipython"
    $env:PATH = "$winPy\python;$winPy\python\Scripts;$env:PATH"
}

function Copy-Tree($src, $dst) {
    # 複製資料夾內容，略過 __pycache__ / .ipynb_checkpoints
    robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP /XD __pycache__ .ipynb_checkpoints | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy 失敗：$src → $dst" }
    $global:LASTEXITCODE = 0
}

function Expand-Zip($zip, $dst) {
    New-Item -ItemType Directory -Force $dst | Out-Null
    Run "$env:SystemRoot\System32\tar.exe" -xf $zip -C $dst    # Windows 內建 bsdtar，比 Expand-Archive 快很多
}

# ------------------------------------------------------------------ 1. WinPython
Step "1. WinPython"
$zip = Get-File $WinPyUrl (Split-Path $WinPyUrl -Leaf)
if (-not (Get-ChildItem $Out -Directory -Filter "WPy64-*" -ErrorAction SilentlyContinue)) {
    Expand-Zip $zip $Out
}
$WinPy = (Get-ChildItem $Out -Directory -Filter "WPy64-*" | Select-Object -First 1).FullName
$Py = Join-Path $WinPy "python\python.exe"
Write-Host "WinPython：$WinPy"
Use-PortableEnv $WinPy

# ------------------------------------------------------------------ 2. 套件
Step "2. 安裝套件"
Run $Py -m pip install --upgrade pip --no-warn-script-location -q
Run $Py -m pip install -r "$Repo\requirements.txt" --no-warn-script-location -q
$site = (& $Py -c "import sysconfig; print(sysconfig.get_paths()['purelib'])").Trim()
# 讓任何位置的 notebook 都能 import statkit（相對於 python.exe 的路徑，換磁碟代號也沒問題）
Set-Content -LiteralPath "$site\statkit_workspace.pth" -Encoding ascii -Value `
    "import os, sys; sys.path.append(os.path.normpath(os.path.join(os.path.dirname(sys.executable), '..', '..', 'workspace')))"
$labSettings = Join-Path $WinPy "python\share\jupyter\lab\settings"
New-Item -ItemType Directory -Force $labSettings | Out-Null
Copy-Item "$Repo\config\jupyterlab-overrides.json" "$labSettings\overrides.json" -Force
Write-Host "預先編譯 .pyc（加快隨身碟上的啟動速度）..."
& $Py -m compileall -q -j 0 "$WinPy\python\Lib" *> $null
$global:LASTEXITCODE = 0

# ------------------------------------------------------------------ 3. VS Code
if (-not $SkipVSCode) {
    Step "3. 可攜式 VS Code"
    $vsDir = Join-Path $Out "VSCode"
    if (-not (Test-Path "$vsDir\Code.exe")) {
        $vsZip = Get-File $VSCodeUrl "vscode-win32-x64.zip"
        Expand-Zip $vsZip $vsDir
    }
    # 新版 VS Code 內建 Copilot 擴充：考試禁用 AI，直接從可攜版移除（設定裡也已關閉 AI 功能）
    Get-ChildItem $vsDir -Directory -Recurse -Depth 4 -Filter extensions |
        Where-Object { $_.FullName -match 'resources\\app\\extensions$' } |
        ForEach-Object { Get-ChildItem $_.FullName -Directory | Where-Object { $_.Name -match 'copilot' } } |
        ForEach-Object { Write-Host "移除內建 AI 擴充：$($_.Name)"; Remove-Item -LiteralPath $_.FullName -Recurse -Force }
    New-Item -ItemType Directory -Force "$vsDir\data\user-data\User", "$vsDir\data\tmp" | Out-Null   # data\ 存在 = portable mode
    # 設定、快捷鍵、snippets、介面語言：同步這台電腦的 VS Code（排除 AI 與綁本機的設定），考試設定優先
    $syncArgs = @("$Repo\tools\sync_vscode_settings.py", "--vscode-data", "$vsDir\data", "--config", "$Repo\config")
    if ($NoLocalSettings) { $syncArgs += "--no-local" }
    Run $Py @syncArgs
    $installed = (& "$vsDir\bin\code.cmd" --list-extensions) -join "`n"
    foreach ($ext in Get-Content "$Repo\config\extensions.txt" | Where-Object { $_.Trim() }) {
        if ($installed -notmatch [regex]::Escape($ext)) {
            Write-Host "安裝擴充 $ext"
            Run "$vsDir\bin\code.cmd" --install-extension $ext --force
        }
    }
    # 語言包快取（啟動器每次啟動前也會依目前的磁碟代號重建，第一次啟動就是中文）
    Run $Py "$Repo\tools\vscode_locale.py" "$vsDir\data"
}

# ------------------------------------------------------------------ 4. workspace
Step "4. workspace（程式、範本、筆記、講義、作業）"
$Ws = Join-Path $Out "workspace"
foreach ($d in "statkit", "tools", "notes") { Copy-Tree "$Repo\$d" "$Ws\$d" }
# 講義與作業：放在 repo 的 handouts\、homework\（不進版控），整個資料夾複製
foreach ($d in "handouts", "homework") {
    if (Test-Path "$Repo\$d") { Copy-Tree "$Repo\$d" "$Ws\$d" }
    else { Write-Warning "找不到 $d\，略過（把檔案放進 $Repo\$d 再重新打包）" }
}
New-Item -ItemType Directory -Force "$Ws\exam", "$Ws\data", "$Ws\homework", "$Ws\fonts", "$Ws\.vscode", "$Ws\tools\templates" | Out-Null
# 乾淨的考卷範本（{學號}、{姓名} 由 5_新增考卷 填入）與學生資料
Copy-Item "$Repo\templates\exam_template.ipynb" "$Ws\tools\templates\exam_template.ipynb" -Force
$student = "$Repo\config\student.json"
if (-not (Test-Path $student)) {
    Write-Warning "找不到 config\student.json，先用範本 student.example.json（考卷會是範例學號）。請複製一份改成自己的學號姓名再重新打包"
    $student = "$Repo\config\student.example.json"
}
Copy-Item $student "$Ws\tools\student.json" -Force
Copy-Item "$Repo\templates\00_索引.ipynb" "$Ws\00_索引.ipynb" -Force
Copy-Item "$Repo\templates\常見問題.md" "$Ws\常見問題.md" -Force
Copy-Item "$Repo\templates\data_README.md" "$Ws\data\README.md" -Force
foreach ($pair in @(@("vscode-workspace-settings.json", "settings.json"), @("vscode-tasks.json", "tasks.json"))) {
    (Get-Content "$Repo\config\$($pair[0])" -Raw -Encoding utf8) -replace "__WINPY__", (Split-Path $WinPy -Leaf) |
        Set-Content "$Ws\.vscode\$($pair[1])" -Encoding utf8
}
Run $Py "$Ws\tools\extract_pdf_text.py" "$Ws\handouts"

# ------------------------------------------------------------------ 5. 字型與離線文件
Step "5. 中文字型與離線文件"
$font = Get-File $FontUrl "NotoSansTC-VF.ttf"
Copy-Item -LiteralPath $font "$Ws\fonts\NotoSansTC-VF.ttf" -Force
if (-not $SkipDocs) {
    $pyMinor = (& $Py -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')").Trim()
    # scipy 的離線文件不一定每個小版本都有，從文件首頁找目前提供的 zip
    $scipyZip = $null
    try {
        $href = (Invoke-WebRequest "https://docs.scipy.org/doc/" -UseBasicParsing).Links.href |
            Where-Object { $_ -match '^scipy/scipy-html-[\d.]+\.zip$' } | Select-Object -First 1
        if ($href) { $scipyZip = "https://docs.scipy.org/doc/$href" }
    } catch { }
    $docs = [ordered]@{
        "pandas" = "https://pandas.pydata.org/docs/pandas.zip"
        "numpy"  = "https://numpy.org/doc/stable/numpy-html.zip"
        "scipy"  = $scipyZip
        "python" = "https://docs.python.org/$pyMinor/archives/python-$pyMinor-docs-html.zip"
    }
    foreach ($name in $docs.Keys) {
        $dst = "$Ws\docs-offline\$name"
        if (Test-Path $dst) { continue }
        if (-not $docs[$name]) { Write-Warning "找不到 $name 的離線文件網址，略過"; continue }
        try {
            $z = Get-File $docs[$name] "docs-$name.zip"
            Expand-Zip $z $dst
            Write-Host "離線文件：$name"
        } catch {
            Write-Warning "抓不到 $name 的離線文件（$($_.Exception.Message)），略過；可以用 hover / Shift+Tab 看說明"
        }
    }
}

# ------------------------------------------------------------------ 6. 啟動器
Step "6. 啟動器"
Copy-Item "$Repo\launchers\*.bat" $Out -Force
Copy-Item "$Repo\templates\使用說明.txt" $Out -Force
& $Py -m pip freeze | Set-Content "$Ws\tools\requirements-lock.txt" -Encoding utf8

# ------------------------------------------------------------------ 7. 檢查
if (-not $SkipCheck) {
    Step "7. 環境檢查"
    & $Py "$Ws\tools\check_env.py"
    if ($LASTEXITCODE -ne 0) { Write-Warning "環境檢查有項目沒通過，請看上面的輸出" }
    $global:LASTEXITCODE = 0
}

$size = (Get-ChildItem $Out -Recurse -File | Measure-Object Length -Sum).Sum / 1GB
Write-Host ("`n完成：{0}（{1:N2} GB）。把整個資料夾複製到隨身碟即可。" -f $Out, $size) -ForegroundColor Green
