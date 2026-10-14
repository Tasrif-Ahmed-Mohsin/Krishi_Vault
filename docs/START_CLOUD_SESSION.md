# Starting a KrishiVault cloud session

Set up the cloud environment once (`docs/CLOUD_SETUP.md`), then start a cloud session on `Tasrif-Ahmed-Mohsin/Krishi_Vault` and paste this as the first message:

---

You are building KrishiVault for an idea competition. First read `CLAUDE.md`, then `docs/HANDOFF.md` (the plan, the prototype scope, what is real and what is not, the to-do list), `docs/PLAN_DETAILS.md` and `docs/DATA_SOURCES.md`.

KrishiVault is a farm business ecosystem, not an information centre. Its five pillars:
1. selling crops for the best value with AI and our partner network;
2. a fertilizer and pesticide supply chain with the right dose, a fair price and on-time delivery;
3. a marketplace for seeds, machinery (to buy or rent) and other agricultural goods;
4. danger alerts for heavy rain, heat, cold, floods, crop disease and price crashes;
5. fair credit instead of dadon.

The farmer's record (কৃষি খাতা) ties them together. Farmers use button phones (voice call, keypad, SMS); officers, cold storages, buyers, dealers, sellers and lenders use web screens. The project must be financially solid (the farmer pays nothing; businesses pay only when they gain), practical, and must reduce financial, crop and sustainability losses.

Data for the prototype is in `krishivault-pipeline/data/reference/mati_kohon/` (a snapshot from the Mati Kohon project). Code to port from Mati Kohon is in `reference/mati_kohon_code/`. The full Mati Kohon project is at https://github.com/muhammadTasin/Mati-Kohon-/tree/feature/crop-loss if you need more.

Now:
1. Install the packages if needed (`pip install -r krishivault-pipeline/requirements-cloud.txt`) and run the tests.
2. Make a new branch, then work through the prototype to-do list in `docs/HANDOFF.md`, section 10, starting with item 1.
3. Keep SMS and calls in dry-run mode unless I say otherwise. Never commit secrets. Do not present demo data as real partners.
4. When an item is done, commit, push the branch, and tell me in plain words what works and how to see it.

---

Later sessions: start with "Read CLAUDE.md and docs/HANDOFF.md, check which to-do items are done (git log), then continue with the next one."
