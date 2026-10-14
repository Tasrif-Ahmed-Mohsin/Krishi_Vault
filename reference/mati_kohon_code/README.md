# Code from the Mati Kohon project, for reference

Copied on 14 October 2026 from `github.com/muhammadTasin/Mati-Kohon-`, branch `feature/crop-loss`, commit `81704cb`. These files are **not part of KrishiVault's build**: read them and port what KrishiVault needs to Python in `krishivault-pipeline/`. See `docs/DATA_SOURCES.md` for what each file does.

The TypeScript files run under Node with `--experimental-strip-types` in Mati Kohon. Keys they read (`SMS_*`, `AWAJ_*`, `GOOGLE_TTS_CREDENTIALS`) come from environment variables; KrishiVault uses the names in `krishivault-pipeline/.env.example`.
