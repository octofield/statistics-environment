"""把 WinPython 裡的 .pyc 換成「不檢查原始檔時間」的格式（PEP 552 unchecked-hash）。

一般的 .pyc 會記錄 .py 的修改時間，載入時對不上就重新編譯。複製到 FAT32 / exFAT 隨身碟後，
檔案時間會被進位成 2 秒（例如 …251.09 秒變成 …252 秒），大約一半的 .pyc 會被當成過期：
在考場上每次 import 都要重新編譯（比較慢），重新編譯的 .pyc 下次更新時又會被複製回去。
unchecked-hash 格式的 .pyc 不看時間，複製到哪裡都有效。

只轉換「時間格式」的 .pyc（uv / compileall 剛產生的），已經轉過的會跳過，所以重新建立時很快。
WinPython 的檔案只會在重新建立時被換掉（換套件時 uv 會連 .pyc 一起重寫），不會有「.py 改了但 .pyc 沒更新」的問題。

    python setup/hash_pyc.py WinPython\\python\\Lib
由 build.ps1 / setup/build_mac.py 在安裝套件、預先編譯之後執行。
"""
import importlib.util
import os
import py_compile
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

MAGIC = importlib.util.MAGIC_NUMBER


def needs_convert(pyc):
    """時間格式（flags = 0）且版本相符的 .pyc 才要轉。"""
    try:
        with open(pyc, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    return len(head) == 8 and head[:4] == MAGIC and struct.unpack("<I", head[4:8])[0] == 0


def convert(pair):
    import warnings
    src, pyc = pair
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")      # 套件附的測試檔常有 SyntaxWarning，不影響使用
            py_compile.compile(src, cfile=pyc, doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        return True
    except Exception:          # 少數不能編譯的檔案（例如範例、測試資料）維持原樣
        return False


def find_pairs(lib):
    """要編譯的 (.py, .pyc)：時間格式的 .pyc，以及標準函式庫裡還沒編譯過的 .py（site-packages 由 uv 編譯）。
    已經是 unchecked-hash 的不動：重新寫入會改變檔案時間，robocopy 就會再複製一次到隨身碟。"""
    lib = Path(lib)
    site = lib / "site-packages"
    for src in lib.rglob("*.py"):
        pyc = Path(importlib.util.cache_from_source(str(src)))
        if pyc.exists():
            if needs_convert(pyc):
                yield str(src), str(pyc)
        elif site not in src.parents:
            yield str(src), str(pyc)


def main(lib):
    pairs = list(find_pairs(lib))
    if not pairs:
        print("所有 .pyc 都已經是不檢查時間的格式，不需要重新編譯")
        return 0
    with ProcessPoolExecutor(max_workers=max(1, min(8, os.cpu_count() or 1))) as pool:
        ok = sum(pool.map(convert, pairs, chunksize=64))
    print(f"已編譯 {ok} 個 .pyc（不檢查時間的格式，複製到 FAT32 / exFAT 隨身碟也不會失效）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else Path(sys.executable).parent / "Lib"))
