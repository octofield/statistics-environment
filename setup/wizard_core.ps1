# 初始化精靈的核心邏輯（不含 UI），由 Setup-Wizard.ps1 載入，也可以單獨測試。

$script:IdPattern = '^[A-Za-z]\d{8}$'

# 各步驟大約佔整體時間的比例（用來算進度條；步驟 2 裝套件、3 VS Code、7 環境檢查最久）
$script:StepWeights = @{ 1 = 5; 2 = 30; 3 = 22; 4 = 5; 5 = 13; 6 = 2; 7 = 23 }

function Get-WizardDefaults {
    param([string]$RepoRoot)
    $desktop = [Environment]::GetFolderPath("Desktop")
    [pscustomobject]@{
        RepoRoot        = $RepoRoot
        Out             = Join-Path $desktop "STAT_EXAM"
        HandoutsDir     = $(if (Test-Path (Join-Path $RepoRoot "handouts")) { Join-Path $RepoRoot "handouts" } else { "" })
        HomeworkDir     = $(if (Test-Path (Join-Path $RepoRoot "homework")) { Join-Path $RepoRoot "homework" } else { "" })
        HasLocalVSCode  = Test-Path (Join-Path $env:APPDATA "Code\User\settings.json")
        LogDir          = Join-Path $env:LOCALAPPDATA "STAT_EXAM_Setup\logs"
    }
}

function Test-StudentId([string]$Id) {
    return [bool]($Id -match $script:IdPattern)
}

function ConvertTo-ArgString([string[]]$Items) {
    # 組成 Start-Process 用的參數字串（Windows 命令列規則）：值加引號；引號前的反斜線要加倍、
    # 引號本身跳脫；結尾的反斜線也要加倍，否則 "D:\講義\" 的 \" 會被當成跳脫的引號
    ($Items | ForEach-Object {
        if ($_ -match '^-[A-Za-z]') { return $_ }
        $v = $_ -replace '(\\*)"', '$1$1\"'
        $v = $v -replace '(\\+)$', '$1$1'
        '"' + $v + '"'
    }) -join ' '
}

function Get-BuildArguments {
    <# 依精靈的選項組出 build.ps1 的參數（string[]）。$Options 欄位：
       Out, StudentId, StudentName, HandoutsDir, HomeworkDir, Docs, SyncVSCode, CleanDownloads #>
    param($Options)
    $a = @("-Out", $Options.Out)
    if ($Options.StudentId -and $Options.StudentName) { $a += @("-StudentId", $Options.StudentId, "-StudentName", $Options.StudentName) }
    # 沒選資料夾就傳空字串，build.ps1 會略過（不要用 repo 預設的資料夾）
    $a += @("-HandoutsDir", [string]$Options.HandoutsDir, "-HomeworkDir", [string]$Options.HomeworkDir)
    if (-not $Options.Docs) { $a += "-SkipDocs" }
    if (-not $Options.SyncVSCode) { $a += "-NoLocalSettings" }
    if ($Options.CleanDownloads) { $a += "-CleanDownloads" }
    return , $a
}

function Get-RemovableDrives {
    # 卸除式磁碟（隨身碟）：DriveType = 2
    Get-CimInstance Win32_LogicalDisk -Filter "DriveType=2" -ErrorAction SilentlyContinue |
        Where-Object { $_.Size } |
        ForEach-Object {
            [pscustomobject]@{
                Drive  = $_.DeviceID
                Label  = $_.VolumeName
                FreeGB = [math]::Round($_.FreeSpace / 1GB, 1)
                SizeGB = [math]::Round($_.Size / 1GB, 1)
                FS     = $_.FileSystem
                Text   = "{0} {1}（剩 {2:N1} GB / 共 {3:N1} GB，{4}）" -f $_.DeviceID, $_.VolumeName, ($_.FreeSpace / 1GB), ($_.Size / 1GB), $_.FileSystem
            }
        }
}

function Get-FreeSpaceGB([string]$Path) {
    $root = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path))
    $d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($root.TrimEnd('\'))'" -ErrorAction SilentlyContinue
    if ($d) { return [math]::Round($d.FreeSpace / 1GB, 1) }
    return $null
}

function Get-RequiredGB([bool]$Docs) {
    # 打包後的大小（不含下載快取）：基本約 2.0 GB，離線文件約 0.65 GB
    return [math]::Round(2.0 + $(if ($Docs) { 0.65 } else { 0 }), 1)
}

function Get-BuildProgress {
    <# 從 build.ps1 的輸出解析進度：回傳 Step（目前第幾步）、Title、Percent（0–100）、Done #>
    param([string]$LogText, [int]$MaxPercent = 100)
    $steps = [regex]::Matches($LogText, '(?m)^=== (\d+)\. (.+?) ===')
    $done = $LogText -match '(?m)^完成：'
    if ($steps.Count -eq 0) { return [pscustomobject]@{ Step = 0; Title = "準備中"; Percent = 0; Done = $done } }
    $last = $steps[$steps.Count - 1]
    $n = [int]$last.Groups[1].Value
    $before = 0
    foreach ($k in $script:StepWeights.Keys) { if ($k -lt $n) { $before += $script:StepWeights[$k] } }
    $pct = if ($done) { 100 } else { $before }
    [pscustomobject]@{
        Step    = $n
        Title   = $last.Groups[2].Value
        Percent = [math]::Min($MaxPercent, [math]::Round($pct * $MaxPercent / 100))
        Done    = $done
    }
}

function Get-CheckResult {
    <# 從輸出解析環境檢查結果：Passed（$true / $false / $null = 沒跑檢查）、FailCount、Failures #>
    param([string]$LogText)
    $fails = [regex]::Matches($LogText, '(?m)^\[FAIL\] (.+)$') | ForEach-Object { $_.Groups[1].Value.Trim() }
    if ($LogText -match '全部通過') { $passed = $true }
    elseif ($LogText -match '有 (\d+) 項沒通過') { $passed = $false }
    else { $passed = $null }
    [pscustomobject]@{ Passed = $passed; FailCount = @($fails).Count; Failures = @($fails) }
}

function Read-NewText {
    <# 讀檔案從 $State.Pos 之後新增的內容（檔案正在被寫入也能讀）。$State 是 @{ Pos = 0 }。
       用同一個 Decoder 解碼，中文字的 UTF-8 位元組被切在兩次讀取之間也不會變亂碼。 #>
    param([string]$Path, [hashtable]$State)
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    if (-not $State.Decoder) { $State.Decoder = (New-Object Text.UTF8Encoding $false).GetDecoder() }
    $fs = [IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
    try {
        if ($fs.Length -le $State.Pos) { return "" }
        [void]$fs.Seek($State.Pos, 'Begin')
        $buf = New-Object byte[] ($fs.Length - $State.Pos)
        $read = $fs.Read($buf, 0, $buf.Length)
        $State.Pos += $read
        $chars = New-Object char[] ($State.Decoder.GetCharCount($buf, 0, $read))
        $n = $State.Decoder.GetChars($buf, 0, $read, $chars, 0)
        return (New-Object string($chars, 0, $n)).TrimStart([char]0xFEFF)
    } finally { $fs.Dispose() }
}

function Start-BuildProcess {
    <# 在背景執行 build.ps1，輸出寫到 log 檔。回傳 Process、LogPath、ErrPath #>
    param([string]$RepoRoot, [string[]]$BuildArgs, [string]$LogDir)
    New-Item -ItemType Directory -Force $LogDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $log = Join-Path $LogDir "build_$stamp.log"
    $err = Join-Path $LogDir "build_$stamp.err.log"
    $argString = "-NoProfile -ExecutionPolicy Bypass -File " + (ConvertTo-ArgString @((Join-Path $RepoRoot "build.ps1"))) +
                 " " + (ConvertTo-ArgString $BuildArgs)
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argString -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError $err
    [pscustomobject]@{ Process = $p; LogPath = $log; ErrPath = $err; Command = "powershell.exe $argString" }
}

function Stop-ProcessTree([int]$ProcessId) {
    # 連同底下的 python / pip / VS Code 安裝程序一起結束
    & "$env:SystemRoot\System32\taskkill.exe" /PID $ProcessId /T /F 2>&1 | Out-Null
}

function Start-UsbCopy {
    <# 用 robocopy 把 STAT_EXAM 複製到隨身碟（只新增 / 更新，不會刪掉隨身碟上 exam\ 裡的考卷）#>
    param([string]$Source, [string]$Drive, [string]$LogDir)
    New-Item -ItemType Directory -Force $LogDir | Out-Null
    $dst = Join-Path ($Drive.TrimEnd('\') + '\') (Split-Path $Source -Leaf)
    $log = Join-Path $LogDir ("copy_{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    $total = (Get-ChildItem -LiteralPath $Source -Recurse -File -Force | Measure-Object).Count
    # 不能排除 __pycache__：WinPython 裡預先編譯好的 .pyc 是讓隨身碟啟動變快的關鍵
    $argString = (ConvertTo-ArgString @($Source, $dst)) + " /E /MT:8 /R:1 /W:1 /NP /NDL /NJH /NJS " +
                 (ConvertTo-ArgString @("/UNILOG:$log"))
    $p = Start-Process -FilePath "$env:SystemRoot\System32\robocopy.exe" -ArgumentList $argString -WindowStyle Hidden -PassThru
    [pscustomobject]@{ Process = $p; LogPath = $log; Destination = $dst; Total = $total }
}

function Get-CopyProgress {
    # /UNILOG 是 UTF-16 的 log，每複製一個檔案一行
    param([string]$LogPath, [int]$Total)
    if (-not (Test-Path -LiteralPath $LogPath) -or $Total -le 0) { return 0 }
    $fs = [IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
    try {
        $reader = New-Object IO.StreamReader($fs, [Text.Encoding]::Unicode)
        $lines = 0
        while ($null -ne $reader.ReadLine()) { $lines++ }
    } finally { $fs.Dispose() }
    return [math]::Min(100, [math]::Round($lines * 100 / $Total))
}
