; 統計學考試環境 初始化精靈的安裝檔（Inno Setup）。
; 只負責把程式解壓到 %LOCALAPPDATA%\STAT_EXAM_Setup 並開啟精靈；實際的環境由精靈在使用者電腦上下載建立。
;
;   ISCC.exe /DAppVersion=v1.0.0 setup\installer.iss      → dist\STAT_EXAM_Setup_v1.0.0.exe

#ifndef AppVersion
  #define AppVersion "dev"
#endif
#define AppName "統計學考試環境"
; 引號要寫四個：ISPP 字串吃掉一層、Inno 的 Parameters 再吃掉一層，最後剩下 "{app}\...ps1"
#define WizardCmd "-NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File """"{app}\setup\Setup-Wizard.ps1"""""

; 新版 Inno Setup 內建繁體中文；舊版用 setup\ChineseTraditional.isl（CI 會下載）
#if FileExists(AddBackslash(CompilerPath) + "Languages\ChineseTraditional.isl")
  #define ChtMessages "compiler:Languages\ChineseTraditional.isl"
#else
  #define ChtMessages "ChineseTraditional.isl"
#endif

[Setup]
AppId={{13A644C3-E1D9-4858-9870-86249DEDFF56}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=octofield
DefaultDirName={localappdata}\STAT_EXAM_Setup
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=STAT_EXAM_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayName={#AppName} 初始化精靈
ShowLanguageDialog=no

[Languages]
Name: "cht"; MessagesFile: "{#ChtMessages}"

[Messages]
cht.WelcomeLabel2=這會安裝「{#AppName} 初始化精靈」到你的電腦。%n%n安裝完會自動開啟精靈，一步一步建立可以帶進考場、完全離線使用的考試環境（Python、VS Code、筆記與工具）。%n%n不需要系統管理員權限。

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; \
  Excludes: "\.git,\.github,\build,\dist,\handouts,\homework,\config\student.json,\setup\ChineseTraditional.isl,\tools\ci\node_modules,\tools\ci\package*.json,__pycache__,*.pyc,.ipynb_checkpoints"

[Icons]
Name: "{group}\{#AppName} 初始化精靈"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "{#WizardCmd}"; WorkingDir: "{app}"
Name: "{group}\解除安裝 {#AppName} 初始化精靈"; Filename: "{uninstallexe}"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "{#WizardCmd}"; WorkingDir: "{app}"; \
  Description: "立即開啟初始化精靈"; Flags: postinstall nowait skipifsilent runhidden

[UninstallDelete]
; 只刪精靈本身與下載快取；精靈建立的 STAT_EXAM 環境（例如桌面上的）不會被刪
Type: filesandordirs; Name: "{app}\build"
