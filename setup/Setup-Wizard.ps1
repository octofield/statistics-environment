<#
.SYNOPSIS
  統計學考試環境 初始化精靈（圖形介面）。由 setup.cmd 或 Setup.exe 啟動。

  一步一步設定學號姓名、講義與作業、選項，接著在背景執行 build.ps1 建立環境，
  完成後可以直接複製到隨身碟。

  開發 / 測試用參數：
    -TestOptions <json>   預先填好選項（欄位同 $S；另外可以給 LatestTag 模擬 GitHub 上的最新版本）
    -AutoStart            開啟後直接開始建立（搭配 -TestOptions）
    -AutoClose            完成後自動關閉
    -ResultFile <path>    把結果寫成 JSON
    -ScreenshotDir <dir>  把每一頁截圖成 PNG 後關閉（不會真的建立）
#>
param(
    [string]$TestOptions,
    [switch]$AutoStart,
    [switch]$AutoClose,
    [string]$ResultFile,
    [string]$ScreenshotDir
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
try {
    Add-Type -Namespace Native -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
    [void][Native.Dpi]::SetProcessDPIAware()
} catch { }

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Split-Path -Parent $Here
. (Join-Path $Here "wizard_core.ps1")
$D = Get-WizardDefaults $Repo

# ------------------------------------------------------------------ 狀態
$S = @{
    Ack = $false; StudentId = ""; StudentName = ""; SkipStudent = $false
    HandoutsDir = $D.HandoutsDir; HomeworkDir = $D.HomeworkDir
    VSCode = $true; VSCodeExtras = $true; JupyterLab = $true; Docs = $true      # 元件：預設全裝
    Out = $D.Out; SyncVSCode = $D.HasLocalVSCode; CleanDownloads = $true
    CopyUsb = $false; UsbDrive = ""
    Status = ""; Log = ""; Err = ""; Job = $null; Copy = $null; Check = $null; ExitCode = $null
}
$ownStudent = Join-Path $Repo "config\student.json"
if (Test-Path $ownStudent) {
    $st = Get-Content $ownStudent -Raw -Encoding UTF8 | ConvertFrom-Json
    $S.StudentId = $st.id; $S.StudentName = $st.name
}
if ($TestOptions) {
    $t = Get-Content $TestOptions -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($p in $t.PSObject.Properties) { $S[$p.Name] = $p.Value }
}

# ------------------------------------------------------------------ 外觀
$fontName = if ([Drawing.FontFamily]::Families.Name -contains "Microsoft JhengHei UI") { "Microsoft JhengHei UI" } else { "Segoe UI" }
$F = New-Object Drawing.Font($fontName, 10)
$FB = New-Object Drawing.Font($fontName, 10, [Drawing.FontStyle]::Bold)
$FT = New-Object Drawing.Font($fontName, 15, [Drawing.FontStyle]::Bold)
$FS = New-Object Drawing.Font($fontName, 9)
$FM = New-Object Drawing.Font("Consolas", 9)
$Accent = [Drawing.Color]::FromArgb(42, 120, 214)
$Muted = [Drawing.Color]::FromArgb(90, 90, 90)

function Add-Label($parent, $text, $x, $y, $w, $h, $font = $F, $color = $null) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Location = New-Object Drawing.Point($x, $y); $l.Size = New-Object Drawing.Size($w, $h)
    $l.Font = $font; if ($color) { $l.ForeColor = $color }
    $parent.Controls.Add($l); return $l
}
function Add-Button($parent, $text, $x, $y, $w = 100, $h = 32) {
    $b = New-Object Windows.Forms.Button
    $b.Text = $text; $b.Location = New-Object Drawing.Point($x, $y); $b.Size = New-Object Drawing.Size($w, $h); $b.Font = $F
    $parent.Controls.Add($b); return $b
}
function Add-TextBox($parent, $text, $x, $y, $w, $h = 28) {
    $t = New-Object Windows.Forms.TextBox
    $t.Text = $text; $t.Location = New-Object Drawing.Point($x, $y); $t.Size = New-Object Drawing.Size($w, $h); $t.Font = $F
    $parent.Controls.Add($t); return $t
}
function Add-CheckBox($parent, $text, $x, $y, $w, $h, $checked) {
    $c = New-Object Windows.Forms.CheckBox
    $c.Text = $text; $c.Location = New-Object Drawing.Point($x, $y); $c.Size = New-Object Drawing.Size($w, $h)
    $c.Font = $F; $c.Checked = [bool]$checked
    $parent.Controls.Add($c); return $c
}
function New-Page {
    $p = New-Object Windows.Forms.Panel
    $p.Location = New-Object Drawing.Point(24, 92); $p.Size = New-Object Drawing.Size(732, 400); $p.Visible = $false
    $form.Controls.Add($p); return $p
}
function Select-Folder($description, $initial) {
    $dlg = New-Object Windows.Forms.FolderBrowserDialog
    $dlg.Description = $description; $dlg.ShowNewFolderButton = $true
    if ($initial -and (Test-Path $initial)) { $dlg.SelectedPath = $initial }
    if ($dlg.ShowDialog($form) -eq "OK") { return $dlg.SelectedPath }
    return $null
}
function Show-Message($text, $buttons = "OK", $icon = "Information") {
    return [Windows.Forms.MessageBox]::Show($form, $text, "統計學考試環境", $buttons, $icon)
}
function Describe-Folder($path) {
    if (-not $path) { return "（未選擇）" }
    if (-not (Test-Path -LiteralPath $path)) { return "⚠ 找不到這個資料夾" }
    $files = @(Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue)
    $pdf = @($files | Where-Object Extension -eq ".pdf").Count
    $nb = @($files | Where-Object Extension -eq ".ipynb").Count
    return "共 $($files.Count) 個檔案（PDF $pdf 個、notebook $nb 個）"
}

# ------------------------------------------------------------------ 視窗框架
$form = New-Object Windows.Forms.Form
$form.SuspendLayout()
$form.AutoScaleDimensions = New-Object Drawing.SizeF(96, 96)
$form.AutoScaleMode = "Dpi"
$form.Text = "統計學考試環境 初始化精靈 v$($D.Version)"
$form.ClientSize = New-Object Drawing.Size(780, 560)
$form.FormBorderStyle = "FixedDialog"; $form.MaximizeBox = $false
$form.StartPosition = "CenterScreen"; $form.Font = $F; $form.BackColor = [Drawing.Color]::White

$header = New-Object Windows.Forms.Panel
$header.Location = New-Object Drawing.Point(0, 0); $header.Size = New-Object Drawing.Size(780, 76)
$header.BackColor = [Drawing.Color]::FromArgb(242, 246, 252)
$form.Controls.Add($header)
$hTitle = Add-Label $header "" 24 12 730 32 $FT
$hSub = Add-Label $header "" 26 46 400 22 $FS $Muted
# 有新版時才出現（開啟精靈時在背景查 GitHub，見最下面的 Start-UpdateCheck）
$lnkUpdate = New-Object Windows.Forms.LinkLabel
$lnkUpdate.AutoSize = $false
$lnkUpdate.Location = New-Object Drawing.Point(430, 46); $lnkUpdate.Size = New-Object Drawing.Size(330, 22)
$lnkUpdate.TextAlign = "MiddleRight"; $lnkUpdate.Font = $FB; $lnkUpdate.Visible = $false
$lnkUpdate.BackColor = [Drawing.Color]::FromArgb(255, 236, 179); $lnkUpdate.LinkColor = [Drawing.Color]::FromArgb(150, 80, 0)
$header.Controls.Add($lnkUpdate); $lnkUpdate.BringToFront()
$lnkUpdate.Add_LinkClicked({ Start-Process $this.Tag })

$line = New-Object Windows.Forms.Label
$line.Location = New-Object Drawing.Point(0, 500); $line.Size = New-Object Drawing.Size(780, 1)
$line.BorderStyle = "Fixed3D"; $form.Controls.Add($line)
$btnBack = Add-Button $form "< 上一步" 434 514
$btnNext = Add-Button $form "下一步 >" 544 514
$btnCancel = Add-Button $form "取消" 656 514

# ------------------------------------------------------------------ 第 1 頁：歡迎
$pWelcome = New-Page
Add-Label $pWelcome "幫你做出可以帶進考場、完全離線的 Python 統計考試環境，複製到隨身碟、換電腦都能用。" 0 0 732 44 $FB | Out-Null
# 兩欄：建立時準備好什麼 / 考試時好用的（完整說明在 README）
$welcomeCols = @(
    @{ X = 0; Title = "建立時會幫你準備好"; Items = @(
        "Python 3.13 與統計套件（pandas、scipy…）"
        "可攜式 VS Code：繁中介面、關閉所有 AI"
        "JupyterLab 備案（規定要用 Jupyter 也行）"
        "講義、作業：PDF 轉成文字，可以全文搜尋"
        "pandas / numpy / scipy 等離線官方文件") }
    @{ X = 376; Title = "考試時好用的"; Items = @(
        "匯入考卷：自動加好 import 與初始設定"
        "statkit：一行算機率、畫圖，附課程寫法"
        "60 個 snippets：打前綴 + Tab 就有程式碼"
        "各章筆記、公式總表、常見問題"
        "一鍵匯出 HTML：自動檢查錯誤並備份") }
)
foreach ($col in $welcomeCols) {
    Add-Label $pWelcome $col.Title $col.X 52 356 24 $FB $Accent | Out-Null
    for ($k = 0; $k -lt $col.Items.Count; $k++) {
        Add-Label $pWelcome "• $($col.Items[$k])" $col.X (82 + 34 * $k) 356 28 $F | Out-Null
    }
}
Add-Label $pWelcome ("需要：網路（下載約 1 GB）、約 3 GB 空間、15–40 分鐘，不需要系統管理員權限。" +
    "所有軟體都從官方網站下載；你的講義、作業不會上傳到任何地方。") 0 266 732 40 $FS $Muted | Out-Null
$lnkReadme = New-Object Windows.Forms.LinkLabel
$lnkReadme.AutoSize = $false; $lnkReadme.TextAlign = "MiddleRight"; $lnkReadme.Font = $F
$lnkReadme.Text = "看完整功能介紹與使用方式 →"
$lnkReadme.Location = New-Object Drawing.Point(432, 371); $lnkReadme.Size = New-Object Drawing.Size(300, 26)
$lnkReadme.Add_LinkClicked({ Start-Process $D.ReadmePage })
$pWelcome.Controls.Add($lnkReadme)
$warn = New-Object Windows.Forms.Panel
$warn.Location = New-Object Drawing.Point(0, 308); $warn.Size = New-Object Drawing.Size(732, 54)
$warn.BackColor = [Drawing.Color]::FromArgb(255, 248, 225); $pWelcome.Controls.Add($warn)
Add-Label $warn ("⚠ 本工具不是學校或課程的官方工具。各課程的考試規定不同（例如是否允許 VS Code、是否一定要用 Jupyter、" +
    "能不能帶哪些檔案），使用前請自行確認考試規定。本工具已關閉 AI 功能，但是否符合規定仍由使用者自行負責。") 12 7 708 42 $FS ([Drawing.Color]::FromArgb(120, 80, 0)) | Out-Null
$chkAck = Add-CheckBox $pWelcome "我了解，會自行確認考試規定" 0 370 420 28 $S.Ack

# ------------------------------------------------------------------ 第 2 頁：學號姓名
$pStudent = New-Page
Add-Label $pStudent ("學號姓名不會自動寫進考卷（考卷是老師給的 ipynb，保留原檔名）；" +
    "匯入考卷後會提醒你填，匯出 HTML 時如果考卷裡找不到你的學號會警告。") 0 0 732 44 | Out-Null
Add-Label $pStudent "學號" 0 50 80 26 $FB | Out-Null
$txtId = Add-TextBox $pStudent $S.StudentId 90 47 220
Add-Label $pStudent "1 個英文字母 + 8 個數字，例如 B12345678" 324 50 400 26 $FS $Muted | Out-Null
Add-Label $pStudent "姓名" 0 95 80 26 $FB | Out-Null
$txtName = Add-TextBox $pStudent $S.StudentName 90 92 220
$chkSkip = Add-CheckBox $pStudent "先略過（第一次「匯入考卷」時可以再輸入）" 0 145 500 30 $S.SkipStudent
Add-Label $pStudent "之後要改：用記事本打開 STAT_EXAM\workspace\tools\student.json。" 0 190 732 50 $FS $Muted | Out-Null
$chkSkip.Add_CheckedChanged({ $txtId.Enabled = -not $chkSkip.Checked; $txtName.Enabled = -not $chkSkip.Checked })

# ------------------------------------------------------------------ 第 3 頁：講義與作業
$pFiles = New-Page
Add-Label $pFiles ("選擇你自己的講義、作業資料夾（選填）。檔案只會複製到 workspace\handouts、workspace\homework，" +
    "講義的 PDF 會另外轉成文字，方便在 VS Code 用 Ctrl+Shift+F 搜尋。都不選也可以。") 0 0 732 48 | Out-Null
$folderRows = @{}
$y = 70
foreach ($kind in @("HandoutsDir", "HomeworkDir")) {
    $title = if ($kind -eq "HandoutsDir") { "講義資料夾" } else { "作業資料夾" }
    Add-Label $pFiles $title 0 ($y + 3) 100 26 $FB | Out-Null
    $tb = Add-TextBox $pFiles $S[$kind] 104 $y 440
    $browse = Add-Button $pFiles "瀏覽…" 554 ($y - 2) 80
    $clear = Add-Button $pFiles "清除" 642 ($y - 2) 80
    $info = Add-Label $pFiles (Describe-Folder $S[$kind]) 104 ($y + 34) 600 22 $FS $Muted
    $folderRows[$kind] = @{ Box = $tb; Info = $info }
    $browse.Tag = $kind; $clear.Tag = $kind; $tb.Tag = $kind
    $browse.Add_Click({
        $k = $this.Tag; $row = $folderRows[$k]
        $picked = Select-Folder "選擇資料夾" $row.Box.Text
        if ($picked) { $row.Box.Text = $picked }
    })
    $clear.Add_Click({ $folderRows[$this.Tag].Box.Text = "" })
    $tb.Add_TextChanged({ $folderRows[$this.Tag].Info.Text = Describe-Folder $this.Text })
    $y += 100
}
Add-Label $pFiles "講義、作業通常有著作權或個人資料，請不要把這些檔案上傳到公開的地方。" 0 290 732 26 $FS $Muted | Out-Null

# ------------------------------------------------------------------ 第 4 頁：選擇元件
$pComps = New-Page
Add-Label $pComps ("預設全部安裝，不需要的可以取消勾選（VS Code 和 JupyterLab 至少要留一個）。" +
    "之後想加回來，用同一個建立位置再執行一次精靈就好；取消勾選不會刪除之前已經建立好的部分。") 0 0 732 44 $FS $Muted | Out-Null
$GB = $script:ComponentGB
$compRows = @(
    @{ Key = "VSCode"; X = 0; Text = "可攜式 VS Code 與必要擴充（約 $($GB.VSCode) GB）"
       Note = "主力編輯器：Python、Pylance、Jupyter、繁中介面、snippets、一鍵匯出 HTML。`n不裝：只能用 JupyterLab 作答，匯出 HTML 改用 3_匯出HTML.bat。" }
    @{ Key = "VSCodeExtras"; X = 24; Text = "附加 VS Code 擴充：PDF 檢視、Excel 檢視、Rainbow CSV、Code Runner（約 25 MB）"
       Note = "不裝：講義 PDF、Excel 資料不能在 VS Code 裡打開，考場電腦不一定有其他程式可以開。" }
    @{ Key = "JupyterLab"; X = 0; Text = "JupyterLab 備案（約 $($GB.JupyterLab) GB）"
       Note = "在瀏覽器作答的備案，有些課程規定一定要用 Jupyter Lab。`n不裝：VS Code 出問題時沒有備案，也不會有 2_啟動JupyterLab.bat。" }
    @{ Key = "Docs"; X = 0; Text = "離線文件：pandas / numpy / scipy / Python（約 $($GB.Docs) GB、2 萬個檔案）"
       Note = "不裝：只能用滑鼠停在函式上或 Shift+Tab 看說明；好處是複製到隨身碟會快很多。" }
)
$compChecks = @{}
$y = 54
foreach ($row in $compRows) {
    $compChecks[$row.Key] = Add-CheckBox $pComps $row.Text $row.X $y (732 - $row.X) 26 $S[$row.Key]
    $compChecks[$row.Key].Font = $FB
    Add-Label $pComps $row.Note ($row.X + 20) ($y + 28) (712 - $row.X) 40 $FS $Muted | Out-Null
    $y += 82
}

# ------------------------------------------------------------------ 第 5 頁：選項
$pOpts = New-Page
Add-Label $pOpts "建立位置" 0 3 90 26 $FB | Out-Null
$txtOut = Add-TextBox $pOpts $S.Out 94 0 530
$btnOut = Add-Button $pOpts "瀏覽…" 634 -2 90
$lblOut = Add-Label $pOpts "" 94 32 630 22 $FS $Muted
$vsText = if ($D.HasLocalVSCode) { "同步這台電腦的 VS Code 設定（字體大小、快捷鍵、介面語言…；AI 相關設定一律排除）" } else { "同步這台電腦的 VS Code 設定（這台電腦沒有安裝 VS Code，無法同步）" }
$chkSync = Add-CheckBox $pOpts $vsText 0 64 732 28 ($S.SyncVSCode -and $D.HasLocalVSCode)
$chkClean = Add-CheckBox $pOpts "完成後刪除下載快取（省約 1 GB；之後要重新建立需要再下載）" 0 96 732 28 $S.CleanDownloads
$chkUsb = Add-CheckBox $pOpts "完成後複製到隨身碟" 0 140 300 28 $S.CopyUsb
$cmbUsb = New-Object Windows.Forms.ComboBox
$cmbUsb.DropDownStyle = "DropDownList"; $cmbUsb.Location = New-Object Drawing.Point(24, 172); $cmbUsb.Size = New-Object Drawing.Size(520, 28); $cmbUsb.Font = $F
$pOpts.Controls.Add($cmbUsb)
$btnUsbRefresh = Add-Button $pOpts "重新整理" 554 170 100
$lblUsb = Add-Label $pOpts "會複製到「隨身碟:\STAT_EXAM」；隨身碟上已經有的考卷不會被刪除。" 24 206 700 22 $FS $Muted
# 沒裝 VS Code 時，附加擴充和同步設定都沒有意義
function Update-CompState {
    $vs = $compChecks.VSCode.Checked
    $compChecks.VSCodeExtras.Enabled = $vs
    $chkSync.Enabled = $vs -and $D.HasLocalVSCode
}
$compChecks.VSCode.Add_CheckedChanged({ Update-CompState })
Update-CompState
$script:Drives = @()
function Update-Drives {
    $script:Drives = @(Get-RemovableDrives)
    $cmbUsb.Items.Clear()
    foreach ($d in $script:Drives) { [void]$cmbUsb.Items.Add($d.Text) }
    if ($cmbUsb.Items.Count -gt 0) {
        $idx = [array]::IndexOf(@($script:Drives.Drive), $S.UsbDrive)
        $cmbUsb.SelectedIndex = [math]::Max(0, $idx)
    } else { [void]$cmbUsb.Items.Add("（找不到隨身碟，請插上後按「重新整理」）"); $cmbUsb.SelectedIndex = 0 }
}
function Update-OutInfo {
    $o = $txtOut.Text.Trim()
    if (-not $o) { $lblOut.Text = ""; return }
    $free = Get-FreeSpaceGB $o
    $exists = Test-Path (Join-Path $o "WPy64-*")
    $old = if ($exists) { Get-EnvVersion $o }
    $what = if (-not $exists) { "會建立新的環境（v$($D.Version)）" }
            elseif ($old -eq $D.Version) { "已經有 v$old 的環境，會重新檢查並補齊（exam\ 裡的考卷不會被刪除）" }
            else { "已經有環境（$(if ($old) { "v$old" } else { '舊版' })），會更新成 v$($D.Version)（exam\ 裡的考卷不會被刪除）" }
    $lblOut.Text = $what +
                   $(if ($null -ne $free) { "　｜　這顆磁碟剩 $free GB" } else { "" })
}
$btnOut.Add_Click({
    $picked = Select-Folder "選擇要建立在哪個資料夾（會在裡面建立 STAT_EXAM）" (Split-Path $txtOut.Text -Parent)
    if ($picked) { $txtOut.Text = $(if ((Split-Path $picked -Leaf) -eq "STAT_EXAM") { $picked } else { Join-Path $picked "STAT_EXAM" }) }
})
$txtOut.Add_TextChanged({ Update-OutInfo })
$btnUsbRefresh.Add_Click({ Update-Drives })
$chkUsb.Add_CheckedChanged({ $cmbUsb.Enabled = $chkUsb.Checked; $btnUsbRefresh.Enabled = $chkUsb.Checked })
Update-Drives; Update-OutInfo
$cmbUsb.Enabled = $chkUsb.Checked; $btnUsbRefresh.Enabled = $chkUsb.Checked

# ------------------------------------------------------------------ 第 5 頁：確認
$pConfirm = New-Page
Add-Label $pConfirm "請確認以下設定，按「開始建立」後會開始下載與安裝：" 0 0 732 26 | Out-Null
$txtSummary = New-Object Windows.Forms.TextBox
$txtSummary.Multiline = $true; $txtSummary.ReadOnly = $true; $txtSummary.BackColor = [Drawing.Color]::FromArgb(248, 248, 248)
$txtSummary.Location = New-Object Drawing.Point(0, 34); $txtSummary.Size = New-Object Drawing.Size(732, 300); $txtSummary.Font = $F
$txtSummary.ScrollBars = "Vertical"; $pConfirm.Controls.Add($txtSummary)
Add-Label $pConfirm "建立過程中可以繼續用電腦，但請不要關閉這個視窗，也不要讓電腦睡眠。" 0 344 732 26 $FS $Muted | Out-Null

# ------------------------------------------------------------------ 第 6 頁：進度
$pProg = New-Page
$lblStep = Add-Label $pProg "準備中…" 0 0 732 28 $FB
$bar = New-Object Windows.Forms.ProgressBar
$bar.Location = New-Object Drawing.Point(0, 34); $bar.Size = New-Object Drawing.Size(732, 24); $bar.Maximum = 100
$pProg.Controls.Add($bar)
$lblStatus = Add-Label $pProg "" 0 66 732 44 $FS $Muted
$lblTime = Add-Label $pProg "" 0 112 400 22 $FS $Muted
$chkLog = Add-CheckBox $pProg "顯示詳細紀錄" 560 108 172 26 $false
$txtLog = New-Object Windows.Forms.TextBox
$txtLog.Multiline = $true; $txtLog.ReadOnly = $true; $txtLog.ScrollBars = "Both"; $txtLog.WordWrap = $false
$txtLog.MaxLength = 0; $txtLog.Font = $FM; $txtLog.Visible = $false
$txtLog.Location = New-Object Drawing.Point(0, 140); $txtLog.Size = New-Object Drawing.Size(732, 255)
$pProg.Controls.Add($txtLog)
$chkLog.Add_CheckedChanged({ $txtLog.Visible = $chkLog.Checked })

# ------------------------------------------------------------------ 第 7 頁：完成
$pDone = New-Page
$lblResult = Add-Label $pDone "" 0 0 732 34 $FT
$lblDetail = Add-Label $pDone "" 0 40 732 90 $F
Add-Label $pDone "接下來：" 0 140 732 26 $FB | Out-Null
$lblNext = Add-Label $pDone ("1. 打開 STAT_EXAM\使用說明.txt，了解每個啟動檔的用途`n" +
    "2. 拔掉網路，雙擊 4_環境檢查.bat，確認斷網也能用`n" +
    "3. 雙擊 5_匯入考卷.bat，選一份作業的 ipynb 當成考卷匯入，在 VS Code 寫一題、匯出 HTML 試試看`n" +
    "4. 換一台電腦再試一次（確認換磁碟代號也能用）") 0 168 732 100
$btnOpenOut = Add-Button $pDone "開啟 STAT_EXAM" 0 290 170
$btnOpenGuide = Add-Button $pDone "開啟使用說明" 180 290 150
$btnOpenUsb = Add-Button $pDone "開啟隨身碟" 340 290 150
$btnOpenLog = Add-Button $pDone "開啟紀錄檔" 500 290 150
Add-Label $pDone "有問題可以附上紀錄檔回報（紀錄檔不含你的講義、作業內容）。" 0 334 732 22 $FS $Muted | Out-Null
$btnOpenOut.Add_Click({ if (Test-Path $S.Out) { Start-Process explorer.exe $S.Out } })
$btnOpenGuide.Add_Click({ $g = Join-Path $S.Out "使用說明.txt"; if (Test-Path $g) { Start-Process notepad.exe $g } })
$btnOpenUsb.Add_Click({ if ($S.Copy -and (Test-Path $S.Copy.Destination)) { Start-Process explorer.exe $S.Copy.Destination } })
$btnOpenLog.Add_Click({ if ($S.Job) { Start-Process notepad.exe $S.Job.LogPath } })

$pages = @($pWelcome, $pStudent, $pFiles, $pComps, $pOpts, $pConfirm, $pProg, $pDone)
$titles = @("歡迎使用統計學考試環境 初始化精靈", "學號與姓名", "講義與作業", "選擇元件", "選項", "確認設定", "正在建立環境", "完成")
# 頁碼用名字對應，加頁的時候不用到處改數字
$iWelcome, $iStudent, $iFiles, $iComps, $iOpts, $iConfirm, $iProg, $iDone = 0..($pages.Count - 1)
$script:Page = 0

function Show-Page([int]$i) {
    $script:Page = $i
    for ($k = 0; $k -lt $pages.Count; $k++) { $pages[$k].Visible = ($k -eq $i) }
    $hTitle.Text = $titles[$i]
    $hSub.Text = if ($i -le $iConfirm) { "步驟 $($i + 1) / $($iConfirm + 1)" } elseif ($i -eq $iProg) { "請稍候，不要關閉這個視窗" } else { "" }
    $btnBack.Visible = ($i -ge 1 -and $i -le $iConfirm)
    $btnNext.Visible = ($i -ne $iProg)
    $btnNext.Text = if ($i -eq $iConfirm) { "開始建立" } elseif ($i -eq $iDone) { "完成" } else { "下一步 >" }
    $btnCancel.Visible = ($i -ne $iDone)
    $btnCancel.Text = if ($i -eq $iProg) { "停止" } else { "取消" }
    if ($i -eq $iConfirm) { $txtSummary.Text = Get-Summary }
}

function Save-Inputs {
    $S.Ack = $chkAck.Checked
    $S.StudentId = $txtId.Text.Trim().ToUpper(); $S.StudentName = $txtName.Text.Trim(); $S.SkipStudent = $chkSkip.Checked
    $S.HandoutsDir = $folderRows["HandoutsDir"].Box.Text.Trim(); $S.HomeworkDir = $folderRows["HomeworkDir"].Box.Text.Trim()
    foreach ($k in $compChecks.Keys) { $S[$k] = $compChecks[$k].Checked }
    $S.VSCodeExtras = $S.VSCodeExtras -and $S.VSCode
    $S.Out = $txtOut.Text.Trim(); $S.SyncVSCode = $chkSync.Checked -and $D.HasLocalVSCode -and $S.VSCode
    $S.CleanDownloads = $chkClean.Checked; $S.CopyUsb = $chkUsb.Checked
    $S.UsbDrive = if ($chkUsb.Checked -and $script:Drives.Count -gt 0 -and $cmbUsb.SelectedIndex -ge 0) { $script:Drives[$cmbUsb.SelectedIndex].Drive } else { "" }
}

function Test-Page([int]$i) {
    Save-Inputs
    switch ($i) {
        $iWelcome { if (-not $S.Ack) { [void](Show-Message "請先勾選「我了解，會自行確認考試規定」。"); return $false } }
        $iStudent {
            if ($S.SkipStudent) { return $true }
            if (-not $S.StudentId -or -not $S.StudentName) { [void](Show-Message "請輸入學號和姓名，或勾選「先略過」。"); return $false }
            if (-not (Test-StudentId $S.StudentId)) {
                $r = Show-Message "學號「$($S.StudentId)」的格式不是 1 個英文字母 + 8 個數字，確定要使用嗎？" "YesNo" "Question"
                if ($r -ne "Yes") { return $false }
            }
        }
        $iFiles {
            foreach ($k in "HandoutsDir", "HomeworkDir") {
                if ($S[$k] -and -not (Test-Path -LiteralPath $S[$k])) { [void](Show-Message "找不到資料夾：$($S[$k])"); return $false }
            }
        }
        $iComps {
            if (-not $S.VSCode -and -not $S.JupyterLab) {
                [void](Show-Message "VS Code 和 JupyterLab 至少要選一個，不然沒有地方可以寫考卷。"); return $false
            }
            if (-not $S.JupyterLab) {
                $r = Show-Message ("不裝 JupyterLab 的話，VS Code 出問題時就沒有備案；有些課程也規定要用 Jupyter Lab。`n`n確定不裝嗎？") "YesNo" "Warning"
                if ($r -ne "Yes") { return $false }
            }
        }
        $iOpts {
            if (-not $S.Out) { [void](Show-Message "請選擇建立位置。"); return $false }
            $need = (Get-RequiredGB $S) + 1.2               # 加上下載快取
            $free = Get-FreeSpaceGB $S.Out
            if ($null -ne $free -and $free -lt $need -and -not (Test-Path (Join-Path $S.Out "WPy64-*"))) {
                if ((Show-Message "建立位置的磁碟只剩 $free GB，建議至少 $need GB，還是要繼續嗎？" "YesNo" "Warning") -ne "Yes") { return $false }
            }
            if ($S.CopyUsb) {
                if (-not $S.UsbDrive) { [void](Show-Message "找不到隨身碟。請插上隨身碟後按「重新整理」，或取消勾選「複製到隨身碟」。"); return $false }
                $d = $script:Drives | Where-Object Drive -eq $S.UsbDrive
                $need = Get-RequiredGB $S
                if ($d.FreeGB -lt $need -and -not (Test-Path (Join-Path $S.UsbDrive "STAT_EXAM"))) {
                    if ((Show-Message "隨身碟只剩 $($d.FreeGB) GB，需要大約 $need GB，還是要繼續嗎？" "YesNo" "Warning") -ne "Yes") { return $false }
                }
            }
        }
    }
    return $true
}

function Get-Summary {
    $yes = { param($b) if ($b) { "是" } else { "否" } }
    $student = if ($S.SkipStudent -or -not $S.StudentId) { "（略過，第一次匯入考卷時可以輸入）" } else { "$($S.StudentId)　$($S.StudentName)" }
    $names = [ordered]@{ VSCode = "VS Code"; VSCodeExtras = "附加 VS Code 擴充"; JupyterLab = "JupyterLab"; Docs = "離線文件" }
    # 沒裝 VS Code 時，附加擴充和同步設定都不算
    $on = @{ VSCode = $S.VSCode; VSCodeExtras = $S.VSCodeExtras -and $S.VSCode; JupyterLab = $S.JupyterLab; Docs = $S.Docs }
    $comps = @($names.Keys | Where-Object { $on[$_] } | ForEach-Object { $names[$_] })
    $skipped = @($names.Keys | Where-Object { -not $on[$_] } | ForEach-Object { $names[$_] })
    @(
        "學號姓名：$student"
        "講義資料夾：$(if ($S.HandoutsDir) { $S.HandoutsDir } else { '（不放）' })"
        "作業資料夾：$(if ($S.HomeworkDir) { $S.HomeworkDir } else { '（不放）' })"
        "建立位置：$($S.Out)"
        "元件：$($comps -join '、')"
        if ($skipped) { "　（不裝：$($skipped -join '、')）" }
        "同步 VS Code 設定：$(& $yes ($S.SyncVSCode -and $S.VSCode))"
        "完成後刪除下載快取：$(& $yes $S.CleanDownloads)"
        "複製到隨身碟：$(if ($S.CopyUsb) { Join-Path $S.UsbDrive 'STAT_EXAM' } else { '否' })"
        ""
        "預估：下載約 1 GB、建立後約 $(Get-RequiredGB $S) GB、15–40 分鐘（依網路速度而定）"
    ) -join "`r`n"
}

# ------------------------------------------------------------------ 建立流程
$timer = New-Object Windows.Forms.Timer
$timer.Interval = 700
$clock = New-Object Diagnostics.Stopwatch
$script:LogState = @{ Pos = 0 }; $script:ErrState = @{ Pos = 0 }

function Add-LogText([string]$text) {
    if (-not $text) { return }
    $txtLog.AppendText(($text -replace "(?<!`r)`n", "`r`n"))
}

function Start-Build {
    $opts = [pscustomobject]@{
        Out = $S.Out; StudentId = $(if ($S.SkipStudent) { "" } else { $S.StudentId }); StudentName = $(if ($S.SkipStudent) { "" } else { $S.StudentName })
        HandoutsDir = $S.HandoutsDir; HomeworkDir = $S.HomeworkDir
        VSCode = $S.VSCode; VSCodeExtras = $S.VSCodeExtras; JupyterLab = $S.JupyterLab; Docs = $S.Docs
        SyncVSCode = $S.SyncVSCode; CleanDownloads = $S.CleanDownloads
    }
    $S.Status = "building"; $S.Log = ""; $S.Err = ""
    $script:LogState.Pos = 0; $script:ErrState.Pos = 0
    $S.Job = Start-BuildProcess $Repo (Get-BuildArguments $opts) $D.LogDir
    $null = $S.Job.Process.Handle                   # 先取得 handle，結束後才讀得到 ExitCode
    Add-LogText ("> " + $S.Job.Command + "`n`n")
    $clock.Restart(); $timer.Start()
}

function Start-Copy {
    $S.Status = "copying"
    $lblStep.Text = "複製到隨身碟 $($S.UsbDrive)"
    $total = Get-BuiltFileCount $S.Log
    if ($total -le 0) { $lblStatus.Text = "正在計算檔案數量…"; [Windows.Forms.Application]::DoEvents() }
    $S.Copy = Start-UsbCopy $S.Out $S.UsbDrive $D.LogDir $total
    $null = $S.Copy.Process.Handle
    Add-LogText "`n> robocopy → $($S.Copy.Destination)（$($S.Copy.Total) 個檔案）`n"
}

function Finish-Wizard([string]$status) {
    $timer.Stop(); $clock.Stop()
    $S.Status = $status
    $chk = $S.Check
    switch ($status) {
        "done" {
            if ($chk.Passed -eq $false) {
                $lblResult.Text = "⚠ 建立完成，但環境檢查有 $($chk.FailCount) 項沒通過"
                $lblResult.ForeColor = [Drawing.Color]::FromArgb(180, 110, 0)
                $lblDetail.Text = "沒通過的項目：`n" + (($chk.Failures | Select-Object -First 4) -join "`n") + "`n請按「開啟紀錄檔」查看詳細內容。"
            } else {
                $lblResult.Text = "✔ 建立完成！"
                $lblResult.ForeColor = [Drawing.Color]::FromArgb(0, 130, 60)
                $lblDetail.Text = "環境位置：$($S.Out)" + $(if ($S.Copy) { "`n已複製到隨身碟：$($S.Copy.Destination)" } else { "" }) +
                                  "`n環境檢查：$(if ($chk.Passed) { '全部通過' } else { '未執行' })　｜　花費時間：$([int]$clock.Elapsed.TotalMinutes) 分鐘"
            }
        }
        "failed" {
            $lblResult.Text = "✖ 建立失敗"
            $lblResult.ForeColor = [Drawing.Color]::FromArgb(200, 40, 40)
            if (($S.Log + $S.Err) -match 'VS Code 擴充沒有裝好|Server returned 503') {
                $lblDetail.Text = ("VS Code 的擴充沒有裝好：VS Code Marketplace 暫時無法連線（HTTP 503，是微軟伺服器暫時故障，不是你的電腦有問題）。`n" +
                    "其他部分都已經完成。請過幾分鐘再執行一次精靈、選同一個建立位置，只會補裝沒裝好的擴充。")
            } else {
                # PowerShell 的錯誤格式（+ ... ~~~、CategoryInfo…）看不懂，只留真正的訊息
                $tail = (($S.Err + "`n" + $S.Log) -split "`r?`n" |
                    Where-Object { $_.Trim() -and $_ -notmatch '^\s*(\+|~|位於|At )|CategoryInfo|FullyQualifiedErrorId' } |
                    Select-Object -Last 4) -join "`n"
                $lblDetail.Text = "最後的訊息：`n$tail`n常見原因：網路中斷、磁碟空間不足、防毒軟體攔截。可以直接再執行一次精靈，已下載的檔案會沿用。"
            }
        }
        "copyfailed" {
            $lblResult.Text = "⚠ 環境已建立，但複製到隨身碟失敗"
            $lblResult.ForeColor = [Drawing.Color]::FromArgb(180, 110, 0)
            $lblDetail.Text = "環境在：$($S.Out)`n可以重新插拔隨身碟後再執行一次精靈，或直接把 STAT_EXAM 資料夾手動複製到隨身碟。"
        }
        "cancelled" {
            $lblResult.Text = "已停止"
            $lblResult.ForeColor = $Muted
            $lblDetail.Text = "已下載的檔案會保留，下次執行精靈會接著做。"
        }
    }
    $btnOpenUsb.Visible = [bool]$S.Copy -and $status -eq "done"
    $btnOpenGuide.Enabled = Test-Path (Join-Path $S.Out "使用說明.txt")
    if ($ResultFile) {
        [pscustomobject]@{ Status = $status; ExitCode = $S.ExitCode; Passed = $chk.Passed; FailCount = $chk.FailCount
                           LogPath = $S.Job.LogPath; CopyDestination = $(if ($S.Copy) { $S.Copy.Destination }) } |
            ConvertTo-Json | Set-Content -LiteralPath $ResultFile -Encoding UTF8
    }
    Show-Page $iDone
    if ($AutoClose) { $form.Close() }
}

$timer.Add_Tick({ try { Update-Progress } catch { Add-LogText "`n[精靈錯誤] $($_.Exception.Message)`n" } })

function Update-Progress {
    $elapsed = $clock.Elapsed
    $lblTime.Text = "已經過 {0:00}:{1:00}" -f [int][math]::Floor($elapsed.TotalMinutes), $elapsed.Seconds
    if ($S.Status -eq "building") {
        $new = Read-NewText $S.Job.LogPath $script:LogState
        $err = Read-NewText $S.Job.ErrPath $script:ErrState
        if ($new) { $S.Log += $new; Add-LogText $new }
        if ($err) { $S.Err += $err; Add-LogText $err }
        $p = Get-BuildProgress $S.Log -MaxPercent $(if ($S.CopyUsb) { 85 } else { 100 })
        if ($p.Step -gt 0) { $lblStep.Text = "步驟 $($p.Step) / 7：$($p.Title)" }
        $bar.Value = [math]::Max($bar.Value, [math]::Min(100, $p.Percent))
        # 狀態列顯示最新的一行（uv / curl 的訊息在 stderr，所以兩邊都看）
        $lastLine = (($new + "`n" + $err) -split "`r?`n" | Where-Object { $_.Trim() -and $_ -notmatch '^===' } | Select-Object -Last 1)
        if ($lastLine) { $lblStatus.Text = $lastLine.Trim() }
        if ($S.Job.Process.HasExited) {
            Start-Sleep -Milliseconds 300
            $tailOut = Read-NewText $S.Job.LogPath $script:LogState; $S.Log += $tailOut; Add-LogText $tailOut
            $tailErr = Read-NewText $S.Job.ErrPath $script:ErrState; $S.Err += $tailErr; Add-LogText $tailErr
            $S.ExitCode = $S.Job.Process.ExitCode
            $S.Check = Get-CheckResult $S.Log
            if ($S.ExitCode -ne 0 -or -not (Get-BuildProgress $S.Log).Done) { Finish-Wizard "failed"; return }
            if ($S.CopyUsb) { Start-Copy } else { $bar.Value = 100; Finish-Wizard "done" }
        }
    } elseif ($S.Status -eq "copying") {
        $pct = Get-CopyProgress $S.Copy.LogPath $S.Copy.Total $S.Copy.State
        $bar.Value = [math]::Min(100, 85 + [math]::Round($pct * 15 / 100))
        $lblStatus.Text = "已複製約 $pct%（共 $($S.Copy.Total) 個檔案，隨身碟比較慢，請耐心等候）"
        if ($S.Copy.Process.HasExited) {
            if ($S.Copy.Process.ExitCode -lt 8) { $bar.Value = 100; Finish-Wizard "done" } else { Finish-Wizard "copyfailed" }
        }
    }
}

function Stop-Running {
    $proc = if ($S.Status -eq "building") { $S.Job.Process } elseif ($S.Status -eq "copying") { $S.Copy.Process } else { $null }
    if ($proc -and -not $proc.HasExited) { Stop-ProcessTree $proc.Id }
    Finish-Wizard "cancelled"
}

# ------------------------------------------------------------------ 按鈕
$btnNext.Add_Click({
    $i = $script:Page
    if ($i -eq $iDone) { $form.Close(); return }
    if (-not (Test-Page $i)) { return }
    if ($i -eq $iConfirm) { Show-Page $iProg; Start-Build; return }
    Show-Page ($i + 1)
})
$btnBack.Add_Click({ Save-Inputs; Show-Page ([math]::Max(0, $script:Page - 1)) })
$btnCancel.Add_Click({
    if ($script:Page -eq $iProg) {
        if ((Show-Message "確定要停止嗎？已下載的檔案會保留，下次執行精靈會接著做。" "YesNo" "Question") -eq "Yes") { Stop-Running }
    } else { $form.Close() }
})
$form.Add_FormClosing({
    param($sender, $e)
    if ($S.Status -in "building", "copying") {
        if ($AutoClose) { return }
        if ((Show-Message "環境還在建立中，確定要停止並關閉嗎？" "YesNo" "Warning") -eq "Yes") { Stop-Running } else { $e.Cancel = $true }
    }
})
$form.AcceptButton = $btnNext

# ------------------------------------------------------------------ 更新提示
function Show-UpdateLink($release) {
    if (-not $release -or -not (Test-NewerVersion $release.Tag $D.Version)) { return }
    $lnkUpdate.Text = "有新版 $($release.Tag)，按這裡下載（目前 v$($D.Version)）"
    $lnkUpdate.Tag = $(if ($release.Url) { $release.Url } else { $D.ReleasesPage })
    $lnkUpdate.Visible = $true
}
$updTimer = New-Object Windows.Forms.Timer
$updTimer.Interval = 500
$updTimer.Add_Tick({
    if ($script:UpdJob.State -in "Running", "NotStarted") { return }
    $updTimer.Stop()
    try { Show-UpdateLink (Receive-Job $script:UpdJob -ErrorAction SilentlyContinue | Select-Object -Last 1) } catch { }
    Remove-Job $script:UpdJob -Force -ErrorAction SilentlyContinue
})
function Start-UpdateCheck {
    # 在背景查 GitHub 最新的 release（不會卡住畫面）；沒網路就什麼都不顯示
    if (-not $D.ReleasesApi) { return }
    $script:UpdJob = Start-Job -ArgumentList (Join-Path $Here "wizard_core.ps1"), $D.ReleasesApi -ScriptBlock {
        param($core, $api)
        . $core
        Get-LatestRelease $api
    }
    $updTimer.Start()
}

# ------------------------------------------------------------------ 開始
$form.ResumeLayout($false)
$form.Add_Shown({
    if ($S.LatestTag) {
        # 測試用：-TestOptions 給 LatestTag 就不連網，直接當作 GitHub 上最新的是這一版
        Show-UpdateLink ([pscustomobject]@{ Tag = $S.LatestTag; Url = $D.ReleasesPage })
    } elseif (-not $ScreenshotDir) {
        Start-UpdateCheck
    }
    if ($ScreenshotDir) {
        New-Item -ItemType Directory -Force $ScreenshotDir | Out-Null
        $lblStep.Text = "步驟 2 / 7：安裝套件"; $bar.Value = 18; $lblStatus.Text = "Collecting numpy..."; $lblTime.Text = "已經過 03:12"
        $S.Check = [pscustomobject]@{ Passed = $true; FailCount = 0; Failures = @() }
        $txtSummary.Text = Get-Summary
        for ($k = 0; $k -lt $pages.Count; $k++) {
            if ($k -eq $iDone) { $lblResult.Text = "✔ 建立完成！"; $lblResult.ForeColor = [Drawing.Color]::FromArgb(0, 130, 60); $lblDetail.Text = "環境位置：$($S.Out)`n環境檢查：全部通過　｜　花費時間：18 分鐘" }
            Show-Page $k
            [Windows.Forms.Application]::DoEvents()
            $bmp = New-Object Drawing.Bitmap($form.Width, $form.Height)
            $form.DrawToBitmap($bmp, (New-Object Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
            $bmp.Save((Join-Path $ScreenshotDir ("page{0}.png" -f ($k + 1))), [Drawing.Imaging.ImageFormat]::Png)
            $bmp.Dispose()
        }
        $form.Close(); return
    }
    if ($AutoStart) { Save-Inputs; Show-Page $iProg; Start-Build }
})
Show-Page 0
[void]$form.ShowDialog()
