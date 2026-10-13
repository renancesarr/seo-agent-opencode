#!/usr/bin/env bash
# Observador de PRs — dispara o review cruzado automaticamente.
#
#   PR da zcode-ai  sem review do bot (Fencing3422) após o último push
#     -> executa `codex exec` headless como ai-codex (publica o review; merge se aprovar)
#   PR da codex-ai sem review do renancesarr após o último push
#     -> notifica o humano (a automação do ZCode cobre o review deste lado)
#
# Estado e logs em ~/.local/state/pr-watcher/. Roda via systemd user timer
# (seo-pr-watcher.timer) a cada 2 minutos; flock impede sobreposição.
set -u

REPO="renancesarr/seo-agent-opencode"
REPO_DIR="/home/nanerr/my-project/seo-agent-infra"
STATE="$HOME/.local/state/pr-watcher"
CODEX_BIN="$(command -v codex || echo /usr/lib/chatgpt/resources/codex)"
GH_BIN="$(command -v gh || echo /usr/bin/gh)"

mkdir -p "$STATE"
LOG="$STATE/watcher.log"
echo "=== $(date -Is) execução ===" >> "$LOG"
exec >> "$LOG" 2>&1

exec 9> "$STATE/lock"
flock -n 9 || { echo "outra instância rodando; skip"; exit 0; }

BOT_TOKEN="$("$GH_BIN" auth token --user Fencing3422 2>/dev/null)" || { echo "sem token do bot; skip"; exit 0; }
cd "$REPO_DIR" || exit 0

# PRs abertos para dev-ai com: último push, último review do bot e do renancesarr
PRS=$("$GH_BIN" pr list --repo "$REPO" --base dev-ai --state open \
  --json number,headRefName,commits,reviews --jq '[ .[] | {
      number, head: .headRefName,
      last_push: (.commits | last | .committedDate),
      bot_review: ([.reviews[] | select(.author.login=="Fencing3422") | .submittedAt] | max),
      me_review:  ([.reviews[] | select(.author.login=="renancesarr") | .submittedAt] | max)
    } ]')
COUNT=$(echo "$PRS" | jq -s 'length')
echo "PRs abertos para dev-ai: $COUNT"

echo "$PRS" | jq -c '.[]' | while read -r pr; do
  n=$(jq -r .number <<< "$pr")
  head=$(jq -r .head <<< "$pr")
  last_push=$(jq -r .last_push <<< "$pr")

  case "$head" in
    zcode-ai) reviewer=bot ;;
    codex-ai) reviewer=me ;;
    *) continue ;;
  esac

  if [ "$reviewer" = bot ]; then last=$(jq -r .bot_review <<< "$pr"); else last=$(jq -r .me_review <<< "$pr"); fi
  [ "$last" = "null" ] && last="1970-01-01T00:00:00Z"
  # já revisado depois do último push -> nada a fazer
  if [[ "$last" > "$last_push" ]]; then continue; fi

  # revisão em andamento (processo vivo)?
  if [ -f "$STATE/inflight-$n" ] && kill -0 "$(cat "$STATE/inflight-$n")" 2>/dev/null; then
    echo "PR #$n ($head): revisão em andamento"; continue
  fi

  if [ "$reviewer" = me ]; then
    echo "PR #$n (codex-ai): aguardando review do ZCode (automação) — notificando humano"
    notify-send -u normal "seo-agent-opencode" "PR #$n (codex-ai) aguardando review do ZCode" 2>/dev/null || true
    continue
  fi

  # limita tentativas por push (reset quando novo push entra)
  stamp_file="$STATE/attempts-$n"
  stamp_push="$(cat "$stamp_file.push" 2>/dev/null || echo none)"
  if [ "$stamp_push" != "$last_push" ]; then echo "$last_push" > "$stamp_file.push"; echo 0 > "$stamp_file"; fi
  attempts=$(cat "$stamp_file" 2>/dev/null || echo 0)
  if [ "$attempts" -ge 3 ]; then
    echo "PR #$n: 3 tentativas sem review publicado; aguardando humano"
    notify-send -u critical "seo-agent-opencode" "PR #$n: Codex falhou 3x — review manual necessário" 2>/dev/null || true
    continue
  fi
  echo $((attempts + 1)) > "$stamp_file"

  CODEX_LOG="$STATE/codex-pr$n-$(date +%s).log"
  echo "PR #$n (zcode-ai): disparando Codex (tentativa $((attempts + 1))) -> $CODEX_LOG"
  GH_TOKEN="$BOT_TOKEN" "$CODEX_BIN" exec --full-auto \
    -c sandbox_workspace_write.network_access=true \
    "Revise o PR #$n do repositorio $REPO (head zcode-ai -> dev-ai). Voce e o ai-codex: siga HANDOFF-CODEX.md e AGENTS.md. Comandos gh ja operam como a conta bot via GH_TOKEN do ambiente - NAO use gh auth switch. Analise com: gh pr diff $n --repo $REPO e gh pr view $n --repo $REPO. Aplique o checklist de review do AGENTS.md. Publique o veredito: gh pr review $n --repo $REPO --approve --body '...' ou --request-changes --body '...', sempre assinando 'Signed-by: ai-codex (GPT-6 Astra Ultra)' com justificativa concreta. Se aprovar, mergeie: gh pr merge $n --repo $REPO --merge. NAO commite nem altere arquivos do repositorio." \
    > "$CODEX_LOG" 2>&1 &
  echo $! > "$STATE/inflight-$n"
done
