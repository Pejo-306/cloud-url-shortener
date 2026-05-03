# TEMPORARY Placeholder Cloud Functions (GCP wiring only)

These directories are **not** the production backend. They exist so you can zip and upload sources that match Terraform’s `entry_point` names and GCS object names (`shorten.zip`, `redirect.zip`, `warm.zip` under `{app_env}/cloud-functions/`).

- [`functions/shorten/`](functions/shorten/) — HTTP `shorten_url` callable; returns a hardcoded JSON body matching OpenAPI `ShortenSuccessResponse`, plus CORS headers / `OPTIONS` → `204`.
- [`functions/redirect/`](functions/redirect/) — HTTP `redirect_url` callable; returns `302` with `Location: https://example.com` and `{}` body (OpenAPI `RedirectSuccessEmptyBody`).
- [`functions/warm/`](functions/warm/) — CloudEvent `warm_appconfig_cache` stub for Eventarc GCS `object.finalized` wiring.

Each folder’s `requirements.txt` lists `functions-framework` for **Cloud Build** when deploying the function zip; it does not change your local `backend/` Python environment.

Change the wiring in templates + remove these once we add real backend function implementations in backend/.
