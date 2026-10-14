#!/usr/bin/env bash
# Runs when a Claude Code session starts. Does nothing on a local machine; in a cloud session it
# 1) writes the Google TTS key file from the GOOGLE_TTS_JSON_B64 environment variable, and
# 2) installs the Python packages if the environment's setup script has not already done it.
set -u
if [ -z "${CLAUDE_CODE_REMOTE_SESSION_ID:-}" ] && [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ -n "${GOOGLE_TTS_JSON_B64:-}" ]; then
  echo "$GOOGLE_TTS_JSON_B64" | base64 -d > /tmp/gcp-tts.json 2>/dev/null && chmod 600 /tmp/gcp-tts.json
fi

REQ="${CLAUDE_PROJECT_DIR:-.}/krishivault-pipeline/requirements-cloud.txt"
if ! python3 -c "import fastapi, google.genai, google.cloud.texttospeech" >/dev/null 2>&1; then
  python3 -m pip install -q -r "$REQ" >/dev/null 2>&1 || echo "KrishiVault: pip install failed; run: pip install -r krishivault-pipeline/requirements-cloud.txt"
fi
exit 0
