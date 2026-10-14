# The conversation screen (`/call`)

A farmer's phone call to KrishiVault, played in a web browser. A teammate speaks (or presses keys) as the farmer; the screen shows what was heard, what KrishiVault understood, the decision in taka, and the reply in Bangla, read aloud.

It uses the same steps the real phone line will use: speech to text → KrishiVault's Bangla number reader (and Gemini, if switched on) → questions for anything missing → every number read back for a keypad "yes" → the decision engine → the number check → the Bangla voice.

## What a call looks like

1. **Greeting and menu:** "১ ফসল বেচা, ২ সার ও কীটনাশক, ৩ বীজ ও যন্ত্রপাতি, ৯ কর্মকর্তা ফোন করবেন", or just speak.
2. **Questions,** only for what the farmer has not said: how many maunds, how much cash is needed and within how many days, the trader's offer, any dadon. One sentence can answer several: "হামার ৮০ মণ আলু উঠছে, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে..."
3. **Read-back:** "আপনি বললেন: ৮০ মণ আলু। ৪ দিনের মধ্যে ২৫,০০০ টাকা দরকার... ঠিক হলে ১, ভুল হলে ২ চাপুন।" A spoken correction ("না, ৯০ মণ") is read back again.
4. **Advice in taka** from the decision engine: sell now, sell part, store, or sell as a group, with the second-best option and its amount.
5. **One action to press:** send the lot to buyers, a cold-storage request, or join a group lot. It is saved for the partner screens (to-do item 6), with a request number.
6. **Every call ends with** "১ = আবার শুনুন, ৯ = কর্মকর্তা ফোন করবেন". Two misunderstandings in a row also lead to the officer callback.

Below the phone: **SMS me** sends the receipt and **Call me** has KrishiVault call the number and read the advice (Awaj). Both are **dry runs** unless the server has `SMS_LIVE=1` or `AWAJ_LIVE=1`: the screen then shows the exact request that would go out.

## What is real and what is demo

| Part | Status |
|---|---|
| Keypad call, menu, questions, read-back, officer callback | Works |
| Bangla number reader: digits and words (পঞ্চাশ, বিশ হাজার, দেড় লাখ), মণ, বস্তা, কেজি, northern forms (টেকা, নাগবে), dadon | Works (tested) |
| Decision in taka | The existing decision engine |
| Number check: Gemini may reword the advice but not change, add or drop a number | Works (tested with a stand-in for Gemini) |
| Speech to text | The browser's own (Chrome). Needs HTTPS, or `localhost` |
| Gemini understanding and rewording | Switches on when `GEMINI_API_KEY` is set. **Not yet tried with a real key** |
| Google Bangla voice | Switches on when the Google key is set; otherwise the phone's own Bangla voice, if it has one. **Not yet tried in this screen with a real key** |
| SMS and calls | Dry run by default (REVE and Awaj, ported from Mati Kohon) |
| Today's price | The farmer's trader offer; if he does not know it, a **demo** buyer's price |
| Price in a month | The **seasonal pattern** in `config/settings.py`. Not a trained forecast; the screen says so |
| Buyers, cold storage, neighbours for a group lot | **Demo data** from the sample database. Clearly fictional; the screen says "DEMO DATA" |

## How to open it

### On a laptop (simplest)

```bash
cd krishivault-pipeline
uvicorn src.main:app --port 8000
```

Open **http://localhost:8000/call** in Chrome. The microphone works on `localhost`.

### On a phone (needs HTTPS for the microphone)

Run the server as above, then make a temporary HTTPS address for it with Cloudflare's free quick tunnel (no account needed):

```bash
# Windows, once:  winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```

It prints an address like `https://something.trycloudflare.com`. Open that address followed by `/call` in **Chrome on Android**.

- Anyone with the address can use the screen while the tunnel runs. Keep `SMS_LIVE=0` and `AWAJ_LIVE=0` while it is open, and stop the tunnel (Ctrl+C) after the demo.
- Without HTTPS the screen still works by typing and with the keypad; only the microphone needs it.
- Other browsers may have no Bangla speech recognition: use the typing box, the "Try" buttons, or the keypad.

### Switching on Gemini and the Google voice

Set these before starting the server (names are in `krishivault-pipeline/.env.example`; values never go in the repository):

- `GEMINI_API_KEY`: Gemini understanding and rewording. `GEMINI_MODEL` can name the model.
- `GOOGLE_APPLICATION_CREDENTIALS`: the Google key file, for the Bangla voice. `TTS_LANGUAGE` can force `bn-BD` or `bn-IN`; otherwise `bn-BD` is tried first.

The strip under the phone shows what is on: speech to text, Gemini, the Google voice, SMS and calls (dry run or live).

## Where the code is

- `krishivault-pipeline/static/call.html`: the screen.
- `krishivault-pipeline/src/voice/conversation.py`: the call, step by step (also for the future phone line).
- `src/voice/understanding.py`, `intent_parser.py`, `bangla_numbers.py`: understanding the farmer.
- `src/voice/number_lock.py`: the number check. `src/voice/gemini.py`: the Gemini client.
- `src/engine/market_inputs.py`: the seasonal price pattern and the demo partners.
- `src/notify/sms.py`, `src/notify/awaj.py`: SMS and calls. `src/events.py`: actions saved for partner screens.
- API: `POST /api/call/turn`, `POST /api/voice/speak`, `POST /api/call/sms`, `POST /api/call/ring`, `GET /api/call/status`, `GET /api/events`.
