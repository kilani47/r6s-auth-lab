#!/usr/bin/env bash
# Downloads the official-style operator icons used across the SHIELDBREAKER campaign.
# Source: r6operators (community package of Ubisoft-derived operator icons) via jsDelivr.
# Personal/educational lab use. Re-run any time to refresh assets.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HERE/../static/img/ops"
VER="2.12.0"
BASE="https://cdn.jsdelivr.net/npm/r6operators@${VER}/dist/icons"
mkdir -p "$DEST"

OPS=(iq sledge dokkaebi thermite blitz nomad mute castle clash oryx aruni kaid)

echo "[*] Fetching ${#OPS[@]} operator icons -> $DEST"
for op in "${OPS[@]}"; do
  if curl -fsSL -m 20 -o "$DEST/$op.svg" "$BASE/$op.svg"; then
    echo "  [ok] $op.svg"
  else
    echo "  [!!] failed: $op" >&2
  fi
done
echo "[*] Done."

cat <<'NOTE'

--- OPTIONAL: your own wallpaper / victory clips ------------------------------
The UI will automatically use these if you drop them in:
    static/img/intro-wall.jpg      full-bleed wallpaper on Command's intro splash
    static/img/victory-op<N>.gif   (or .webp) plays on Operation N's breach overlay
Grab them from any wallpaper/clip site you like and name them as above -- check
templates/op<N>_console.html for the exact filename/extension each op expects.
If absent, a built-in CSS icon-slam animation is used instead. Nothing breaks.
--------------------------------------------------------------------------------
NOTE
