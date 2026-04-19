---
name: gcp-cloud-run-release-debug
description: Diagnose and repair GitHub Actions release pipelines that deploy to GCP Cloud Run, especially when they use semantic-release, `google-github-actions/auth`, `GCP_CREDENTIALS`, Artifact Registry, Secret Manager, and custom `gcloud run deploy` scripts. Use when a release workflow fails in the deploy job, when Cloud Build or Cloud Run permissions are unclear, when reruns behave differently from new releases, or when you need to decide between fixing IAM and changing the image build path.
---

# GCP Cloud Run Release Debug

Use this skill for repos that release from GitHub Actions to Cloud Run and fail somewhere between semantic-release, image build, and deploy.

## Quick audit

Check these first:

- the workflow file, especially the split between `release` and `deploy`
- the deploy script that builds the image and runs `gcloud run deploy`
- whether auth uses `credentials_json`, workload identity, or both
- which service account is intended to deploy
- the latest failed run and the exact failing step

Useful commands:

```bash
gh run list --workflow=release.yml --limit 5 --json databaseId,attempt,status,conclusion,displayTitle,createdAt,url
gh run view <run-id> --log-failed
gh run view <run-id> --json jobs
```

## Workflow

### 1. Identify the real failure surface

Do not jump straight to IAM guesses.

- Confirm whether the run failed in `release` or `deploy`.
- If `release` succeeded but `deploy` failed, focus on deploy credentials, image build path, and Cloud Run config.
- If the run is an older rerun, confirm whether semantic-release will short-circuit because the version/tag already exists.

Important guardrail:
- Rerunning an old release workflow can be misleading once that version already exists.
- Prefer rerunning only the failed deploy job on the same run when available.
- Otherwise push a fresh `fix:` commit and let semantic-release create a new patch release.

### 2. Confirm the deploy identity

Find the deploy identity from repo code before editing IAM:

- inspect `.github/workflows/*.yml`
- inspect bootstrap or infra scripts such as `scripts/init_release_infra.py`
- inspect the secret or auth stanza used by `google-github-actions/auth`

Common patterns:

- `credentials_json: ${{ secrets.GCP_CREDENTIALS }}`
- workload identity provider + service account email

For JSON-key auth, verify that the secret still corresponds to the intended service account. Stale secrets are common.

### 3. Reproduce the failing cloud command outside GitHub

Reproduce the exact failing `gcloud` command locally before redesigning the pipeline.

For example, if CI fails on:

```bash
gcloud builds submit --project=... --tag=...
```

test that exact call while authenticated as the deploy service account in an isolated `CLOUDSDK_CONFIG`.

Useful checks:

```bash
gcloud projects get-iam-policy <project> --flatten='bindings[].members' --filter='bindings.members:serviceAccount:<sa-email>' --format='table(bindings.role)'
gcloud storage buckets get-iam-policy gs://<bucket> --format=json
gcloud iam service-accounts keys list --iam-account=<sa-email> --project=<project>
```

Bucket access is not the same as `gcloud builds submit` success. Test both.

### 4. Fix the smallest real problem

If the issue is a stale JSON key:

- rotate the key
- update the GitHub secret
- rerun the failed deploy attempt

If the issue is missing IAM:

- grant the smallest role that unblocks the exact command
- re-test under the deploy identity, not under your own account

If `gcloud builds submit` still fails for the deploy service account even after bucket and project roles look correct:

- stop spending time on Cloud Build staging-bucket theory
- change the CI deploy path to build and push the image on the runner
- then deploy with `gcloud run deploy --image ...`

That path is often more reliable for GitHub-hosted runners because it removes the Cloud Build source-upload dependency from CI.

### 5. Patch the deploy flow carefully

Preferred change shape:

- keep the deploy script as the single source of truth
- add a configurable image build backend
- use the new backend only in CI
- leave the existing backend available if it still works elsewhere

Example direction:

- default backend: `cloud-build`
- CI backend: `docker`

Validation target:

- `docker build -t <image> .`
- `docker push <image>`
- `gcloud run deploy ... --image <image>`

### 6. Validate end to end

After patching:

- run a local syntax check on the deploy script
- push a `fix:` commit so semantic-release issues a patch release
- watch the new workflow through both `release` and `deploy`

Useful commands:

```bash
python3 -m py_compile scripts/deploy_cloudrun.py
gh run watch <run-id> --exit-status
gh run view <run-id> --json status,conclusion,jobs
git tag --sort=-version:refname | head
gh release list --limit 3
```

Success means:

- a new tag exists
- the deploy job completes
- Cloud Run receives the new revision

## Failure patterns from this workflow family

### Cloud Build bucket error

Example:

```text
ERROR: (gcloud.builds.submit) The user is forbidden from accessing the bucket [...]
```

Treat this as one of:

- stale or wrong deploy credentials
- missing IAM for the deploy service account
- a Cloud Build path that should be removed from GitHub Actions entirely

Do not assume a single bucket role is enough just because `gcloud storage cp` works.

### Semantic-release already published the version

If logs show that no release will be made because the version already exists:

- do not expect a rerun to behave like a fresh release
- use a new `fix:` commit to create the next patch version

### Manual deploy works but GitHub deploy fails

This usually means one of:

- GitHub is authenticating as a different principal
- the repo secret is stale
- CI is using a build path with different permissions than your manual deploy

Compare:

- local active account
- CI auth mode
- intended deploy service account
- exact failing command

## Close-out checklist

- name the exact failing identity
- name the exact failing command
- say whether the fix was IAM, secret rotation, workflow change, or script change
- report the final successful run URL and released version
