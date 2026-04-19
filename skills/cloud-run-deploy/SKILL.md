---
name: cloud-run-deploy
description: Deploy a repo to Google Cloud Run when the project already has a scripted deploy path such as `scripts/deploy_cloudrun.py` or equivalent. Use when the user asks to build and deploy a Cloud Run service, redeploy an existing GCP service, push a repo live on Cloud Run, or verify a Cloud Run rollout using the repo's own deploy flow.
---

# Cloud Run Deploy

Use this skill for repos that already know how they want to deploy to Cloud Run. Prefer the repo's documented deploy script and live service config over ad hoc `gcloud run deploy` flags.

## Workflow

1. Read the repo deploy docs first.
   Check `README.md`, `docs/operators/*deploy*`, `docs/builders/*environment*`, and deployment scripts under `scripts/`.

2. Locate the deploy entrypoint.
   Prefer repo helpers such as:
   - `scripts/deploy_cloudrun.py`
   - `npm run deploy:cloudrun`
   - `make deploy`

3. Check current shell config before inventing values.
   Inspect:
   - `env | rg '^(GCP_|CLOUD_RUN_|ONTRANSLATE_|BABEL_COPY_)='`
   - `gcloud config get-value project`
   - `gcloud auth list --filter=status:ACTIVE`

4. If required deploy env vars are missing, infer them from the live service.
   Use the existing deployed service as the source of truth:
   - `gcloud run services list --region=<region> --project=<project>`
   - `gcloud run services describe <service> --region=<region> --project=<project> --format=json`

   Extract:
   - service name
   - region
   - runtime service account
   - image repository shape
   - current app env vars
   - current secret-backed env vars
   - current concurrency, memory, timeout, min instances

   Reuse the live config unless the repo docs or user request says otherwise.

5. Run the repo deploy helper with explicit env.
   Use a single `env ... <deploy command>` invocation so the deploy script receives the full config.

6. Wait for build and rollout completion.
   If the deploy helper already waits, stay attached until it finishes. If it exits early, follow with:
   - `gcloud builds describe <build-id>`
   - `gcloud run services describe <service>`

7. Verify the deployed revision.
   Check:
   - latest ready revision name
   - image tag/digest
   - service URL
   - app health endpoint

## Command Pattern

When the repo uses `scripts/deploy_cloudrun.py`, the common pattern is:

```bash
env \
  GCP_PROJECT_ID=... \
  GCP_REGION=... \
  GCP_ARTIFACT_REPOSITORY=... \
  CLOUD_RUN_SERVICE=... \
  CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT=... \
  <app env vars> \
  <deployment env vars> \
  python3 scripts/deploy_cloudrun.py --version <tag-or-commit>
```

Prefer the current commit SHA for manual deploy tags unless the repo requires SemVer or the user asked for a specific version.

## Verification

After deploy, report:
   - deployed revision
   - image tag
   - service URL
   - health payload

Useful checks:

```bash
gcloud run services describe <service> --region=<region> --project=<project> --format='value(status.latestReadyRevisionName,spec.template.spec.containers[0].image)'
```

```bash
curl -fsSL https://<service-url>/api/health
```

If the repo deploy helper already performs a healthcheck, still summarize the returned payload.

## Failure Shields

- Do not guess missing deploy variables when the live service can tell you.
- Do not replace the repo deploy helper with a raw `gcloud run deploy` unless the helper is broken or absent.
- Do not silently switch service names or regions; confirm them from docs or `gcloud`.
- If Cloud Build fails, quote the concrete failing line and identify whether it is:
  - Dockerfile build failure
  - package/toolchain failure
  - deploy script env mismatch
  - rollout failure after image build
- If you changed the Dockerfile and the deploy now fails in Cloud Build, fix the image or roll back the risky container change before retrying.
- Keep commits atomic during deploy debugging. Separate runtime error-surfacing fixes from speculative image optimizations.
