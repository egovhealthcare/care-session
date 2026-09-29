# AGENTS.md

## Purpose

This repository is a training environment for running CARE locally with Docker Compose. Agents working here must preserve the small, understandable architecture and must not turn it into a production deployment template.

## Safety rules

- Use only local workshop credentials from `.env.example`.
- Use only synthetic fixture data.
- Never connect this stack to production databases, buckets, Redis instances, APIs, or credentials.
- Never read, print, commit, or overwrite a user's existing `.env`.
- Never run `docker compose down -v` unless the user explicitly requests deletion of local data.
- Do not commit the cloned `care/` or `care_fe/` repositories.
- Keep `deploy-states-sample/` synthetic: fake project IDs, domains, accounts and secrets only. Never copy real values from `auto-deploy-states` or any live environment.
- Do not add a separate migration or init service. The current CARE `celery_beat.sh` performs migrations and synchronization before starting Beat.

## Required local layout

```text
care-session/
├── compose.yaml
├── .env.example
├── frontend.env.production.local
├── docs/                 # workshop docs + the Session 3 deck (GitHub Pages root)
├── deploy-states-sample/ # synthetic copy of the auto-deploy-states layout and workflows
├── care/       # cloned from ohcnetwork/care develop
└── care_fe/    # cloned from ohcnetwork/care_fe develop
```

## Preflight

Run these checks before changing or starting the stack:

```bash
docker info
docker compose version
test -f compose.yaml
test -d care/.git
test -d care_fe/.git
```

If either source repository is missing, clone it:

```bash
git clone --depth 1 --branch develop https://github.com/ohcnetwork/care.git
git clone --depth 1 --branch develop https://github.com/ohcnetwork/care_fe.git
```

If `.env` is missing, create it without overwriting an existing file:

```bash
test -f .env || cp .env.example .env
```

Configure the frontend build:

```bash
cp frontend.env.production.local care_fe/.env.production.local
```

## Validate before starting

```bash
docker compose config --quiet
docker compose config --services
```

The service list must contain exactly these runtime roles:

- `db`
- `redis`
- `silo`
- `beat`
- `backend`
- `worker`
- `frontend`

## Build and start

```bash
docker compose up -d --build --wait
```

The backend, worker, and Beat share the `care-local-backend` image. Beat must become healthy before the backend and worker start. Its startup script performs database migrations, compiles messages, synchronizes permissions and value sets, writes `/tmp/healthy`, and then starts Celery Beat.

## Verify

Do not report success until every check has been run:

```bash
docker compose ps -a
curl -f http://localhost:9000/ping/
curl -I http://localhost:4000/
docker compose exec backend python manage.py check
```

Confirm:

- PostgreSQL, Redis, and Silo are healthy.
- Beat is healthy.
- Backend, worker, and frontend are running.
- Backend health returns success.
- Frontend returns an HTTP response.
- Django system checks pass.

If fixture data is required:

```bash
docker compose exec backend python -m pip install --target /tmp/care-fixtures-deps 'Faker==38.2.0'
docker compose exec -e PYTHONPATH=/tmp/care-fixtures-deps \
  -e 'DJANGO_ALLOWED_HOSTS=["localhost","127.0.0.1","backend","testserver"]' \
  backend python manage.py load_fixtures
```

Faker is a development-only upstream dependency; this local install is lost when the backend container is recreated. Never load fixtures in a real instance.

## Troubleshooting order

Inspect dependencies from the bottom up:

```bash
docker compose logs --tail=200 db
docker compose logs --tail=200 redis
docker compose logs --tail=200 silo
docker compose logs --tail=200 beat
docker compose logs --tail=200 backend
docker compose logs --tail=200 worker
docker compose logs --tail=200 frontend
```

Fix the first failing dependency before changing downstream services.

## Plugs

Backend plugs are installed at image build time through `ADDITIONAL_PLUGS`. Keep `ADDITIONAL_PLUGS=[]` unless the user specifies a plug. When adding a plug:

- Use the exact package documented by the plug.
- Pin a release or commit.
- Keep secrets out of the JSON value.
- Rebuild all backend roles:

```bash
docker compose build --no-cache backend worker beat
docker compose up -d --wait
```

## Stop behavior

Preserve data by default:

```bash
docker compose down
```

Only with explicit user approval, delete all local volumes:

```bash
docker compose down -v
```

## Documentation consistency

When changing a component or startup dependency, update all of:

- `compose.yaml`
- `README.md`
- `docs/architecture.md`
- `docs/architecture.svg`
- `docs/architecture.html`
- `docs/facilitator-guide.md`
- `docs/readiness-checklist.md`
- `docs/local-to-gcp.md` when the production mapping changes
- `docs/index.html` (the deck) when setup commands, ports, services or fixture steps change — slide "Run CARE on your own machine" repeats them

## Presentation

The CARE Fundamentals Webinar Series · Session 3 deck is a single file, `docs/index.html`, published by GitHub Pages from `main` / `docs` at <https://egovhealthcare.github.io/care-session/>. There is no build step and no Actions workflow: pushing to `main` deploys it. `#N` jumps to slide N.

- `docs/infra-session.html` is a redirect for the old URL. Keep it.
- Images it uses: `docs/tech-stack-runtime-diagram-v6.svg` (and `.png` export) and `docs/celery-worker-hpa-sample.png`. Remove old diagram versions instead of keeping drafts.
- Style follows ohc.network: Bricolage Grotesque headings, Switzer body, forest green / lime palette. Reuse the existing CSS classes; do not add a second template.
- Content rules:
  - Only facts verified in `care`, `care_fe`, `gcp_template`, `deploy-states-sample`, or live read-only measurements.
  - No state names, project IDs, cluster names or other instance identifiers. Refer to instances generically.
  - Plain vCPU / GB, not GCP machine types or Cloud SQL tier names.
  - Costs are estimates from Google list prices; say so.
  - File and repo references are plain hyperlinks (new tab), no emojis. Do not link private repos.
- After editing, render each changed slide and check nothing overlaps the footer before pushing.
