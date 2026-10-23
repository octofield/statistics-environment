"""第一次在 Windows 上使用時完成安裝（給在 Mac 上建立的環境用）。

- Mac 上沒辦法執行 Windows 版 VS Code 來安裝擴充，所以 setup/build_mac.py 先把 Windows 版的 .vsix
  放在 VSCode\\data\\pending-vsix\\，這裡用可攜式 VS Code 離線安裝，裝好就刪掉那個資料夾。
- Mac 上裝的套件沒有 python\\Scripts\\*.exe（jupyter、pylsp…），用 fix_launchers.py 補上。
由 1_啟動VSCode.bat、4_環境檢查.bat 在啟動前呼叫；在 Windows 上建立的環境兩件事都已經做好，什麼都不做。

    python tools/finish_setup.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VSCODE = ROOT / "VSCode"
PENDING = VSCODE / "data" / "pending-vsix"


def installed_ids():
    path = VSCODE / "data" / "extensions" / "extensions.json"
    try:
        return {e["identifier"]["id"].lower() for e in json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError):
        return set()


def install(vsix):
    cmd = [str(VSCODE / "bin" / "code.cmd")]
    for p in vsix:
        cmd += ["--install-extension", str(p)]
    env = dict(os.environ)
    env.pop("ELECTRON_RUN_AS_NODE", None)     # 有這個變數時 Code.exe 會變成單純的 Node
    return subprocess.run(cmd + ["--force"], env=env).returncode


def main():
    import fix_launchers
    if not fix_launchers.MARKER.exists():
        fixed = fix_launchers.fix()
        if fixed:
            print(f"第一次在 Windows 上使用：產生 {len(fixed)} 個命令列執行檔（jupyter、pylsp…）")
    vsix = sorted(PENDING.glob("*.vsix")) if PENDING.is_dir() else []
    if not vsix:
        return 0
    # order.txt：相依的擴充排在前面（build_mac.py 寫的）
    order_file = PENDING / "order.txt"
    if order_file.is_file():
        ranked = [PENDING / n for n in order_file.read_text(encoding="utf-8").split() if (PENDING / n).is_file()]
        vsix = ranked + [p for p in vsix if p not in ranked]
    print(f"第一次在 Windows 上使用：安裝 VS Code 擴充（{len(vsix)} 個，不需要網路，大約 1 分鐘）…")
    if install(vsix) != 0:
        # 一次裝失敗時（VS Code 會同時裝，extension pack 裡的擴充可能撞在一起），沒裝好的照順序一個一個裝
        done = installed_ids()
        missing = [p for p in vsix if p.name.split("__")[0].lower() not in done]
        print(f"改成一個一個安裝剩下的 {len(missing)} 個…")
        failed = [p.name for p in missing if install([p]) != 0]
        if failed:
            print(f"[WARN] 這些 VS Code 擴充安裝失敗，下次啟動會再試一次：{', '.join(failed)}")
            return 1
    shutil.rmtree(PENDING, ignore_errors=True)
    # 擴充裝好之後才有語言包，重建快取，第一次啟動就是中文介面
    subprocess.run([sys.executable, str(Path(__file__).with_name("vscode_locale.py")), str(VSCODE / "data")])
    print("VS Code 擴充安裝完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
