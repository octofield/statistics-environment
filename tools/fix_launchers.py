"""把 python\\Scripts 裡的執行檔（jupyter、pylsp、ipython…）換成可以跟著隨身碟搬家的格式。

uv 安裝套件時會把這些 .exe 寫成 uv 自己的 trampoline，裡面記的是建立時的 Python 路徑；
整個環境搬到別的位置（例如複製到隨身碟）後就會出現「uv trampoline failed to canonicalize script path」。
WinPython 自己的執行檔是 distlib 格式、寫的是 #!python.exe（靠 env.bat 設好的 PATH 找到 Python），
這裡用 pip 內附的 distlib 把每個進入點重新產生成同樣的格式。

由 build.ps1 在安裝套件後執行；在 Mac 上建立的環境沒有這些執行檔，由 finish_setup.py 第一次在 Windows 上補。

    python tools/fix_launchers.py            重新產生不可攜的執行檔
    python tools/fix_launchers.py --check    只列出不可攜的執行檔（有的話結束代碼為 1）
"""
import sys
import sysconfig
from importlib.metadata import distributions
from pathlib import Path

SHEBANG = b"#!python.exe\n"
SCRIPTS = Path(sysconfig.get_path("scripts"))
MARKER = SCRIPTS / ".portable-launchers"        # 有這個檔 = 已經修好（finish_setup.py 看它決定要不要再跑）


def entry_points():
    """這個 Python 的 site-packages 裡所有套件的命令列進入點：[(名稱, 'module:func', 是否為 GUI)]"""
    site = sysconfig.get_path("purelib")
    eps = {}
    for dist in distributions(path=[site]):
        for ep in dist.entry_points:
            if ep.group in ("console_scripts", "gui_scripts"):
                eps[ep.name] = (ep.value, ep.group == "gui_scripts")
    return [(name, value, gui) for name, (value, gui) in sorted(eps.items())]


def is_portable(exe):
    try:
        return SHEBANG in exe.read_bytes()[-4096:]
    except OSError:
        return False


def nonportable(scripts=SCRIPTS):
    """不存在、或不是 #!python.exe 格式的執行檔名稱"""
    return [name for name, _, _ in entry_points() if not is_portable(scripts / f"{name}.exe")]


def fix(scripts=SCRIPTS):
    from pip._vendor.distlib.scripts import ScriptMaker

    bad = set(nonportable(scripts))
    maker = ScriptMaker(None, str(scripts), add_launchers=True)
    maker.executable = "python.exe"             # 跟 WinPython 一樣：用 PATH 找 Python，不寫死路徑
    maker.variants = {""}                       # 只產生 jupyter.exe，不要 jupyter-3.13.exe
    maker.clobber = True
    for name, value, gui in entry_points():
        if name in bad:
            maker.make(f"{name} = {value}", {"gui": gui})
    MARKER.write_text("ok\n", encoding="ascii")
    return sorted(bad)


if __name__ == "__main__":
    if "--check" in sys.argv:
        bad = nonportable()
        print("全部可攜" if not bad else f"不可攜的執行檔（{len(bad)} 個）：{', '.join(bad)}")
        sys.exit(1 if bad else 0)
    fixed = fix()
    print(f"已重新產生 {len(fixed)} 個執行檔（#!python.exe 格式）" if fixed else "Scripts 的執行檔都已經是可攜格式")
