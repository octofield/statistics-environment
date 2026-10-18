# statistics-environment

統計學（115-1）考試用的**隨身碟離線環境**產生器。考試全程斷網、禁用 AI，只能用隨身碟裡的環境，最後交 HTML。

- **主力**：可攜式 VS Code（Python / Jupyter / Pylance / PDF 檢視，所有 AI 功能關閉）
- **備案**：WinPython 的 JupyterLab（規範指定）
- **statkit**：依講義寫的小工具，會產生「課程寫法」的 scipy 程式碼；`sk.explore()` 是互動式分布計算機
- **文件區**：講義（PDF 可全文搜尋）、作業、各章筆記、pandas / numpy / scipy / Python 離線文件

## 打包（需要網路，一次即可）

第一次打包前，先把 `config/student.example.json` 複製成 `config/student.json`，填上自己的學號、姓名（「新增考卷」會用它命名檔案、填考卷抬頭）。`student.json` 已加入 `.gitignore`，不會被 commit。
忘了設定也沒關係：每次「新增考卷」都會先顯示學號姓名請你確認，還是範例資料時會要求輸入，改過的資料會存在隨身碟的 `workspace\tools\student.json`。

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1            # 全部
powershell -ExecutionPolicy Bypass -File build.ps1 -SkipDocs  # 不下載離線文件（快很多、檔案少）
```

產生 `build\STAT_EXAM\`（約 2 GB），整個資料夾複製到隨身碟即可。可以重複執行：已下載的檔案會沿用。

| 參數 | 說明 |
|---|---|
| `-WinPyUrl` | WinPython 下載網址（預設 3.13.15 dot 版；dot 版只有 Python，套件由 `requirements.txt` 安裝） |
| `-SkipVSCode` | 只要 JupyterLab |
| `-SkipDocs` | 不下載離線文件 |
| `-SkipCheck` | 不跑最後的環境檢查 |
| `-NoLocalSettings` | 不同步這台電腦的 VS Code 設定，只用考試設定 |

### VS Code 設定同步

打包時 `tools/sync_vscode_settings.py` 會把這台電腦的 VS Code 設定帶到隨身碟：
`settings.json`、`keybindings.json`、snippets、介面語言（`argv.json` 的 locale）。

- **排除**：AI 相關（Copilot / Claude / Gemini / Tabnine / chat…）、跟考試無關或綁本機的（Java、C++、Dart、CMake、含 `C:\Users\` 路徑的設定）
- **考試設定優先**：`config/vscode-user-settings.json`（關 AI、不檢查更新、關遙測、自動存檔⋯）會覆蓋本機同名設定
- 本機改了設定後重跑 `build.ps1` 就會重新同步；要帶的擴充寫在 `config/extensions.txt`

## 隨身碟結構

```
STAT_EXAM/
├─ 1_啟動VSCode.bat  2_啟動JupyterLab.bat  3_匯出HTML.bat  4_環境檢查.bat  5_新增考卷.bat  使用說明.txt
├─ WPy64-313150/      WinPython + 套件（statkit 透過 .pth 加進 sys.path）
├─ VSCode/            可攜式 VS Code（data/ 內是設定、snippets、擴充）
└─ workspace/         00_索引.ipynb、exam/、data/、notes/、handouts/、homework/、docs-offline/、statkit/、tools/
```

## Repo 內容

| 路徑 | 內容 |
|---|---|
| `statkit/` | 工具函式庫：`desc`（敘述統計）、`plots`（圖）、`dist`（分布、機率字串解析、程式碼產生、互動 UI、報童模型）、`sim`（模擬） |
| `statkit/selftest.py` | 跟作業 / 講義答案比對的自我測試：`python -m statkit.selftest` |
| `notes/` | 讀入資料與整理、公式總表、Markdown 與 LaTeX 語法、各章筆記 notebook |
| `templates/` | 考卷範本（`{學號}` `{姓名}` `{考試名稱}` 佔位）、索引、常見問題、說明檔 |
| `config/` | VS Code 設定（關 AI、離線）、tasks、snippets、擴充清單、JupyterLab 設定、`student.example.json`（學號姓名範本） |
| `launchers/` | 根目錄的 .bat |
| `tools/` | `env.bat`（相對路徑環境設定）、`check_env.py`、`export_html.py`（匯出＋備份）、`new_exam.py`、`vscode_locale.py`（語言包快取）、`sync_vscode_settings.py`、`extract_pdf_text.py` |
| `handouts/` | 講義 PDF 與課程程式（不進版控） |
| `homework/` | 作業 ipynb / html / 資料（不進版控） |

講義和作業的打包方式一樣：放進 `handouts/`、`homework/`（子資料夾也可以），打包時整個資料夾分別複製到 `workspace\handouts\`、`workspace\homework\`。

講義、作業與資料檔（`.pdf`、`.xlsx`、`.csv`、`*_HW*`）**不進版控**（見 `.gitignore`）。
在新的電腦 clone 之後，要先把講義放進 `handouts/`、作業放進 `homework/`，才能打包；缺哪個資料夾打包時會跳出警告。

## 考前演練

1. 關掉網路，從隨身碟執行 `4_環境檢查.bat`，全部 OK
2. 分別用 VS Code 和 JupyterLab 寫一題 → `3_匯出HTML.bat` → 用瀏覽器打開檢查
3. 換一台電腦（磁碟代號不同）再試一次
