#!/bin/bash
# 統計學考試環境：在 Mac 上建立給 Windows 考場用的隨身碟。
#
# 在 Finder 雙擊這個檔案（第一次如果出現「無法打開」，請按右鍵 →「打開」），
# 或在「終端機」執行：bash setup_mac.command
#
# 不帶參數會一步一步問；帶參數就不問，直接交給 setup/build_mac.py，例如：
#   ./setup_mac.command --out ~/Desktop/STAT_EXAM --skip-docs
# 不需要系統管理員權限，也不會改系統設定：uv 與 Python 都放在 build/downloads 和 uv 的快取裡。
set -eo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"
DL="$REPO/build/downloads"
mkdir -p "$DL"

# 從 Finder 下載的 zip 會帶「從網路下載」的標記，複製到隨身碟會多出一堆 ._ 檔案，先拿掉
xattr -dr com.apple.quarantine "$REPO" 2>/dev/null || true

src() { sed -n "s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" "$REPO/config/sources.json" | head -n 1; }
VERSION="$(tr -d '[:space:]' < "$REPO/VERSION")"
newer_version() {   # newer_version 1.2.0 1.1.0 → 第一個比第二個新時成功
    awk -v a="$1" -v b="$2" 'BEGIN { split(a, x, "."); split(b, y, ".");
        for (i = 1; i <= 3; i++) { if (x[i] + 0 > y[i] + 0) exit 0; if (x[i] + 0 < y[i] + 0) exit 1 } exit 1 }'
}

# ------------------------------------------------------------------ uv（會自動下載 Python）
if [ "$(uname -m)" = "arm64" ]; then UV_URL="$(src uv_mac_arm64)"; else UV_URL="$(src uv_mac_x64)"; fi
UV="$DL/uv-mac/uv"
if [ ! -x "$UV" ]; then
    echo "下載 uv ..."
    curl -L --fail -sS --retry 3 -o "$DL/uv-mac.tar.gz.part" "$UV_URL"
    mkdir -p "$DL/uv-mac"
    tar -xzf "$DL/uv-mac.tar.gz.part" -C "$DL/uv-mac" --strip-components 1
    rm -f "$DL/uv-mac.tar.gz.part"
fi
export UV
# WinPython 的 Python 版本（WinPython64-3.13.15.0dot.zip → 3.13），.pyc 要用同一個版本編譯
PY_MINOR="$(src winpython | sed -n 's/.*WinPython64-\([0-9]*\.[0-9]*\)\..*/\1/p')"

# ------------------------------------------------------------------ 問答
ask_yes() {   # ask_yes "問題" Y|N（預設）
    local ans
    read -r -p "$1 $( [ "$2" = Y ] && echo '[Y/n]' || echo '[y/N]' ) " ans
    ans="${ans:-$2}"
    [[ "$ans" =~ ^[Yy] ]]
}
choose_folder() {
    osascript -e "POSIX path of (choose folder with prompt \"$1\")" 2>/dev/null || true
}

ARGS=("$@")
if [ $# -eq 0 ]; then
    echo "=================================================="
    echo " 統計學考試環境 v$VERSION：在 Mac 上建立給 Windows 考場用的隨身碟"
    echo "=================================================="
    echo "這不是學校或任何課程的官方工具，請自行確認考試規定。"
    echo "需要網路（下載約 1 GB）與約 4 GB 的空間，大約 15–40 分鐘。"
    # 有新版就提醒（查不到就略過）
    LATEST="$(curl -fsS --max-time 5 "$(src releases_api)" 2>/dev/null | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -n 1 || true)"
    if [ -n "$LATEST" ] && newer_version "$LATEST" "$VERSION"; then
        echo "★ 有新版 v$LATEST（目前 v$VERSION），建議先到 $(src releases_page) 下載新版再執行。"
    fi
    echo

    echo "學號姓名不會自動寫進考卷，只用來在匯入考卷後提醒你填、匯出 HTML 時檢查考卷裡有沒有寫。"
    read -r -p "學號（例如 B12345678；直接按 Enter 略過）：" SID
    if [ -n "$SID" ]; then
        until [[ "$SID" =~ ^[A-Za-z][0-9]{8}$ ]]; do
            read -r -p "格式不對（1 個英文字母 + 8 個數字），請重新輸入：" SID
        done
        SNAME=""
        until [ -n "$SNAME" ]; do read -r -p "姓名：" SNAME; done
        ARGS+=(--student-id "$SID" --student-name "$SNAME")
    fi

    HANDOUTS=""; HOMEWORK=""
    if ask_yes "要放講義嗎？（會開視窗讓你選資料夾）" N; then HANDOUTS="$(choose_folder "選擇講義資料夾")"; fi
    if ask_yes "要放作業嗎？（會開視窗讓你選資料夾）" N; then HOMEWORK="$(choose_folder "選擇作業資料夾")"; fi
    ARGS+=(--handouts "$HANDOUTS" --homework "$HOMEWORK")
    [ -n "$HANDOUTS$HOMEWORK" ] && echo "講義、作業通常有著作權或個人資料，請不要上傳到公開的地方。"

    echo
    echo "要安裝的元件（預設全裝）："
    echo "  • 可攜式 VS Code 與必要擴充（約 1.2 GB）：主力編輯器"
    echo "  • 附加 VS Code 擴充（約 25 MB）：PDF 檢視、Excel 檢視、Rainbow CSV、Code Runner"
    echo "  • JupyterLab（約 0.1 GB）：在瀏覽器作答的備案"
    echo "  • 離線文件（約 0.65 GB、2 萬個檔案）：pandas / numpy / scipy / Python 官方文件"
    if ! ask_yes "全部安裝？（選 n 逐項決定）" Y; then
        while :; do
            COMP_ARGS=()
            VSCODE=1; LAB=1
            if ! ask_yes "裝 VS Code？（不裝：只能用 JupyterLab 作答，匯出 HTML 改用 3_匯出HTML.bat）" Y; then
                COMP_ARGS+=(--skip-vscode); VSCODE=0
            elif ! ask_yes "裝附加 VS Code 擴充？（不裝：講義 PDF、Excel 不能在 VS Code 裡打開）" Y; then
                COMP_ARGS+=(--skip-extra-extensions)
            fi
            if ! ask_yes "裝 JupyterLab？（不裝：VS Code 出問題時沒有備案，有些課程規定要用 Jupyter Lab）" Y; then
                COMP_ARGS+=(--skip-jupyterlab); LAB=0
            fi
            if [ $VSCODE -eq 1 ] || [ $LAB -eq 1 ]; then break; fi
            echo "VS Code 和 JupyterLab 至少要選一個，不然沒有地方可以寫考卷。請重新選擇。"
        done
        ARGS+=(${COMP_ARGS[@]+"${COMP_ARGS[@]}"})
        if ! ask_yes "下載離線文件？（不裝：只能用滑鼠停在函式上看說明；好處是複製到隨身碟快很多）" Y; then
            ARGS+=(--skip-docs)
        fi
    fi

    OUT="$HOME/Desktop/STAT_EXAM"
    read -r -p "建立位置（直接按 Enter 用 $OUT）：" OUT_IN
    ARGS+=(--out "${OUT_IN:-$OUT}")

    VOLUMES=()
    for v in /Volumes/*; do
        [ -d "$v" ] && [ "$(cd "$v" && pwd -P)" != "/" ] && VOLUMES+=("$v")
    done
    if [ ${#VOLUMES[@]} -gt 0 ] && ask_yes "完成後複製到隨身碟？" Y; then
        echo "隨身碟要是 ExFAT 或 FAT32 格式，Windows 才讀得到："
        for i in "${!VOLUMES[@]}"; do echo "  $((i + 1))) ${VOLUMES[$i]}"; done
        read -r -p "選哪一個？（輸入編號，直接按 Enter 不複製）" N
        if [[ "$N" =~ ^[0-9]+$ ]] && [ "$N" -ge 1 ] && [ "$N" -le ${#VOLUMES[@]} ]; then
            ARGS+=(--usb "${VOLUMES[$((N - 1))]}")
        fi
    fi
    echo
fi

set +e
"$UV" run --no-project --python "$PY_MINOR" --with pypdf "$REPO/setup/build_mac.py" ${ARGS[@]+"${ARGS[@]}"}
CODE=$?
set -e
if [ $# -eq 0 ]; then
    echo
    if [ $CODE -eq 0 ]; then echo "全部完成。"; else echo "建立失敗（exit $CODE）。可以直接再執行一次，已下載的檔案會沿用。"; fi
    read -r -p "按 Enter 關閉…" _
fi
exit $CODE
