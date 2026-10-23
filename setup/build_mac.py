"""在 Mac 上建立給 Windows 考場用的 STAT_EXAM（跟 build.ps1 產生一樣的資料夾結構）。

一般使用者請雙擊 repo 根目錄的 setup_mac.command；它會先準備好 uv 與 Python 3.13，再執行：

    uv run --no-project --python 3.13 --with pypdf setup/build_mac.py --out ~/Desktop/STAT_EXAM [選項]

Mac 上沒辦法執行 Windows 程式，所以跟 build.ps1 有三個地方不一樣：
- 套件：用 uv 跨平台安裝 Windows 版的 wheel（--python-platform x86_64-pc-windows-msvc）；
  python\\Scripts 的 jupyter.exe 等執行檔由 tools/finish_setup.py 第一次在 Windows 上產生
- VS Code 擴充：只下載 Windows 版 .vsix 到 VSCode/data/pending-vsix/，第一次在 Windows 上執行
  1_啟動VSCode.bat 或 4_環境檢查.bat 時由 tools/finish_setup.py 離線安裝
- 環境檢查：要到 Windows 上執行 4_環境檢查.bat
也可以在 Windows / Linux 上執行（測試用）。
"""
import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DL = REPO / "build" / "downloads"
SOURCES = json.loads((REPO / "config" / "sources.json").read_text(encoding="utf-8"))
WIN_PLATFORM = "x86_64-pc-windows-msvc"
VSIX_PLATFORM = "win32-x64"
GALLERY = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
# 跟 build.ps1 一樣：這些套件附的 tests 資料夾考試用不到
TEST_PACKAGES = ("numpy", "pandas", "scipy", "statsmodels", "sympy", "matplotlib", "mpl_toolkits", "seaborn", "IPython")
# Windows 上測試時要用系統的 curl.exe / tar.exe（Git Bash 的 GNU tar 解不開 zip）
SYS32 = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
TAR = str(SYS32 / "tar.exe") if os.name == "nt" else "tar"
CURL = [str(SYS32 / "curl.exe") if os.name == "nt" else "curl", "-L", "--fail", "-sS", "--retry", "3", "--retry-delay", "2"]

step_times = {}
_current = {"title": None, "start": 0.0}
prefetch = {}           # 檔名 → 背景下載的 curl Popen


def step(title=None):
    if _current["title"]:
        step_times[_current["title"]] = time.monotonic() - _current["start"]
    _current.update(title=title, start=time.monotonic())
    if title:
        print(f"\n=== {title} ===", flush=True)


def run(*cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, **kw)


# ------------------------------------------------------------------ 下載
def start_prefetch(url, name):
    path = DL / name
    if url and not path.exists() and name not in prefetch:
        prefetch[name] = subprocess.Popen([*CURL, "-C", "-", "-o", str(path) + ".part", url])


def get_file(url, name):
    path = DL / name
    part = Path(str(path) + ".part")
    if path.exists():
        return path
    p = prefetch.pop(name, None)
    if p:
        if p.poll() is None:
            print(f"等待背景下載 {name} ...", flush=True)
        if p.wait() == 0:
            part.replace(path)
            return path
    print(f"下載 {name} ...", flush=True)
    run(*CURL, "-C", "-", "-o", part, url)
    part.replace(path)
    return path


def expand(archive, dst):
    dst.mkdir(parents=True, exist_ok=True)
    run(TAR, "-xf", archive, "-C", dst)


def merge_move(src, dst):
    """把 src 資料夾的內容搬進 dst（合併、覆蓋同名檔），再刪掉 src。"""
    for p in sorted(src.rglob("*")):
        if p.is_file():
            target = dst / p.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(p, target)
    shutil.rmtree(src)


def copy_tree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".ipynb_checkpoints"))


# ------------------------------------------------------------------ VS Code 擴充
def version_key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def gallery_versions(ext_id):
    body = {"filters": [{"criteria": [{"filterType": 7, "value": ext_id}], "pageNumber": 1, "pageSize": 1}],
            "flags": 0x1 | 0x2 | 0x10 | 0x80}     # versions、files、version properties、asset URI
    r = subprocess.run([*CURL, "-X", "POST", "-H", "Content-Type: application/json",
                        "-H", "Accept: application/json;api-version=3.0-preview.1",
                        "--data-binary", "@-", GALLERY],
                       input=json.dumps(body).encode(), capture_output=True, check=True)
    exts = json.loads(r.stdout)["results"][0]["extensions"]
    if not exts:
        raise RuntimeError(f"Marketplace 找不到擴充 {ext_id}")
    return exts[0]["versions"]


def pick_version(versions, vscode_version):
    """跟 VS Code 一樣挑：Windows x64 或通用版、不是 pre-release、支援這個 VS Code 版本的最新版。"""
    for v in versions:                      # Marketplace 回傳的順序是新到舊
        if v.get("targetPlatform") not in (None, VSIX_PLATFORM):
            continue
        props = {p["key"]: p["value"] for p in v.get("properties", [])}
        if props.get("Microsoft.VisualStudio.Code.PreRelease") == "true":
            continue
        engine = props.get("Microsoft.VisualStudio.Code.Engine", "")
        if vscode_version and engine.lstrip("^>=~ ") and version_key(engine) > version_key(vscode_version):
            continue
        return v
    return None


def vsix_url(v):
    for f in v.get("files", []):
        if f.get("assetType") == "Microsoft.VisualStudio.Services.VSIXPackage":
            return f["source"]
    return v["assetUri"] + "/Microsoft.VisualStudio.Services.VSIXPackage"


def vsix_manifest(path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("extension/package.json").decode("utf-8-sig"))


def download_extensions(vs_dir, wanted):
    """下載 Windows 版 .vsix（包含相依與 extension pack 裡的擴充），依「相依的先裝」寫出 order.txt。"""
    pending = vs_dir / "data" / "pending-vsix"
    pending.mkdir(parents=True, exist_ok=True)
    installed_json = vs_dir / "data" / "extensions" / "extensions.json"
    installed = set()
    if installed_json.is_file():
        installed = {e["identifier"]["id"].lower() for e in json.loads(installed_json.read_text(encoding="utf-8"))}
    pkg = next(iter(sorted(vs_dir.glob("**/resources/app/package.json"))), None)
    vscode_version = json.loads(pkg.read_text(encoding="utf-8"))["version"] if pkg else ""

    order, seen = [], set()

    def visit(ext_id):
        key = ext_id.lower()
        if key in seen or key in installed:
            return
        seen.add(key)
        existing = sorted(pending.glob(f"{key}__*.vsix"))
        if existing:
            path = existing[-1]
        else:
            v = pick_version(gallery_versions(ext_id), vscode_version)
            if v is None:
                raise RuntimeError(f"找不到支援 Windows 與 VS Code {vscode_version} 的 {ext_id}")
            path = pending / f"{key}__{v['version']}.vsix"
            print(f"下載擴充 {ext_id} {v['version']}", flush=True)
            run(*CURL, "--compressed", "-o", str(path) + ".part", vsix_url(v))
            Path(str(path) + ".part").replace(path)
            if not zipfile.is_zipfile(path):
                path.unlink()
                raise RuntimeError(f"{ext_id} 的 .vsix 下載不完整")
        manifest = vsix_manifest(path)
        for dep in [*manifest.get("extensionDependencies", []), *manifest.get("extensionPack", [])]:
            visit(dep)
        order.append(path.name)

    for ext_id in wanted:
        visit(ext_id)
    if order:
        (pending / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
        print(f"已下載 {len(order)} 個擴充；第一次在 Windows 上執行 1_啟動VSCode 或 4_環境檢查 時會自動安裝（不需要網路）")
    else:
        shutil.rmtree(pending, ignore_errors=True)


# ------------------------------------------------------------------ 隨身碟
def copy_to_usb(src, volume):
    if sys.platform != "darwin":
        sys.exit("--usb 只能在 Mac 上使用")
    volume = Path(volume)
    info = plistlib.loads(subprocess.run(["diskutil", "info", "-plist", str(volume)], capture_output=True, check=True).stdout)
    fs = str(info.get("FilesystemType", "")).lower()
    if fs not in ("exfat", "msdos"):
        sys.exit(f"\n{volume} 的格式是 {info.get('FilesystemUserVisibleName', fs)}，Windows 讀不到。\n"
                 "請用「磁碟工具程式」把隨身碟清除成「ExFAT」格式（會刪除隨身碟上所有資料），再執行一次。")
    need = sum(p.stat().st_size for p in src.rglob("*") if p.is_file())
    if shutil.disk_usage(volume).free < need:
        sys.exit(f"\n隨身碟空間不足：需要約 {need / 1e9:.1f} GB")
    dst = volume / src.name
    print(f"\n複製到 {dst}（隨身碟寫小檔案比較慢，請耐心等候）...", flush=True)
    # 不加 --delete：隨身碟上 exam\ 裡的考卷不會被刪；COPYFILE_DISABLE 避免產生 ._ 開頭的 macOS 附屬檔
    run("rsync", "-rt", "--exclude", "._*", "--exclude", ".DS_Store", f"{src}/", f"{dst}/",
        env={**os.environ, "COPYFILE_DISABLE": "1"})
    subprocess.run(["dot_clean", "-m", str(dst)])
    print(f"已複製到隨身碟：{dst}")


# ------------------------------------------------------------------ 主流程
def main():
    ap = argparse.ArgumentParser(description="在 Mac 上建立給 Windows 考場用的 STAT_EXAM")
    ap.add_argument("--out", type=Path, default=Path.home() / "Desktop" / "STAT_EXAM")
    ap.add_argument("--student-id", default="")
    ap.add_argument("--student-name", default="")
    ap.add_argument("--handouts", type=Path, default=REPO / "handouts", help="講義資料夾（沒有就略過）")
    ap.add_argument("--homework", type=Path, default=REPO / "homework", help="作業資料夾（沒有就略過）")
    # 元件（跟 build.ps1 一樣）：取消勾選不會移除之前已經建立好的部分
    ap.add_argument("--skip-vscode", action="store_true", help="不裝可攜式 VS Code（只用 JupyterLab）")
    ap.add_argument("--skip-extra-extensions", action="store_true", help="不裝附加的 VS Code 擴充（config/extensions-extra.txt）")
    ap.add_argument("--skip-jupyterlab", action="store_true", help="不裝 JupyterLab，也不放 2_啟動JupyterLab.bat")
    ap.add_argument("--skip-docs", action="store_true")
    ap.add_argument("--clean-downloads", action="store_true", help="完成後刪除下載快取（build/downloads，約 1 GB）")
    ap.add_argument("--usb", help="完成後複製到這個隨身碟（例如 /Volumes/USB）")
    args = ap.parse_args()

    out = args.out.expanduser().resolve()
    ws = out / "workspace"
    DL.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        sys.exit("找不到 uv，請用 setup_mac.command 執行")

    # ------------------------------------------------------------ 1. WinPython
    step("1. WinPython")
    if not args.skip_vscode and not (out / "VSCode" / "Code.exe").exists():
        start_prefetch(SOURCES["vscode_win"], "vscode-win32-x64.zip")
    start_prefetch(SOURCES["font"], "NotoSansTC-VF.ttf")
    winpy_url = SOURCES["winpython"]
    zip_path = get_file(winpy_url, winpy_url.rsplit("/", 1)[-1])
    if not list(out.glob("WPy64-*")):
        expand(zip_path, out)
    winpy = sorted(p for p in out.glob("WPy64-*") if p.is_dir())[0]
    pydir = winpy / "python"
    site = pydir / "Lib" / "site-packages"
    print(f"WinPython：{winpy}")
    # WinPython 的 Python 版本（python313.dll → 3.13）要跟執行這支程式的 Python 一樣，.pyc 才能共用
    dll = next(m for m in (re.fullmatch(r"python3(\d+)\.dll", p.name, re.I) for p in pydir.iterdir()) if m)
    minor = int(dll.group(1))
    if sys.version_info[:2] != (3, minor):
        sys.exit(f"WinPython 是 Python 3.{minor}，請用 Python 3.{minor} 執行（uv run --python 3.{minor} ...）")

    docs = {}
    if not args.skip_docs:
        scipy_zip = None
        try:
            html = subprocess.run([*CURL, SOURCES["docs_scipy_index"]], capture_output=True, check=True).stdout.decode("utf-8", "replace")
            m = re.search(r'href="(scipy/scipy-html-[\d.]+\.zip)"', html)
            scipy_zip = SOURCES["docs_scipy_index"] + m.group(1) if m else None
        except Exception:
            pass
        docs = {"pandas": SOURCES["docs_pandas"], "numpy": SOURCES["docs_numpy"], "scipy": scipy_zip,
                "python": SOURCES["docs_python"].replace("{minor}", f"3.{minor}")}
        for name, url in docs.items():
            if not (ws / "docs-offline" / name).exists():
                start_prefetch(url, f"docs-{name}.zip")

    # ------------------------------------------------------------ 2. 套件
    step("2. 安裝套件")
    # 在 Mac 上直接裝 Windows 版的 wheel；--compile-bytecode 用這個 Python 3.x 編譯，Windows 上可以直接用
    # --link-mode copy：預設會從 uv 的快取 clone / hardlink，建立位置在別的磁碟（例如隨身碟）時會失敗
    reqs = ["-r", REPO / "requirements.txt"]
    if not args.skip_jupyterlab:
        reqs += ["-r", REPO / "requirements-jupyterlab.txt"]
    run(uv, "pip", "install", "--target", site, "--python-platform", WIN_PLATFORM, "--python-version", f"3.{minor}",
        "--python", sys.executable, "--only-binary", ":all:", "--link-mode", "copy", "--compile-bytecode", *reqs)
    # --target 會把 wheel 的資料檔（JupyterLab 的網頁、kernel 設定、etc/jupyter…）放在 site-packages 底下，
    # 要搬到 sys.prefix（python\）底下 Jupyter 才找得到；bin\ 是 Mac 格式的執行檔，在 Windows 上沒用
    for name in ("share", "etc"):
        if (site / name).is_dir():
            merge_move(site / name, pydir / name)
    for name in ("bin", "Scripts"):
        shutil.rmtree(site / name, ignore_errors=True)
    (site / "statkit_workspace.pth").write_text(
        "import os, sys; sys.path.append(os.path.normpath(os.path.join(os.path.dirname(sys.executable), '..', '..', 'workspace')))\n",
        encoding="ascii")
    lab_settings = pydir / "share" / "jupyter" / "lab" / "settings"
    lab_settings.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "config" / "jupyterlab-overrides.json", lab_settings / "overrides.json")
    for pkg in TEST_PACKAGES:
        if (site / pkg).is_dir():
            for d in sorted((site / pkg).rglob("tests"), key=lambda p: len(p.parts)):
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
    print("預先編譯 .pyc（加快隨身碟上的啟動速度）...", flush=True)
    subprocess.run([sys.executable, "-m", "compileall", "-q", "-j", "0", "-x", "site-packages", str(pydir / "Lib")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ------------------------------------------------------------ 3. VS Code
    if not args.skip_vscode:
        step("3. 可攜式 VS Code")
        vs_dir = out / "VSCode"
        if not (vs_dir / "Code.exe").exists():
            expand(get_file(SOURCES["vscode_win"], "vscode-win32-x64.zip"), vs_dir)
        # 新版 VS Code 內建 Copilot 擴充：考試禁用 AI，直接從可攜版移除
        for ext_root in [*vs_dir.glob("resources/app/extensions"), *vs_dir.glob("*/resources/app/extensions")]:
            for d in ext_root.iterdir():
                if d.is_dir() and "copilot" in d.name.lower():
                    print(f"移除內建 AI 擴充：{d.name}")
                    shutil.rmtree(d)
        for d in ("data/user-data/User", "data/tmp"):           # data\ 存在 = portable mode
            (vs_dir / d).mkdir(parents=True, exist_ok=True)
        # Mac 的設定與快捷鍵（cmd 鍵、Mac 字型）不適合 Windows，只用考試設定
        run(sys.executable, REPO / "tools" / "sync_vscode_settings.py", "--vscode-data", vs_dir / "data",
            "--config", REPO / "config", "--no-local")
        # 介面語言：沿用這台 Mac 的 VS Code 設定，沒有就用繁體中文（擴充清單裡有繁中語言包）
        sys.path.insert(0, str(REPO / "tools"))
        from sync_vscode_settings import load_jsonc
        mac_argv = Path.home() / ".vscode" / "argv.json"
        locale = ((load_jsonc(mac_argv) or {}).get("locale") if mac_argv.is_file() else None) or "zh-tw"
        argv_out = vs_dir / "data" / "argv.json"
        current = (load_jsonc(argv_out) or {}) if argv_out.is_file() else {}
        current["locale"] = locale
        current.setdefault("enable-crash-reporter", False)
        argv_out.write_text(json.dumps(current, ensure_ascii=False, indent=4), encoding="utf-8")
        ext_files = ["extensions.txt"] + ([] if args.skip_extra_extensions else ["extensions-extra.txt"])
        wanted = [line.strip() for f in ext_files
                  for line in (REPO / "config" / f).read_text(encoding="utf-8").splitlines() if line.strip()]
        download_extensions(vs_dir, wanted)

    # ------------------------------------------------------------ 4. workspace
    step("4. workspace（程式、範本、筆記、講義、作業）")
    for d in ("statkit", "tools", "notes"):
        copy_tree(REPO / d, ws / d)
    # 開發用的檢查工具不用帶進隨身碟
    shutil.rmtree(ws / "tools" / "ci", ignore_errors=True)
    (ws / "tools" / "validate_repo.py").unlink(missing_ok=True)
    for name, what, src in (("handouts", "講義", args.handouts), ("homework", "作業", args.homework)):
        if not src or not str(src).strip():
            print(f"略過{what}（沒有指定資料夾）")
        elif Path(src).expanduser().is_dir():
            copy_tree(Path(src).expanduser(), ws / name)
            print(f"已複製{what}：{src}")
        else:
            print(f"略過{what}（找不到資料夾：{src}）")
    for d in ("exam", "data", "homework", "fonts", ".vscode", "tools/templates"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "templates" / "exam_template.ipynb", ws / "tools" / "templates" / "exam_template.ipynb")
    student = ws / "tools" / "student.json"
    if args.student_id.strip() and args.student_name.strip():
        sid, sname = args.student_id.strip().upper(), args.student_name.strip()
        student.write_text(json.dumps({"id": sid, "name": sname}, ensure_ascii=False, indent=4), encoding="utf-8")
        print(f"學號姓名：{sid} {sname}")
    elif (REPO / "config" / "student.json").is_file():
        shutil.copy2(REPO / "config" / "student.json", student)
    elif not student.is_file():
        print("還沒設定學號姓名，第一次「新增考卷」時會請你輸入")
        shutil.copy2(REPO / "config" / "student.example.json", student)
    shutil.copy2(REPO / "templates" / "00_索引.ipynb", ws / "00_索引.ipynb")
    shutil.copy2(REPO / "templates" / "常見問題.md", ws / "常見問題.md")
    shutil.copy2(REPO / "templates" / "data_README.md", ws / "data" / "README.md")
    for src_name, dst_name in (("vscode-workspace-settings.json", "settings.json"), ("vscode-tasks.json", "tasks.json")):
        text = (REPO / "config" / src_name).read_text(encoding="utf-8-sig").replace("__WINPY__", winpy.name)
        (ws / ".vscode" / dst_name).write_text(text, encoding="utf-8")
    if any(p.suffix.lower() == ".pdf" for p in (ws / "handouts").glob("*")):
        run(sys.executable, ws / "tools" / "extract_pdf_text.py", ws / "handouts")

    # ------------------------------------------------------------ 5. 字型與離線文件
    step("5. 中文字型與離線文件")
    shutil.copy2(get_file(SOURCES["font"], "NotoSansTC-VF.ttf"), ws / "fonts" / "NotoSansTC-VF.ttf")
    for name, url in docs.items():
        dst = ws / "docs-offline" / name
        if dst.exists():
            continue
        if not url:
            print(f"[WARN] 找不到 {name} 的離線文件網址，略過")
            continue
        try:
            expand(get_file(url, f"docs-{name}.zip"), dst)
            print(f"離線文件：{name}")
        except Exception as e:
            shutil.rmtree(dst, ignore_errors=True)
            print(f"[WARN] 抓不到 {name} 的離線文件（{e}），略過；可以用 hover / Shift+Tab 看說明")

    # ------------------------------------------------------------ 6. 啟動器
    step("6. 啟動器")
    for bat in (REPO / "launchers").glob("*.bat"):
        # 沒裝的編輯器就不放它的啟動檔
        if (args.skip_vscode and bat.name.startswith("1_")) or (args.skip_jupyterlab and bat.name.startswith("2_")):
            continue
        shutil.copy2(bat, out / bat.name)                       # 原樣複製，保留 CRLF
    shutil.copy2(REPO / "templates" / "使用說明.txt", out / "使用說明.txt")
    # 套件清單（相當於 pip freeze）：從 *.dist-info 的資料夾名稱取得
    lock = sorted({"==".join(d.name[:-len(".dist-info")].split("-", 1)) for d in site.glob("*.dist-info")}, key=str.lower)
    (ws / "tools" / "requirements-lock.txt").write_text("\n".join(lock) + "\n", encoding="utf-8")
    step()

    if args.clean_downloads:
        shutil.rmtree(DL, ignore_errors=True)
        print(f"已刪除下載快取：{DL}")

    print("\n各步驟耗時：")
    for title, sec in step_times.items():
        print(f"  {int(sec // 60):3}:{int(sec % 60):02}  {title}")
    files = [p for p in out.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"\n完成：{out}（{size / 1024 ** 3:.2f} GB，{len(files)} 個檔案）。")
    if args.usb:
        copy_to_usb(out, args.usb)
    print("\n接下來：把隨身碟插到任何一台 Windows 電腦，執行一次 4_環境檢查.bat。"
          "\n第一次執行會安裝 VS Code 擴充（不需要網路，約 1 分鐘），並確認環境在 Windows 上都能用。")


if __name__ == "__main__":
    main()
