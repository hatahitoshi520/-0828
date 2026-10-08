#!/usr/bin/env bash
# AI Team Starter: 4層構成を邪魔する設定がないか「確認だけ」するスクリプト。
# ファイルは一切変更しません。
set -u

KEYS='CLAUDE_CODE_DISABLE_ADVISOR_TOOL|CLAUDE_CODE_EFFORT_LEVEL|DISABLE_TELEMETRY|DO_NOT_TRACK|CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC|effortLevel|advisorModel'

echo "== 現在の環境変数"
env | grep -E "^($KEYS)=" || echo "  （該当なし）"

echo
echo "== 設定ファイル・シェル設定"
for f in \
  "$HOME/.claude/settings.json" \
  "$HOME/.claude/settings.local.json" \
  ".claude/settings.json" \
  ".claude/settings.local.json" \
  "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.profile"
do
  [ -f "$f" ] || continue
  hits=$(grep -nE "$KEYS" "$f" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "-- $f"
    echo "$hits" | sed 's/^/  /'
  fi
done

echo
cat <<'NOTE'
== 見方
  CLAUDE_CODE_DISABLE_ADVISOR_TOOL            … 設定されていると advisor が使えません
  CLAUDE_CODE_EFFORT_LEVEL                    … settings.json の effortLevel より優先されます
  DISABLE_TELEMETRY / DO_NOT_TRACK /
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC    … 機能の配信（feature flag）が止まり、
                                                 一部の新機能が使えない場合があります
  effortLevel / advisorModel                  … 既に設定されている値を確認してください
NOTE
