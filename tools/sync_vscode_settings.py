"""把這台電腦的 VS Code 設定同步到可攜式 VS Code（排除 AI 與綁本機的設定），考試設定優先。

    python tools/sync_vscode_settings.py --vscode-data <STAT_EXAM\\VSCode\\data> --config <repo\\config> [--no-local]

會寫入：
    <vscode-data>\\user-data\\User\\settings.json      本機設定（過濾後）+ 考試設定覆蓋
    <vscode-data>\\user-data\\User\\keybindings.json   本機快捷鍵（去掉 AI 指令）
    <vscode-data>\\user-data\\User\\snippets\\*         本機 snippets + stat.code-snippets
    <vscode-data>\\argv.json                         介面語言（locale）
"""
import argparse
import json
import os
import re
import shutil
from pathlib import Path

# 考試禁用 AI：這些開頭的設定一律不帶（chat.disableAIFeatures 由考試設定強制為 true）
AI_PREFIXES = ("github.copilot", "tabnine", "geminicodeassist", "gemini", "claudeCode", "claude",
               "inlineChat", "chat.", "codeium", "continue.", "cody.", "aws.amazonQ", "intellicode")
AI_WORDS = ("copilot", "claude", "gemini", "tabnine", "codeium", "inlinechat", "workbench.action.chat",
            "amazonq", "intellicode")
# 跟考試無關、或綁這台電腦的設定
LOCAL_PREFIXES = ("dart.", "cmake.", "java.", "redhat.", "C_Cpp", "http.", "remote.", "sqltools.",
                  "python.defaultInterpreterPath", "python.pythonPath", "terminal.integrated.profiles",
                  "terminal.integrated.defaultProfile", "jupyter.kernels")
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.IGNORECASE)


def load_jsonc(path):
    """讀 VS Code 的 JSONC：允許 // 與 /* */ 註解、結尾多餘的逗號。"""
    text = Path(path).read_text(encoding="utf-8-sig")
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    return json.loads(cleaned) if cleaned.strip() else None


def _has_local_path(value):
    if isinstance(value, str):
        return bool(LOCAL_PATH_RE.search(value))
    if isinstance(value, dict):
        return any(_has_local_path(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_local_path(v) for v in value)
    return False


def filter_settings(local):
    kept, dropped = {}, {}
    for key, value in local.items():
        if key.startswith(AI_PREFIXES):
            dropped[key] = "AI"
        elif key.startswith(LOCAL_PREFIXES):
            dropped[key] = "跟考試無關 / 綁本機"
        elif _has_local_path(value):
            dropped[key] = "含本機路徑"
        else:
            kept[key] = value
    return kept, dropped


def filter_keybindings(bindings):
    keep = [b for b in bindings
            if not any(w in str(b.get("command", "")).lower() for w in AI_WORDS)
            and not any(w in str(b.get("when", "")).lower() for w in AI_WORDS)]
    return keep, len(bindings) - len(keep)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vscode-data", required=True, type=Path, help="可攜式 VS Code 的 data 資料夾")
    ap.add_argument("--config", required=True, type=Path, help="repo 的 config 資料夾")
    ap.add_argument("--local", type=Path, default=Path(os.environ.get("APPDATA", "")) / "Code" / "User")
    ap.add_argument("--argv", type=Path, default=Path.home() / ".vscode" / "argv.json")
    ap.add_argument("--no-local", action="store_true", help="只用考試設定，不讀這台電腦的設定")
    args = ap.parse_args()

    user = args.vscode_data / "user-data" / "User"
    exam = load_jsonc(args.config / "vscode-user-settings.json") or {}
    use_local = not args.no_local and (args.local / "settings.json").is_file()

    # settings.json：本機（過濾後）→ 考試設定覆蓋
    settings = {}
    if use_local:
        kept, dropped = filter_settings(load_jsonc(args.local / "settings.json") or {})
        settings.update(kept)
        overridden = sorted(k for k in kept if k in exam and kept[k] != exam[k])
        print(f"本機設定：帶過去 {len(kept)} 項，排除 {len(dropped)} 項")
        for k, why in sorted(dropped.items()):
            print(f"  ✗ {k}（{why}）")
        for k in overridden:
            print(f"  ↻ {k}：改用考試設定 {json.dumps(exam[k], ensure_ascii=False)}")
    else:
        print("不讀本機設定，只用考試設定")
    settings.update(exam)
    write_json(user / "settings.json", settings)

    # keybindings.json
    kb_path = args.local / "keybindings.json"
    if use_local and kb_path.is_file():
        bindings, removed = filter_keybindings(load_jsonc(kb_path) or [])
        write_json(user / "keybindings.json", bindings)
        print(f"快捷鍵：帶過去 {len(bindings)} 項" + (f"，排除 AI 指令 {removed} 項" if removed else ""))

    # snippets：本機的先放，再放考試版（同名時考試版優先）
    snip_dir = user / "snippets"
    snip_dir.mkdir(parents=True, exist_ok=True)
    local_snips = list((args.local / "snippets").glob("*")) if use_local else []
    for f in local_snips:
        if f.is_file():
            shutil.copy2(f, snip_dir / f.name)
    shutil.copy2(args.config / "stat.code-snippets", snip_dir / "stat.code-snippets")
    print(f"snippets：本機 {len(local_snips)} 個 + stat.code-snippets")

    # argv.json：介面語言
    if use_local and args.argv.is_file():
        locale = (load_jsonc(args.argv) or {}).get("locale")
        if locale:
            argv_out = args.vscode_data / "argv.json"
            current = (load_jsonc(argv_out) or {}) if argv_out.is_file() else {}
            current["locale"] = locale
            current.setdefault("enable-crash-reporter", False)
            write_json(argv_out, current)
            print(f"介面語言：{locale}")


if __name__ == "__main__":
    main()
