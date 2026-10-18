"""在啟動可攜式 VS Code 之前，用「目前的路徑」產生語言包快取 languagepacks.json。

VS Code 啟動時要先讀到這個檔才會套用中文介面，但它是 VS Code 啟動之後才產生、而且存的是絕對路徑，
所以第一次啟動、或隨身碟換了磁碟代號時都會變回英文。由 1_啟動VSCode.bat 在啟動前呼叫。

    python tools/vscode_locale.py [VSCode\\data 資料夾]
"""
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "VSCode" / "data"


def build_cache(data_dir):
    """回傳 languagepacks.json 的內容；沒有設定 locale 或找不到對應語言包時回傳 None。"""
    argv = data_dir / "argv.json"
    if not argv.is_file():
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sync_vscode_settings import load_jsonc

    locale = str((load_jsonc(argv) or {}).get("locale", "")).lower()
    if not locale or locale.startswith("en"):
        return None

    ext_root = data_dir / "extensions"
    for ext in load_jsonc(ext_root / "extensions.json") or []:
        folder = ext_root / ext.get("relativeLocation", "")
        manifest = folder / "package.json"
        if not ext.get("relativeLocation") or not manifest.is_file():
            continue
        pkg = json.loads(manifest.read_text(encoding="utf-8-sig"))
        for loc in pkg.get("contributes", {}).get("localizations", []):
            if str(loc.get("languageId", "")).lower() != locale:
                continue
            ident = ext["identifier"]
            version = ext.get("version") or pkg["version"]
            key = ident.get("uuid") or ident["id"]          # VS Code：md5(uuid + version)
            return {locale: {
                "hash": hashlib.md5((key + version).encode("utf-8")).hexdigest(),
                "extensions": [{"extensionIdentifier": ident, "version": version}],
                "translations": {t["id"]: str((folder / t["path"]).resolve()) for t in loc.get("translations", [])},
                "label": loc.get("localizedLanguageName") or loc.get("languageName") or locale,
            }}
    return None


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    try:
        cache = build_cache(data_dir)
        if cache is None:
            return
        out = data_dir / "user-data" / "languagepacks.json"
        text = json.dumps(cache, ensure_ascii=False)
        if out.is_file() and out.read_text(encoding="utf-8") == text:
            return
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    except Exception as e:   # 失敗也不要擋住 VS Code 啟動，頂多是英文介面
        print(f"[WARN] language pack cache: {e}")


if __name__ == "__main__":
    main()
