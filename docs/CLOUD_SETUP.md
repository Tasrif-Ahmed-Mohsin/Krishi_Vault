# Moving KrishiVault to a Claude cloud session

A cloud session clones this repository from GitHub, so everything it needs must be pushed. Secrets never go into the repository; they go into the cloud environment's settings.

## 1. Connect GitHub

At claude.ai/code, connect GitHub and install the Claude GitHub App on `Tasrif-Ahmed-Mohsin/Krishi_Vault`. Add `muhammadTasin/Mati-Kohon-` too if the cloud session should read Mati Kohon's data.

## 2. Create a cloud environment

In claude.ai/code, open the environment settings (create one named `KrishiVault`).

**Network access:** choose **Custom**, keep the default list, and add these domains one per line:

```
generativelanguage.googleapis.com
texttospeech.googleapis.com
oauth2.googleapis.com
smpp.revesms.com
api.awajdigital.com
market.dam.gov.bd
dam.gov.bd
power.larc.nasa.gov
api.open-meteo.com
download.pytorch.org
```

Choosing **Full** also works, if you prefer not to keep a list.

**Setup script** (installs packages once; the result is cached):

```bash
#!/bin/bash
pip install -r krishivault-pipeline/requirements-cloud.txt
```

## 3. Add the keys

On a Pro or Max plan, add keys that go in a request header (the Gemini key) as **network secrets**, so the session can use them without seeing them. Everything else goes in **Environment variables**, one `KEY=value` per line. Anyone who uses the environment can read its variables, so keep the environment personal.

| Variable | Where the value is on your PC |
|---|---|
| `GEMINI_API_KEY` | `E:\futureisgp\env materials.txt` |
| `GOOGLE_TTS_JSON_B64` | The Google key file `E:\futureisgp\krishivault-pipeline\calltest-510315-452c8ce4219e.json`, base64-encoded (command below) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Type exactly: `/tmp/gcp-tts.json` |
| `SMS_BASE_URL`, `SMS_API_KEY`, `SMS_SECRET_KEY`, `SMS_SENDER_ID` | `E:\nasa-farm\sync-main\.env` (copied from the REVE note in `E:\nasa-farm\awaj`) |
| `SMS_LIVE` | `0` |
| `AWAJ_API_TOKEN`, `AWAJ_SENDER`, `AWAJ_LIVE=0` | Optional: calls are not part of the prototype |

To base64-encode the Google key file and copy it, run this in PowerShell, then paste it after `GOOGLE_TTS_JSON_B64=`:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("E:\futureisgp\krishivault-pipeline\calltest-510315-452c8ce4219e.json")) | Set-Clipboard
```

The repository's SessionStart hook (`.claude/hooks/session-start.sh`) turns it back into `/tmp/gcp-tts.json` at the start of each cloud session.

## 4. Start the session

Start a cloud session on `Tasrif-Ahmed-Mohsin/Krishi_Vault` with the `KrishiVault` environment. A good first message:

> Read CLAUDE.md and docs/HANDOFF.md. Run the tests. Then continue the prototype to-do list in HANDOFF.md, section 10.

## If something fails

- **"Module not found":** run `pip install -r krishivault-pipeline/requirements-cloud.txt`.
- **A request to Gemini, Google or REVE is blocked:** add the domain to the environment's network list, or switch to Full. On 14 October the REVE gateway (`smpp.revesms.com:7790`) closed the connection from a cloud session without answering; if a live SMS fails there, send the first one from a laptop.
- **The SMS or voice keys are not picked up:** the names must be exactly `SMS_API_KEY`, `SMS_SECRET_KEY`, `SMS_SENDER_ID`, `SMS_LIVE`, `GOOGLE_TTS_JSON_B64`, `GOOGLE_APPLICATION_CREDENTIALS` (the Awaj sender may be `AWAJ_SENDER` or `AWAJ_SENDER_NUMBER`). Variables reach only sessions started after the change. On `/call`, the strip under the phone says "SMS: keys set, dry run" once the three SMS keys are in.
- **The Bangla voice fails:** check `GOOGLE_TTS_JSON_B64` is one line with nothing missing, and `GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-tts.json` (the path, not the key file's name). On `/call`, hold the mouse over the "Google voice: off" chip to see why.
- **Gemini says "no answer":** the server log names the reason. Google needs a wait of at least 10 seconds and retires model names; set `GEMINI_MODEL` to a current one if all four defaults fail.
