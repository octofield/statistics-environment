# 統計學考試環境

一鍵建立可以帶進考場、**完全離線**使用的 Python 統計考試環境：WinPython + 可攜式 VS Code（已移除 Copilot、關閉所有 AI 功能）+ JupyterLab，附上統計工具、各章筆記、公式總表、考卷範本與常見問題。寫完直接匯出 HTML 繳交。

為開書上機考設計的（考試全程斷網、禁用 AI、只能用隨身碟裡的環境），其他使用 Python / Jupyter 的統計課程也可以直接用或改來用。

> ⚠ **這不是學校或任何課程的官方工具。** 各課程的考試規定不同（是否允許 VS Code、是否一定要用 Jupyter、能帶哪些檔案），使用前請自行確認。本工具已關閉 AI 功能，但是否符合規定由使用者自行負責。

> ⚠ 要確認是否能使用 VS Code 以及自己寫的套件，如果最後不能用，我會再進行修改。如果有任何問題歡迎開 issue 或直接跟我說。

## 功能

- **一個精靈搞定**：圖形介面一步一步設定學號姓名、講義與作業、選項，自動下載安裝，完成後可以直接複製到隨身碟
- **完全離線、換電腦也能用**：全部用相對路徑，換磁碟代號、換電腦都不用重新設定；不會讀到考場電腦上的套件
- **編輯器**：可攜式 VS Code（繁體中文介面、Python / Jupyter / Pylance、PDF 與 Excel 檢視），JupyterLab 當備案
- **statkit 工具**：機率字串（`sk.prob(sk.Poisson(6.6), 'X >= 10')`，自動處理離散分布的 ≥ 要減 1）、互動式分布計算機 `sk.explore()`（會產生課程寫法的 scipy 程式碼）、敘述統計、統計圖、報童模型、模擬、資料速覽 `sk.peek()`
- **文件**：讀入資料與整理、公式總表、Markdown 與 LaTeX 語法、各章筆記、常見問題；snippets 都有參數說明
- **考試流程**：新增考卷（自動用學號姓名命名）、匯出 HTML（檢查檔名、執行順序、錯誤，並自動備份）、環境檢查

## 快速開始

### 方法 A：下載 Setup.exe（最簡單）

1. 到 [Releases](../../releases) 下載最新的 `STAT_EXAM_Setup_vX.Y.Z.exe`
2. 執行。如果出現「Windows 已保護您的電腦」，按「**其他資訊**」→「**仍要執行**」（這個安裝檔沒有付費的數位簽章，所以 Windows 會提醒）
3. 安裝完會自動開啟初始化精靈，照著畫面做就好

安裝檔只有 2 MB，不需要系統管理員權限，只是把精靈放到 `%LOCALAPPDATA%\STAT_EXAM_Setup`；之後可以從開始功能表的「統計學考試環境 初始化精靈」再次開啟。

### 方法 B：下載 zip

1. 本頁上方「**Code** → **Download ZIP**」，解壓縮
2. 雙擊 **`setup.cmd`**

### 方法 C：git clone（進階 / 開發）

```powershell
git clone <這個 repo 的網址>
cd statistics-environment
.\setup.cmd                                        # 圖形介面精靈
# 或直接用參數打包：
powershell -ExecutionPolicy Bypass -File build.ps1 -Out D:\STAT_EXAM -StudentId B12345678 -StudentName 王小明 -HandoutsDir D:\講義
```

| `build.ps1` 參數 | 說明 |
|---|---|
| `-Out` | 建立位置（預設 `build\STAT_EXAM`） |
| `-StudentId` / `-StudentName` | 學號姓名（不給的話，第一次「新增考卷」時會請你輸入） |
| `-HandoutsDir` / `-HomeworkDir` | 講義、作業資料夾（預設是 repo 的 `handouts/`、`homework/`，沒有就略過） |
| `-SkipDocs` | 不下載離線文件（少 0.65 GB、2 萬個檔案，複製到隨身碟快很多） |
| `-NoLocalSettings` | 不同步這台電腦的 VS Code 設定 |
| `-CleanDownloads` | 完成後刪除下載快取（約 1 GB） |
| `-SkipVSCode` / `-SkipCheck` / `-StrictCheck` | 不裝 VS Code／不跑環境檢查／環境檢查失敗時回傳錯誤（CI 用） |

## 精靈會做什麼

1. **歡迎**：說明與考試規定提醒
2. **學號姓名**：用在考卷檔名和抬頭（可以先略過）
3. **講義與作業**（選填）：選你自己的資料夾，只會複製到你的電腦和隨身碟；講義 PDF 會轉成文字，方便在 VS Code 搜尋
4. **選項**：建立位置、離線文件（多約 2 萬個檔案，要複製到隨身碟的話會久很多）、同步 VS Code 設定（AI 相關設定一律排除）、刪除下載快取、複製到隨身碟
5. **確認** → 6. **建立**（顯示進度，可以停止，下次會接著做）→ 7. **完成**（環境檢查結果、使用說明、紀錄檔）

### 系統需求

- Windows 10（1803 以後）或 Windows 11，64 位元
- 建立時需要網路：下載約 1 GB，所有軟體都從官方網站下載
- 硬碟空間約 3–4 GB；隨身碟建議 8 GB 以上（建立後約 2–2.7 GB、5–7 萬個檔案，USB 3.0 比較快）
- 15–40 分鐘（依網路速度）；不需要系統管理員權限，也不會改系統設定

## 建立好的環境

```
STAT_EXAM/
├─ 1_啟動VSCode.bat      主力編輯器（會自動打開索引）
├─ 2_啟動JupyterLab.bat  備案
├─ 3_匯出HTML.bat        匯出並檢查、備份
├─ 4_環境檢查.bat        考前跑一次（建議斷網跑）
├─ 5_新增考卷.bat        確認學號姓名 → 建立 學號_姓名_考試名稱.ipynb
├─ 使用說明.txt
├─ WPy64-313150/         WinPython（Python 與所有套件）
├─ VSCode/               可攜式 VS Code（設定、擴充都在 VSCode\data\）
└─ workspace/            00_索引.ipynb、常見問題.md、exam/、data/、notes/、handouts/、homework/、statkit/、tools/
```

考試當天：插隨身碟 → `1_啟動VSCode.bat` → `5_新增考卷.bat` → 作答 → Ctrl+Shift+P「執行工作」→「匯出目前的 notebook 成 HTML」→ 上傳。詳細流程寫在 `使用說明.txt` 和 `00_索引.ipynb`。

**考前一定要演練**：拔掉網路，從隨身碟跑一次 `4_環境檢查.bat`，用 VS Code 和 JupyterLab 各寫一題、匯出 HTML；可以的話換一台電腦再試一次。

## 安裝時的常見問題

| 狀況 | 解法 |
|---|---|
| 「Windows 已保護您的電腦」 | 按「其他資訊」→「仍要執行」。安裝檔沒有付費的數位簽章；原始碼都在這個 repo 裡 |
| 防毒軟體攔截 | 少數防毒會誤判下載程式的 PowerShell 腳本。可以暫時允許，或改用方法 B 自己看過腳本再執行 |
| 下載到一半失敗 / 停止 | 直接再執行一次精靈，已下載的檔案會沿用 |
| 精靈說建立失敗 | 按「開啟紀錄檔」看最後幾行；常見原因是網路中斷、磁碟空間不足 |
| 覺得太慢 | 紀錄檔最後有「各步驟耗時」，回報時附上；複製到隨身碟最花時間的是檔案數量，不需要離線文件就取消勾選 |
| 學校 / 公司網路有 proxy | 換到一般網路（例如手機熱點）再執行 |
| 想更新環境 | 選同一個建立位置再跑一次精靈；`exam\` 裡的考卷不會被刪 |

精靈的紀錄檔在 `%LOCALAPPDATA%\STAT_EXAM_Setup\logs\`（不含你的講義、作業內容），回報問題時可以附上。

## 隱私與著作權

- 這個 repo **只有程式碼與自己寫的筆記**。講義、作業屬於授課老師或你自己，**不包含**在 repo 裡，也請不要上傳到公開的地方
- `config/student.json`（你的學號姓名）、`handouts/`、`homework/` 都在 `.gitignore` 裡
- 精靈不會上傳任何東西；它只會從官方網站下載 WinPython、VS Code、uv、Python 套件、字型與文件

## 開發

| 路徑 | 內容 |
|---|---|
| `setup.cmd`、`setup/` | 精靈入口、圖形介面（`Setup-Wizard.ps1`）、邏輯（`wizard_core.ps1`）、Inno Setup 安裝檔設定（`installer.iss`） |
| `build.ps1` | 實際打包的腳本（精靈在背景執行它） |
| `statkit/` | 工具函式庫；`python -m statkit.selftest` 跟講義、作業答案比對 |
| `notes/`、`templates/` | 筆記、考卷範本（`{學號}` `{姓名}` `{考試名稱}` 佔位）、索引、常見問題、使用說明 |
| `config/` | VS Code 設定（關 AI、離線）、tasks、snippets、擴充清單、JupyterLab 設定、`student.example.json` |
| `launchers/`、`tools/` | 隨身碟根目錄的 .bat、環境設定與工具（匯出、新增考卷、語言包、設定同步、環境檢查） |
| `.github/workflows/` | CI 與發布 |

**檢查**（CI 每次 push / PR 都會跑）：

```powershell
python -m statkit.selftest            # statkit 自我測試
python tools/validate_repo.py         # 設定檔、snippets、PowerShell 語法與 BOM、bat 純 ASCII + CRLF、執行所有 notebook
npm install --no-save --prefix tools/ci katex@0.16.11
python tools/ci/extract_math.py > math.json; node tools/ci/check_math.js math.json   # 用 KaTeX 檢查所有公式
```

**修改時要注意**：
- `.ps1` 要存成 **UTF-8 with BOM**（Windows PowerShell 5.1 才讀得懂中文）
- `.bat` / `.cmd` 只能用 **ASCII**（cmd 會把中文切錯位）
- 換行由 `.gitattributes` 處理

**發布**：打 tag 就會自動編譯 Setup.exe 並建立 Release。

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## 第三方軟體與授權

精靈在**使用者的電腦上**從官方來源下載以下軟體，本 repo 不轉散布：

- [WinPython](https://winpython.github.io/)（MIT）與 Python 套件（用 [uv](https://github.com/astral-sh/uv)（MIT / Apache-2.0）安裝，只在建立時使用，不會放進隨身碟）（各自的授權，見建立後的 `workspace\tools\requirements-lock.txt`）
- [Visual Studio Code](https://code.visualstudio.com/)（[Microsoft 軟體授權](https://code.visualstudio.com/license)）與擴充功能
- [Noto Sans TC](https://fonts.google.com/noto/specimen/Noto+Sans+TC)（SIL Open Font License）
- pandas、NumPy、SciPy、Python 官方文件（各自的授權）

本專案的程式碼以 [MIT License](LICENSE) 授權。
