#!/usr/bin/env bash
# Start the local CARE workshop stack in one step.
#
#   ./run-care.sh              build, start and verify CARE
#   ./run-care.sh --demo-data  also load synthetic demo data (local only)
#
# Safe to re-run. It never deletes volumes and never writes a .env file.
set -euo pipefail
cd "$(dirname "$0")"

DEMO_DATA=false
for arg in "$@"; do
  case "$arg" in
    --demo-data) DEMO_DATA=true ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

step "Checking prerequisites"
command -v git >/dev/null || fail "git is not installed"
command -v docker >/dev/null || fail "Docker is not installed"
docker info >/dev/null 2>&1 || fail "Docker is not running. Start Docker Desktop / the Docker daemon and retry."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required (docker compose version)"

step "Fetching CARE sources (git submodules)"
if [ ! -f care/manage.py ] || [ ! -f care_fe/package.json ]; then
  git submodule update --init --depth 1
fi
git submodule status

step "Validating compose.yaml"
docker compose config --quiet

step "Building and starting CARE (first run takes several minutes)"
# Retry once: Docker Desktop occasionally races on first container start.
docker compose up -d --build --wait || { echo "Retrying start..."; docker compose up -d --wait; }

step "Verifying"
curl -fsS http://localhost:9000/ping/ >/dev/null || fail "Backend health check failed: docker compose logs --tail=200 backend"
curl -fsSI http://localhost:4000/ >/dev/null || fail "Frontend not responding: docker compose logs --tail=200 frontend"
docker compose exec -T backend python manage.py check
docker compose ps

if [ "$DEMO_DATA" = true ]; then
  step "Loading synthetic demo data"
  docker compose exec -T backend python -m pip install -q --target /tmp/care-fixtures-deps 'Faker==38.2.0'
  docker compose exec -T -e PYTHONPATH=/tmp/care-fixtures-deps \
    -e 'DJANGO_ALLOWED_HOSTS=["localhost","127.0.0.1","backend","testserver"]' \
    backend python manage.py load_fixtures
fi

cat <<'EOF'

CARE is running.
  Frontend:        http://localhost:4000
  Backend API:     http://localhost:9000
  Storage console: http://localhost:9001

Stop (keeps data):  docker compose down
EOF
