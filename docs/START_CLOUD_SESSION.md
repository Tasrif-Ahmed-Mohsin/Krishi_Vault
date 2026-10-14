# Starting a KrishiVault cloud session

Set up the cloud environment once (`docs/CLOUD_SETUP.md`), then start a cloud session on `Tasrif-Ahmed-Mohsin/Krishi_Vault` and paste this as the first message:

---

You are building KrishiVault for an idea competition. First read `CLAUDE.md`, then `docs/HANDOFF.md` (the plan, the prototype scope, what is real and what is not, the to-do list), `docs/PLAN_DETAILS.md`, `docs/DATA_SOURCES.md` and `docs/SCREENS.md`.

KrishiVault focuses on potato after the harvest: "store or sell, and until when?" Its seven parts: production and price prediction with ranges; the storage and selling-time engine (sell now, store longer, or sell part and store the rest, after the flat ৳250-a-sack rent, losses, transport and interest); market access (buyers ranked by money in the farmer's hand); crop-backed bank loans (KrishiVault verifies and connects, the bank lends); export market intelligence; group storage; and a profit calculator.

Farmers use button phones (voice call, keypad, SMS); in the prototype the call is previewed in the browser (`/call`) and SMS can be sent. Helpers, cold storages, banks, buyers and exporters use the dashboard (`/`). The farmer pays nothing; partners pay only when they gain. All partners in the prototype are demo data.

Now:
1. Install the packages if needed (`pip install -r krishivault-pipeline/requirements-cloud.txt`) and run the tests.
2. Make a new branch, then work through the prototype to-do list in `docs/HANDOFF.md`, section 10, starting with the first item not done.
3. Keep SMS in dry-run mode unless I say otherwise. Never commit secrets. Do not present demo data as real partners.
4. When an item is done, commit, push the branch, and tell me in plain words what works and how to see it.

---

Later sessions: start with "Read CLAUDE.md and docs/HANDOFF.md, check which to-do items are done (git log), then continue with the next one."
