"""
Safety for every test run: nothing real is sent, whatever the local .env says.

A laptop's .env may switch on live SMS and live phone calls (SMS_LIVE=1, VOICEBLAST_LIVE=1). The app
reads .env without overriding what is already set, so setting the switches here, before the app is
imported, keeps every test a dry run: no SMS is billed and no real phone rings.
"""

import os

for _switch in ("SMS_LIVE", "VOICEBLAST_LIVE", "BROADCAST_LIVE", "AWAJ_LIVE"):
    os.environ[_switch] = "0"
