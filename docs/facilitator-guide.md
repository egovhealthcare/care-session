# Facilitator guide

## Session outcome

Participants should leave able to:

1. explain the CARE frontend, backend, and dependency roles;
2. distinguish the two CARE application images;
3. build, run, and verify a local instance;
4. demonstrate that a synthetic record and file can be saved and retrieved;
5. perform a routine health check and diagnose a prepared failure;
6. choose a hosting model, identify compatible dependencies, and assign operators;
7. plan a release and recovery, then make an evidence-based readiness decision.

The final artifact is one completed [operator worksheet](operator-worksheet.md) per team; the [readiness checklist](readiness-checklist.md) is a separate real-deployment gate.

## Teaching sequence

Use this order:

```text
Understand CARE
  → Build the two CARE images
  → Run and verify locally
  → Practice an operator check, troubleshooting and data preservation
  → Choose a hosting model and assign owners
  → Decide readiness; show Kubernetes/GCP only as optional examples
```

Do not introduce Kubernetes or managed services before participants can explain the local system. No one platform is required to host CARE. Do not describe a current production environment in the participant-facing deck.

"Local" means a host controlled for development or training. It could be a workstation, VM, or server. CARE can run without Docker, but that requires the operator to install and manage the language runtimes, dependency services, process startup, and ports on the host. This workshop uses Docker for repeatability and isolation.

## Suggested 90-minute workshop

| Time | Activity |
|---:|---|
| 0–10 min | Start with CARE in a local environment and explain why the workshop uses Docker |
| 10–20 min | Explain the two CARE images and their build-time configuration |
| 20–30 min | Prepare the repositories and inspect the Compose roles |
| 30–45 min | Build and start the stack; inspect startup order |
| 45–58 min | Verify health and complete a synthetic workflow |
| 58–68 min | Perform the daily check, inspect logs, and diagnose one prepared failure |
| 68–73 min | Stop and restart safely; verify the synthetic record and file persist |
| 73–80 min | Choose a hosting model and name owners using the operator worksheet |
| 80–87 min | Plan a release, rollback, restore test, and readiness evidence |
| 87–90 min | Record the decision and unanswered critical checks |

For a 60-minute delivery, prepare a running stack in advance and demonstrate the build command without waiting for a clean build.

## The two CARE images

CARE has two application images:

| Image | Source repository | Build inputs | Runtime responsibility |
|---|---|---|---|
| Frontend | `ohcnetwork/care_fe` | Frontend `REACT_*` build variables | Nginx serves the generated static files |
| Backend | `ohcnetwork/care` | `ADDITIONAL_PLUGS` build argument | API, Celery worker, and Celery Beat |

The local database, S3-compatible storage, and cache/task broker are dependencies. Do not describe them as CARE application images.

### Frontend explanation

The frontend Dockerfile has two stages:

1. Node installs dependencies and runs the frontend build.
2. The final Nginx stage copies and serves the generated HTML, JavaScript, and CSS.

The build reads values from `frontend.env.production.local`, which the frontend build copies into the image. `REACT_CARE_API_URL` must be the URL reachable by the participant's browser. In the workshop it is `http://localhost:9000`; an internal Compose hostname would not work in the browser.

A frontend build-variable change requires a new frontend image.

### Backend explanation

The backend Dockerfile receives `ADDITIONAL_PLUGS` during the image build. The build parses the JSON list, downloads the selected plug packages, and installs them into the image.

API, worker, and Beat run the same backend image with different entry points. They must contain the same plug set. Changing the plug list requires a new backend image.

Do not place secret values in `ADDITIONAL_PLUGS`. Deliver secrets through the runtime secret mechanism.

## Demonstration sequence

1. Display `docs/architecture.svg`.
2. Ask participants to identify the two CARE images and the supporting dependency roles.
3. Explain the frontend and backend image builds.
4. Run `docker compose config --services`.
5. Run `docker compose up -d --build --wait`.
6. Run `docker compose ps -a`.
7. Show that Beat becomes healthy after migrations and synchronization.
8. Verify frontend, backend, and Django checks.
9. Follow the README's local fixture preparation (temporary Faker install and `testserver` host override), then load fixtures and use only synthetic data.
10. Complete one synthetic workflow and inspect the relevant health and log evidence.
11. Perform the operator check and diagnose a prepared failure from the first failing dependency upward.
12. Stop with `docker compose down`, restart, and check that synthetic data remains; never reset volumes in the exercise.
13. Use `docs/operator-worksheet.md` to assign hosting, release, monitoring and recovery owners.
14. If the audience is planning GCP, use `docs/local-to-gcp.md` as a *platform example*; validate storage and Celery broker compatibility separately.
15. Review `docs/readiness-checklist.md` as a gate for any real deployment, not a lab pass mark.

## Questions participants should answer

- Which image produces the browser application?
- When is the backend API URL added to the frontend?
- Why does changing a frontend build variable require a rebuild?
- Why do API, worker, and Beat use the same backend image?
- When are backend plugs installed?
- Which startup operations does Beat perform?
- Which dependency stores structured records?
- Which dependency stores files through the S3 API?
- Which dependency transports asynchronous tasks?
- What evidence shows the application is healthy?
- Who owns each dependency, alert and recovery action on the team's chosen platform?
- What evidence shows data survives a restart, and what additional test proves a backup can be restored?
- Which controls are still required before a real instance?

## Presenter prompts by section

### Local architecture

Say: "We first care about responsibilities, not products. CARE needs a database, S3-compatible storage, and a cache and task broker."

Ask participants to distinguish CARE application images from supporting dependencies.

### Build

Say: "CARE itself produces two images. The frontend image contains static files served by Nginx. The backend image runs three process roles."

Show the frontend build environment and the backend plug list separately.

### Verification

Ask for evidence, not impressions. A running container does not prove that login, file storage, or background work succeeds.

### Hosting decision

Say: "The CARE responsibilities stay the same. Your team decides where they run and who maintains each one."

Only when relevant, use the simple Kubernetes architecture and GCP mapping as examples, not the required destination. The frontend API URL is baked in at build time; do not imply a runtime ConfigMap changes it.

For a GCP example, discuss candidate mappings and compatibility checks:

```text
Local database        → Cloud SQL
S3-compatible storage → GCS buckets
Local cache/broker    → compatible managed broker after Celery testing
Frontend/backend      → independent process roles on the selected host
Local images          → pinned artifacts in a trusted registry
```

### Readiness decision

Require each team to state its decision, strongest evidence, named operator, and largest open risk. Treat an unknown critical gate as no-go until evidence exists.

## Build-time and runtime configuration

Keep this distinction visible throughout the workshop:

| Build-time input | Effect |
|---|---|
| Frontend `REACT_*` variables | Baked into the static frontend files |
| `REACT_CARE_API_URL` | Tells the browser where to reach the backend API |
| Backend `ADDITIONAL_PLUGS` | Selects and installs plugs into the backend image |

Runtime backend configuration includes database, S3, cache/broker, secrets, and integration endpoints. Runtime secret values must not be embedded in either application image.

## Demo fallback plan

If a clean build is too slow or fails:

1. preserve the participant's error output;
2. move the pair to a working machine or prebuilt facilitator stack;
3. continue health checks, application verification, and evidence collection;
4. return to the build failure during troubleshooting time.

Do not let a slow image download consume the architecture and verification portions of the session.

## Safety boundaries

- Use only local workshop credentials.
- Use only synthetic fixture data.
- Do not connect to production databases, buckets, queues, or APIs.
- Do not paste real secrets into `.env` or plug configuration.
- Do not present the Compose file as a production deployment pattern.
- Confirm before running `docker compose down -v`; it deletes local state.
