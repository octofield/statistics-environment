<#
.SYNOPSIS
  打包統計學考試用的隨身碟環境（需要網路，執行一次即可）。

.DESCRIPTION
  產生 build\STAT_EXAM\，內含 WinPython（Python + JupyterLab + 套件）、可攜式 VS Code、
  statkit、範本、筆記、講義、作業與離線文件。完成後把整個 STAT_EXAM 資料夾複製到隨身碟。
  可以重複執行：已下載的檔案會沿用，workspace 的內容會重新複製（exam\ 與 data\ 裡你自己的檔案不會被刪）。

  一般使用者請雙擊 repo 根目錄的 setup.cmd，用圖形介面精靈設定；這支腳本是精靈背後實際執行打包的程式。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File build.ps1
  powershell -ExecutionPolicy Bypass -File build.ps1 -SkipDocs
  powershell -ExecutionPolicy Bypass -File build.ps1 -SkipJupyterLab -SkipExtraExtensions
  powershell -ExecutionPolicy Bypass -File build.ps1 -Out E:\STAT_EXAM -StudentId B12345678 -StudentName 王小明 -HandoutsDir D:\講義
#>
param(
    [string]$Out = "$PSScriptRoot\build\STAT_EXAM",
    [string]$StudentId,                                   # 學號姓名：寫進 workspace\tools\student.json
    [string]$StudentName,
    [string]$HandoutsDir = "$PSScriptRoot\handouts",      # 講義來源資料夾（沒有就略過）
    [string]$HomeworkDir = "$PSScriptRoot\homework",      # 作業來源資料夾（沒有就略過）
    # 下載網址的預設值在 config\sources.json（跟 Mac 版的 setup\build_mac.py 共用）
    [string]$WinPyUrl = (Get-Content -Raw -Encoding utf8 "$PSScriptRoot\config\sources.json" | ConvertFrom-Json).winpython,
    [string]$VSCodeUrl = (Get-Content -Raw -Encoding utf8 "$PSScriptRoot\config\sources.json" | ConvertFrom-Json).vscode_win,
    [string]$FontUrl = (Get-Content -Raw -Encoding utf8 "$PSScriptRoot\config\sources.json" | ConvertFrom-Json).font,
    [string]$UvUrl = (Get-Content -Raw -Encoding utf8 "$PSScriptRoot\config\sources.json" | ConvertFrom-Json).uv_windows,
    # 元件（精靈的「選擇元件」頁）：取消勾選不會移除之前已經建立好的部分
    [switch]$SkipVSCode,          # 不裝可攜式 VS Code（只用 JupyterLab）
    [switch]$SkipExtraExtensions, # 不裝附加的 VS Code 擴充（config\extensions-extra.txt：PDF / Excel 檢視…）
    [switch]$SkipJupyterLab,      # 不裝 JupyterLab（requirements-jupyterlab.txt），也不放 2_啟動JupyterLab.bat
    [switch]$SkipDocs,
    [switch]$SkipCheck,
    [switch]$NoLocalSettings,     # 不同步這台電腦的 VS Code 設定，只用考試設定
    [switch]$CleanDownloads,      # 完成後刪除下載快取（build\downloads，約 1 GB）
    [switch]$StrictCheck          # 環境檢查沒通過時結束代碼為 1（CI 用）
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if ([Console]::IsOutputRedirected) {
    # 被精靈導到 log 檔時用 UTF-8，中文才不會亂碼
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    $OutputEncoding = [Text.Encoding]::UTF8
}
$Repo = $PSScriptRoot
$Dl = Join-Path $Repo "build\downloads"
$Version = (Get-Content -Raw "$Repo\VERSION").Trim()
# 舊版留下、現在已經不用的檔案（相對於 STAT_EXAM\）；精靈複製到隨身碟前也會刪掉隨身碟上的這些
$LegacyFiles = @("5_新增考卷.bat", "workspace\tools\new_exam.py", "workspace\tools\templates")
New-Item -ItemType Directory -Force $Dl, $Out | Out-Null

# 每一步的耗時，最後印成總表（回報「很慢」時看 log 就知道慢在哪裡）
$StepClock = [Diagnostics.Stopwatch]::StartNew()
$StepTimes = [ordered]@{}
$script:CurrentStep = $null

function End-Step {
    if ($script:CurrentStep) { $StepTimes[$script:CurrentStep] = $StepClock.Elapsed }
    $script:CurrentStep = $null
}

function Step($msg) {
    End-Step
    $script:CurrentStep = $msg
    $StepClock.Restart()
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

# 背景預先下載（檔名 → curl 的 Process），讓下載跟安裝套件同時進行
$Prefetch = @{}
$extFailed = @()      # 沒裝好的 VS Code 擴充（Marketplace 暫時無法連線時），最後才回報失敗
trap { foreach ($p in $Prefetch.Values) { if (-not $p.HasExited) { $p.Kill() } }; break }

function Get-CurlArgs($url, $out) {
    # Windows 10 1803 起內建 curl.exe：比 Invoke-WebRequest 快，-C - 可以接著上次中斷的 .part 續傳
    return @("-L", "--fail", "-sS", "--retry", "3", "--retry-delay", "2", "-C", "-", "-o", $out, $url)
}

function Start-Prefetch($url, $name) {
    $path = Join-Path $Dl $name
    if (-not $url -or (Test-Path -LiteralPath $path) -or $Prefetch[$name]) { return }
    # Start-Process 不會幫參數加引號，路徑可能有空白
    $argString = (Get-CurlArgs $url "$path.part" | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' '
    $p = Start-Process "$env:SystemRoot\System32\curl.exe" -ArgumentList $argString -WindowStyle Hidden -PassThru
    $null = $p.Handle                               # 先取得 handle，結束後才讀得到 ExitCode
    $Prefetch[$name] = $p
}

function Get-File($url, $name) {
    $path = Join-Path $Dl $name
    if (Test-Path -LiteralPath $path) { return $path }
    $p = $Prefetch[$name]
    if ($p) {
        if (-not $p.HasExited) { Write-Host "等待背景下載 $name ..." }
        $p.WaitForExit()
        $Prefetch.Remove($name)
        if ($p.ExitCode -eq 0) {
            Move-Item -LiteralPath "$path.part" $path
            return $path
        }
    }
    Write-Host "下載 $name ..."
    & "$env:SystemRoot\System32\curl.exe" @(Get-CurlArgs $url "$path.part")
    if ($LASTEXITCODE -ne 0) {
        # curl 不會用系統的 proxy 設定，有些學校 / 公司網路要改用 Invoke-WebRequest
        Write-Host "curl 下載失敗（exit $LASTEXITCODE），改用 Invoke-WebRequest 重新下載 $name ..."
        $global:LASTEXITCODE = 0
        Invoke-WebRequest $url -OutFile "$path.part"
    }
    Move-Item -LiteralPath "$path.part" $path -Force
    return $path
}

function Run {
    # 執行外部程式，失敗就停止（用 $args，避免 -m 之類的參數被 PowerShell 吃掉）
    $exe, $rest = $args
    $rest = @($rest)            # 只有一個參數時 $rest 是字串，直接 splat 會被拆成一個一個字元
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

Write-Host "統計學考試環境 v$Version"

# ------------------------------------------------------------------ 1. WinPython
Step "1. WinPython"
$Ws = Join-Path $Out "workspace"
if (-not $SkipVSCode -and -not (Test-Path "$Out\VSCode\Code.exe")) { Start-Prefetch $VSCodeUrl "vscode-win32-x64.zip" }
Start-Prefetch $FontUrl "NotoSansTC-VF.ttf"
Start-Prefetch $UvUrl "uv-windows.zip"
$zip = Get-File $WinPyUrl (Split-Path $WinPyUrl -Leaf)
if (-not (Get-ChildItem $Out -Directory -Filter "WPy64-*" -ErrorAction SilentlyContinue)) {
    Expand-Zip $zip $Out
}
$WinPy = (Get-ChildItem $Out -Directory -Filter "WPy64-*" | Select-Object -First 1).FullName
$Py = Join-Path $WinPy "python\python.exe"
Write-Host "WinPython：$WinPy"
Use-PortableEnv $WinPy

# 離線文件的網址（Python 文件要配合 WinPython 的版本），先開始在背景下載
$docs = [ordered]@{}
if (-not $SkipDocs) {
    $pyMinor = (& $Py -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')").Trim()
    $src = Get-Content -Raw -Encoding utf8 "$Repo\config\sources.json" | ConvertFrom-Json
    # scipy 的離線文件不一定每個小版本都有，從文件首頁找目前提供的 zip
    $scipyZip = $null
    try {
        $href = (Invoke-WebRequest $src.docs_scipy_index -UseBasicParsing).Links.href |
            Where-Object { $_ -match '^scipy/scipy-html-[\d.]+\.zip$' } | Select-Object -First 1
        if ($href) { $scipyZip = $src.docs_scipy_index + $href }
    } catch { }
    $docs = [ordered]@{
        "pandas" = $src.docs_pandas
        "numpy"  = $src.docs_numpy
        "scipy"  = $scipyZip
        "python" = $src.docs_python -replace '\{minor\}', $pyMinor
    }
    foreach ($name in $docs.Keys) {
        if (-not (Test-Path "$Ws\docs-offline\$name")) { Start-Prefetch $docs[$name] "docs-$name.zip" }
    }
}

# ------------------------------------------------------------------ 2. 套件
Step "2. 安裝套件"
$reqArgs = @("-r", "$Repo\requirements.txt")
if (-not $SkipJupyterLab) { $reqArgs += @("-r", "$Repo\requirements-jupyterlab.txt") }
# uv 會平行下載、安裝，比 pip 快很多；拿不到 uv 或安裝失敗就改用 pip
$uv = $null
try {
    $uvZip = Get-File $UvUrl "uv-windows.zip"
    if (-not (Test-Path "$Dl\uv\uv.exe")) { Expand-Zip $uvZip "$Dl\uv" }
    $uv = (Get-ChildItem "$Dl\uv" -Recurse -Filter uv.exe | Select-Object -First 1).FullName
} catch {
    Write-Warning "拿不到 uv（$($_.Exception.Message)），改用 pip"
}
$installed = $false
if ($uv) {
    # --link-mode copy：uv 預設從快取 hardlink，建立位置跟快取不在同一顆 NTFS 磁碟（或被防毒鎖住）時會失敗；
    # 反正整個環境之後都要複製到隨身碟，直接複製最可靠，也不會跟 uv 的快取共用檔案
    & $uv pip install --python $Py --link-mode copy --compile-bytecode @reqArgs
    $installed = $LASTEXITCODE -eq 0
    if (-not $installed) { Write-Warning "uv 安裝失敗（exit $LASTEXITCODE），改用 pip" }
    $global:LASTEXITCODE = 0
}
if (-not $installed) {
    Run $Py -m pip install @reqArgs --no-warn-script-location --progress-bar off
}
# uv 產生的 Scripts\*.exe（jupyter、pylsp…）記的是建立時的路徑，複製到隨身碟就不能用；換成 WinPython 的 #!python.exe 格式
Run $Py "$Repo\tools\fix_launchers.py"
$site = (& $Py -c "import sysconfig; print(sysconfig.get_paths()['purelib'])").Trim()
# 套件附的測試檔（加起來上萬個檔案、數百 MB）考試用不到，刪掉之後防毒掃描、複製到隨身碟都快很多
foreach ($pkg in "numpy", "pandas", "scipy", "statsmodels", "sympy", "matplotlib", "mpl_toolkits", "seaborn", "IPython") {
    if (Test-Path -LiteralPath "$site\$pkg") {
        Get-ChildItem -LiteralPath "$site\$pkg" -Directory -Recurse -Filter tests -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}
# Python 每次啟動都執行 _stat_exam_env：能 import statkit、PATH 以隨身碟的 Python 優先、不讀 user site-packages
# （VS Code 不是從 1_ 啟動、或考場電腦也有 Python 時，匯出 HTML 才不會用到別的 jupyter-nbconvert）
Copy-Item "$Repo\setup\_stat_exam_env.py" "$site\_stat_exam_env.py" -Force
Set-Content -LiteralPath "$site\statkit_workspace.pth" -Encoding ascii -Value "import _stat_exam_env"
$labSettings = Join-Path $WinPy "python\share\jupyter\lab\settings"
New-Item -ItemType Directory -Force $labSettings | Out-Null
Copy-Item "$Repo\config\jupyterlab-overrides.json" "$labSettings\overrides.json" -Force
Write-Host "預先編譯 .pyc（加快隨身碟上的啟動速度）..."
# site-packages 在安裝時已經編譯過（uv --compile-bytecode / pip 預設），這裡只補標準函式庫
& $Py -m compileall -q -j 0 -x "site-packages" "$WinPy\python\Lib" *> $null
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
    $extFiles = @("$Repo\config\extensions.txt")
    if (-not $SkipExtraExtensions) { $extFiles += "$Repo\config\extensions-extra.txt" }
    $wantedExt = @(Get-Content $extFiles | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    function Get-MissingExtensions {
        $installed = @(& "$vsDir\bin\code.cmd" --list-extensions | ForEach-Object { $_.Trim().ToLower() })
        $global:LASTEXITCODE = 0
        return @($wantedExt | Where-Object { $installed -notcontains $_.ToLower() })
    }
    $missing = Get-MissingExtensions
    # VS Code Marketplace 偶爾會回 HTTP 503（暫時無法服務）：重試，後兩次一個一個裝，避免同時太多請求
    $waits = @(0, 20, 60)
    for ($try = 1; $try -le $waits.Count -and $missing; $try++) {
        if ($try -eq 1) {
            # 第一次一起裝：每呼叫一次 code.cmd 就要冷啟動一次 VS Code
            Write-Host "安裝擴充：$($missing -join ', ')"
            & "$vsDir\bin\code.cmd" @($missing | ForEach-Object { "--install-extension", $_ }) --force
        } else {
            Write-Host "還有 $($missing.Count) 個擴充沒裝好（VS Code Marketplace 可能暫時無法連線），$($waits[$try - 1]) 秒後重試（第 $try / $($waits.Count) 次）…"
            Start-Sleep -Seconds $waits[$try - 1]
            foreach ($id in $missing) { & "$vsDir\bin\code.cmd" --install-extension $id --force }
        }
        $global:LASTEXITCODE = 0
        $missing = Get-MissingExtensions
    }
    if ($missing) {
        # 備案：跟 Mac 版一樣直接下載 .vsix（curl 會自動重試 503），第 7 步前由 finish_setup.py 離線安裝
        Write-Host "改用直接下載 .vsix：$($missing -join ', ')"
        $env:STAT_VS_DIR = $vsDir; $env:STAT_EXT_IDS = $missing -join ","
        & $Py -c "import os, sys; from pathlib import Path; sys.path.insert(0, r'$Repo\setup'); import build_mac; build_mac.download_extensions(Path(os.environ['STAT_VS_DIR']), os.environ['STAT_EXT_IDS'].split(','))"
        if ($LASTEXITCODE -ne 0) { $extFailed = $missing; Write-Warning "下載 .vsix 也失敗：$($missing -join ', ')" }
        $global:LASTEXITCODE = 0
    }
    # 語言包快取（啟動器每次啟動前也會依目前的磁碟代號重建，第一次啟動就是中文）
    Run $Py "$Repo\tools\vscode_locale.py" "$vsDir\data"
}

# ------------------------------------------------------------------ 4. workspace
Step "4. workspace（程式、範本、筆記、講義、作業）"
foreach ($d in "statkit", "tools", "notes") { Copy-Tree "$Repo\$d" "$Ws\$d" }
# 開發用的檢查工具不用帶進隨身碟
Remove-Item -LiteralPath "$Ws\tools\ci", "$Ws\tools\validate_repo.py" -Recurse -Force -ErrorAction SilentlyContinue
# 講義與作業：預設是 repo 的 handouts\、homework\（不進版控），也可以用 -HandoutsDir / -HomeworkDir 指定
foreach ($pair in @(@("handouts", $HandoutsDir), @("homework", $HomeworkDir))) {
    $name, $src = $pair
    $what = if ($name -eq "handouts") { "講義" } else { "作業" }
    if (-not $src) {
        Write-Host "略過$what（沒有指定資料夾）"
    } elseif (Test-Path -LiteralPath $src) {
        Copy-Tree $src "$Ws\$name"
        Write-Host "已複製$what：$src"
    } else {
        Write-Host "略過$what（找不到資料夾：$src）"
    }
}
New-Item -ItemType Directory -Force "$Ws\exam", "$Ws\data", "$Ws\homework", "$Ws\fonts", "$Ws\.vscode" | Out-Null
# 舊版的「從空白範本新增考卷」已經改成「匯入老師給的考卷」，更新時把舊檔刪掉（exam\ 裡的考卷不動）
foreach ($old in $LegacyFiles) { Remove-Item -LiteralPath (Join-Path $Out $old) -Recurse -Force -ErrorAction SilentlyContinue }
Copy-Item "$Repo\VERSION" "$Ws\tools\VERSION" -Force
# 學號姓名（只用來在匯入考卷後提醒、匯出 HTML 時檢查考卷裡有沒有寫）：參數 → repo 的 config\student.json → 範例
if ($StudentId -and $StudentName) {
    [IO.File]::WriteAllText("$Ws\tools\student.json",
        (@{ id = $StudentId.Trim().ToUpper(); name = $StudentName.Trim() } | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
    Write-Host "學號姓名：$($StudentId.Trim().ToUpper()) $($StudentName.Trim())"
} elseif (Test-Path "$Repo\config\student.json") {
    Copy-Item "$Repo\config\student.json" "$Ws\tools\student.json" -Force
} elseif (-not (Test-Path "$Ws\tools\student.json")) {
    Write-Host "還沒設定學號姓名，第一次「匯入考卷」時會請你輸入（可以略過）"
    Copy-Item "$Repo\config\student.example.json" "$Ws\tools\student.json" -Force
}
Copy-Item "$Repo\templates\00_索引.ipynb" "$Ws\00_索引.ipynb" -Force
Copy-Item "$Repo\templates\常見問題.md" "$Ws\常見問題.md" -Force
Copy-Item "$Repo\templates\data_README.md" "$Ws\data\README.md" -Force
foreach ($pair in @(@("vscode-workspace-settings.json", "settings.json"), @("vscode-tasks.json", "tasks.json"))) {
    (Get-Content "$Repo\config\$($pair[0])" -Raw -Encoding utf8) -replace "__WINPY__", (Split-Path $WinPy -Leaf) |
        Set-Content "$Ws\.vscode\$($pair[1])" -Encoding utf8
}
if (Get-ChildItem "$Ws\handouts" -Filter *.pdf -ErrorAction SilentlyContinue) {
    Run $Py "$Ws\tools\extract_pdf_text.py" "$Ws\handouts"
}

# ------------------------------------------------------------------ 5. 字型與離線文件
Step "5. 中文字型與離線文件"
$font = Get-File $FontUrl "NotoSansTC-VF.ttf"
Copy-Item -LiteralPath $font "$Ws\fonts\NotoSansTC-VF.ttf" -Force
if (-not $SkipDocs) {
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
# 沒裝的編輯器就不放它的啟動檔（之前建立過的會留著，跟留下來的程式一致）
Get-ChildItem "$Repo\launchers\*.bat" |
    Where-Object { -not (($SkipVSCode -and $_.Name -like "1_*") -or ($SkipJupyterLab -and $_.Name -like "2_*")) } |
    Copy-Item -Destination $Out -Force
Copy-Item "$Repo\templates\使用說明.txt" $Out -Force
& $Py -m pip freeze | Set-Content "$Ws\tools\requirements-lock.txt" -Encoding utf8

# ------------------------------------------------------------------ 7. 檢查
# 第 3 步改用 .vsix 備案時，在這裡離線安裝（跟在 Mac 上建立的環境第一次啟動時一樣）
$pendingVsix = Join-Path $Out "VSCode\data\pending-vsix"
if (-not $SkipVSCode -and (Test-Path $pendingVsix)) {
    & $Py "$Ws\tools\finish_setup.py"
    $global:LASTEXITCODE = 0
    if (Get-ChildItem $pendingVsix -Filter *.vsix -ErrorAction SilentlyContinue) {
        $extFailed = @(Get-ChildItem $pendingVsix -Filter *.vsix | ForEach-Object { ($_.Name -split '__')[0] })
    }
}
if (-not $SkipCheck) {
    Step "7. 環境檢查"
    & $Py "$Ws\tools\check_env.py"
    $checkFailed = $LASTEXITCODE -ne 0
    if ($checkFailed) { Write-Warning "環境檢查有項目沒通過，請看上面的輸出" }
    $global:LASTEXITCODE = 0
}

if ($CleanDownloads -and (Test-Path $Dl)) {
    Remove-Item -LiteralPath $Dl -Recurse -Force
    Write-Host "已刪除下載快取：$Dl"
}

End-Step
Write-Host "`n各步驟耗時："
foreach ($k in $StepTimes.Keys) {
    $t = $StepTimes[$k]
    Write-Host ("  {0,3}:{1:00}  {2}" -f [int][math]::Floor($t.TotalMinutes), $t.Seconds, $k)
}

# 檔案數也印出來：精靈複製到隨身碟時用來算進度，不用再數一次
$files = Get-ChildItem $Out -Recurse -File -Force | Measure-Object Length -Sum
Write-Host ("`n完成：{0}（{1:N2} GB，{2} 個檔案）。把整個資料夾複製到隨身碟即可。" -f $Out, ($files.Sum / 1GB), $files.Count) -ForegroundColor Green
if ($extFailed) {
    # 精靈會把最後幾行當成失敗原因顯示，所以這段一定要放在最後
    Write-Host "`n✖ VS Code 擴充沒有裝好：$($extFailed -join ', ')"
    Write-Host "VS Code Marketplace 暫時無法連線。其他部分都已完成，請過幾分鐘再執行一次精靈（已完成的部分會沿用）。"
    exit 1
}
if ($StrictCheck -and $checkFailed) { exit 1 }
