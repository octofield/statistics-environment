"""隨身碟 WinPython 每次啟動時自動執行（由 site-packages\\statkit_workspace.pth 載入）。

不管 Python 是從 1_啟動VSCode.bat、VS Code 的 Jupyter 擴充、還是其他地方啟動，都確保：
1. 任何位置的 notebook 都能 import statkit（把 workspace 加進 sys.path）
2. PATH 最前面是隨身碟的 python\\ 和 python\\Scripts\\：
   VS Code 匯出 HTML 時執行 `python -m jupyter nbconvert`，jupyter 會在 PATH 上找 jupyter-nbconvert，
   如果考場電腦（或你自己的電腦）裝了別的 Python，可能會用到它的 jupyter-nbconvert 而出現
   ModuleNotFoundError: No module named 'nbconvert'
3. 不讀考場電腦的 user site-packages（%APPDATA%\\Python\\...），也讓子程序不讀
4. matplotlib / Jupyter / IPython 的設定與快取放在 WinPython\\settings（跟 tools\\env.bat 一樣）

由 build.ps1 / setup/build_mac.py 複製到 WinPython 的 site-packages；這個檔案出錯也不能讓 Python 無法啟動。
"""
import os
import sys


def _setup():
    import site

    here = os.path.dirname(os.path.abspath(__file__))       # ...\python\Lib\site-packages
    pydir = os.path.dirname(os.path.dirname(here))           # ...\python
    winpy = os.path.dirname(pydir)                            # ...\WPy64-xxxx
    workspace = os.path.join(os.path.dirname(winpy), "workspace")

    # 1. statkit
    if os.path.isdir(workspace) and workspace not in sys.path:
        sys.path.append(workspace)

    # 2. PATH：隨身碟的 Python 優先
    norm = lambda p: os.path.normcase(os.path.normpath(p))
    first = [pydir, os.path.join(pydir, "Scripts")]
    rest = [p for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and norm(p) not in {norm(f) for f in first}]
    os.environ["PATH"] = os.pathsep.join(first + rest)

    # 3. 不讀 user site-packages
    user_site = getattr(site, "USER_SITE", None)
    if user_site:
        sys.path[:] = [p for p in sys.path if norm(p) != norm(user_site)]
    os.environ["PYTHONNOUSERSITE"] = "1"

    # 4. 設定與快取的位置（已經由 env.bat 設好的就不動）
    settings = os.path.join(winpy, "settings")
    for key, sub in (("MPLCONFIGDIR", ".matplotlib"), ("JUPYTER_CONFIG_DIR", ".jupyter"),
                     ("JUPYTER_DATA_DIR", "jupyter_data"), ("IPYTHONDIR", ".ipython")):
        os.environ.setdefault(key, os.path.join(settings, sub))


try:
    _setup()
except Exception:      # 出錯也不能讓 Python 啟動失敗
    pass
