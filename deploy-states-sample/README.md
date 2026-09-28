# deploy-states-sample

Workshop sample of how CARE HMIS environments are built and deployed. It uses the
same layout and the same GitHub Actions workflows as our real `auto-deploy-states`
repo. The environments, project IDs, domains, and accounts are **fake**. Nothing
in this folder can deploy anywhere as-is.

The main idea: **this repo contains no application code.** Each environment is a
folder of config. CI reads that config, builds images from the upstream source
repos, and rolls them out to GKE with OpenTofu.

## Layout

```text
env/<environment>/
├── deploy_config.json        # where it deploys: GCP project, WIF, registry, tfvars secret, IaC repo
└── build/
    ├── care/
    │   ├── build_config.json # which backend repo + git ref to build
    │   └── care.env          # docker --build-arg lines (ADDITIONAL_PLUGS)
    └── care_fe/
        ├── build_config.json # which frontend repo + git ref to build
        └── care_fe.env       # copied to .env.local before the frontend build
```

Sample environments:

| Environment       | Ref          | `TF_VAR_env_name` | Plugs                          |
|-------------------|--------------|-------------------|--------------------------------|
| `staging`         | `develop`    | `staging`         | `care_radiology`               |
| `demo-state-hmis` | `production` | `production`      | `care_radiology`, `token_display` |

`production` in the workflow dropdown is not a folder. It expands to every env
whose `tofu.TF_VAR_env_name` is `production`. That is how one click rolls out to
all states.

## Pipeline

```text
PR touching env/**  ──► validate.yaml   JSON syntax, required keys, plug format
                                       (tools/normalize_plugs.py --check)

manual dispatch     ──► build.yaml      for each env × component:
                                         checkout <repo>@<ref>
                                         inject care.env / care_fe.env
                                         docker buildx → Artifact Registry
                                         tag latest-<run_number>, latest
                                       optional: call deploy for a single env

manual dispatch     ──► deploy.yaml     verify tags exist in Artifact Registry
                                       update image tags in tfvars (Secret Manager)
                                       clone IaC repo → tofu init + plan
                                       open GitHub issue with the plan
                                       "approved" comment by an approver → tofu apply
                                       "denied" or 45 min timeout → cancel
```

Auth to GCP is keyless: Workload Identity Federation maps the GitHub OIDC token to
`service_account` (see `.github/actions/gcp-auth`). No JSON keys are stored.

Secrets never live here. `gcp_secret_name` is just a *name*; the tfvars inside
Secret Manager hold DB passwords, etc.

## Exercises

1. **Change a frontend setting.** Edit `REACT_APP_TITLE` in
   `env/staging/build/care_fe/care_fe.env`. Which workflow do you run, and for
   which component? (Answer: build `care_fe` for `staging`, then deploy.)
2. **Add a plug to one state.** Add an entry to `ADDITIONAL_PLUGS` in
   `env/demo-state-hmis/build/care/care.env`, then run:

   ```bash
   python3 tools/normalize_plugs.py --check   # fails if not canonical
   python3 tools/normalize_plugs.py           # rewrites in place
   ```

   Only the backend image changes. Backend, worker, and beat all share it.
3. **Add a new state.** Copy `env/demo-state-hmis` to `env/<new-state>`, change
   every value in `deploy_config.json`, and add the name to the `options` list
   in both `build.yaml` and `deploy.yaml`.
4. **Promote a release.** Staging builds `develop`; states build `production`.
   Promotion is a merge upstream, then a build + deploy with `production`.

## Compared with the local compose stack

| Local (`compose.yaml`)          | Here                                      |
|---------------------------------|-------------------------------------------|
| `ADDITIONAL_PLUGS` in `.env`    | `env/<env>/build/care/care.env`           |
| `frontend.env.production.local` | `env/<env>/build/care_fe/care_fe.env`     |
| `docker compose build`          | `build.yaml` → Artifact Registry          |
| `docker compose up`             | `deploy.yaml` → OpenTofu → GKE            |
| you decide when it runs         | a plan goes into an issue; a human approves the apply |
