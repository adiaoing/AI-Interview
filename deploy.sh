#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Friday — Production Deployment Script
#
# Deploys:
#   1. Backend  → GCP Cloud Run  (Docker build + push + deploy)
#   2. Frontend → Vercel         (vercel --prod)
#
# Prerequisites:
#   - gcloud CLI authenticated: gcloud auth login && gcloud auth configure-docker
#   - vercel CLI authenticated: vercel login
#   - backend/.env populated
#   - frontend/.env.local populated
#
# Usage:
#   bash scripts/deploy.sh                  # deploy both
#   bash scripts/deploy.sh --backend-only   # backend only
#   bash scripts/deploy.sh --frontend-only  # frontend only
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

log()  { echo -e "\n${BOLD}▸ $*${RESET}"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET} $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*"; exit 1; }
dim()  { echo -e "  ${DIM}$*${RESET}"; }

# ── Parse flags ───────────────────────────────────────────────────────────────
DEPLOY_BACKEND=true
DEPLOY_FRONTEND=true

for arg in "$@"; do
  case $arg in
    --backend-only)  DEPLOY_FRONTEND=false ;;
    --frontend-only) DEPLOY_BACKEND=false  ;;
  esac
done

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       Friday — Production Deploy         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Load or prompt GCP config ─────────────────────────────────────────────────
DEPLOY_CONFIG="$ROOT/.deploy-config"

load_or_prompt_config() {
  if [[ -f "$DEPLOY_CONFIG" ]]; then
    # shellcheck source=/dev/null
    source "$DEPLOY_CONFIG"
    ok "Loaded deploy config from .deploy-config"
  else
    echo -e "  ${YELLOW}First-time deploy setup${RESET}"
    echo ""
    echo -ne "  ${CYAN}?${RESET} GCP Project ID: "
    read -r GCP_PROJECT_ID
    echo -ne "  ${CYAN}?${RESET} GCP Region (e.g. us-central1): "
    read -r GCP_REGION
    GCP_REGION="${GCP_REGION:-us-central1}"
    echo -ne "  ${CYAN}?${RESET} Cloud Run service name: "
    read -r CLOUD_RUN_SERVICE
    CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-friday-backend}"
    echo -ne "  ${CYAN}?${RESET} Vercel project name (or leave blank to detect): "
    read -r VERCEL_PROJECT

    cat > "$DEPLOY_CONFIG" <<EOF
GCP_PROJECT_ID="${GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION}"
CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE}"
VERCEL_PROJECT="${VERCEL_PROJECT}"
EOF
    ok "Saved deploy config to .deploy-config"
  fi

  # Derived values
  IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/friday-backend"
}

# ── Deploy backend to GCP Cloud Run ──────────────────────────────────────────
deploy_backend() {
  log "Deploying backend to GCP Cloud Run"

  # Check prerequisites
  command -v gcloud &>/dev/null || err "gcloud CLI not found. Install: https://cloud.google.com/sdk"
  command -v docker  &>/dev/null || err "docker not found. Install: https://docs.docker.com/get-docker/"

  # Verify gcloud auth
  if ! gcloud auth print-access-token &>/dev/null; then
    err "Not authenticated with gcloud. Run: gcloud auth login"
  fi
  ok "gcloud authenticated"

  # Load .env for secrets
  if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    err "backend/.env not found. Run: bash setup.sh"
  fi
  # shellcheck source=/dev/null
  source "$BACKEND_DIR/.env"

  # Validate required vars
  local required_vars=(ANTHROPIC_API_KEY ELEVENLABS_API_KEY OPENAI_API_KEY SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY)
  for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      err "backend/.env is missing: $var"
    fi
  done

  # Build Docker image
  log "Building Docker image: $IMAGE_NAME"
  docker build -t "$IMAGE_NAME" "$BACKEND_DIR"
  ok "Docker image built"

  # Push to Google Container Registry
  log "Pushing image to GCR"
  gcloud auth configure-docker --quiet 2>/dev/null
  docker push "$IMAGE_NAME"
  ok "Image pushed to $IMAGE_NAME"

  # Build env-vars string for Cloud Run
  CLOUD_RUN_CORS="${CORS_ORIGINS:-https://friday.vercel.app}"
  ENV_VARS="ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
  ENV_VARS+=",ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}"
  ENV_VARS+=",OPENAI_API_KEY=${OPENAI_API_KEY}"
  ENV_VARS+=",SUPABASE_URL=${SUPABASE_URL}"
  ENV_VARS+=",SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}"
  ENV_VARS+=",CORS_ORIGINS=${CLOUD_RUN_CORS}"
  ENV_VARS+=",MAX_TURNS=${MAX_TURNS:-8}"

  # Deploy to Cloud Run
  log "Deploying to Cloud Run (${GCP_REGION})"
  gcloud run deploy "$CLOUD_RUN_SERVICE" \
    --image "$IMAGE_NAME" \
    --platform managed \
    --region "$GCP_REGION" \
    --project "$GCP_PROJECT_ID" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "$ENV_VARS" \
    --quiet

  # Get the deployed URL
  BACKEND_URL=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
    --platform managed \
    --region "$GCP_REGION" \
    --project "$GCP_PROJECT_ID" \
    --format "value(status.url)" 2>/dev/null || echo "")

  echo ""
  ok "Backend deployed!"
  if [[ -n "$BACKEND_URL" ]]; then
    echo -e "  ${CYAN}URL:${RESET} $BACKEND_URL"
    echo -e "  ${DIM}Update NEXT_PUBLIC_API_URL in Vercel to: $BACKEND_URL${RESET}"
    # Save for frontend deploy step
    echo "BACKEND_CLOUD_RUN_URL=$BACKEND_URL" >> "$DEPLOY_CONFIG"
  fi
}

# ── Deploy frontend to Vercel ─────────────────────────────────────────────────
deploy_frontend() {
  log "Deploying frontend to Vercel"

  command -v vercel &>/dev/null || err "vercel CLI not found. Install: npm i -g vercel"

  # Verify vercel auth
  if ! vercel whoami &>/dev/null; then
    err "Not authenticated with Vercel. Run: vercel login"
  fi
  ok "vercel authenticated ($(vercel whoami 2>/dev/null))"

  # Check for Cloud Run URL from previous step
  if [[ -f "$DEPLOY_CONFIG" ]]; then
    source "$DEPLOY_CONFIG"
  fi
  if [[ -n "${BACKEND_CLOUD_RUN_URL:-}" ]]; then
    warn "Remember to set NEXT_PUBLIC_API_URL=${BACKEND_CLOUD_RUN_URL} in Vercel dashboard"
  fi

  # Deploy
  log "Running vercel --prod"
  local VERCEL_ARGS="--prod --yes"
  if [[ -n "${VERCEL_PROJECT:-}" ]]; then
    VERCEL_ARGS="$VERCEL_ARGS --name $VERCEL_PROJECT"
  fi

  cd "$FRONTEND_DIR"
  # shellcheck disable=SC2086
  DEPLOYED_URL=$(vercel $VERCEL_ARGS 2>&1 | tee /dev/stderr | grep -E "https://.*\.vercel\.app" | tail -1 || echo "")

  echo ""
  ok "Frontend deployed to Vercel!"
  if [[ -n "$DEPLOYED_URL" ]]; then
    echo -e "  ${GREEN}URL:${RESET} $DEPLOYED_URL"
  fi
  cd "$ROOT"
}

# ── Run ───────────────────────────────────────────────────────────────────────
load_or_prompt_config

if [[ "$DEPLOY_BACKEND" == "true" ]]; then
  deploy_backend
fi

if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
  deploy_frontend
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         Deployment complete! 🚀          ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

if [[ "$DEPLOY_BACKEND" == "true" && -n "${BACKEND_CLOUD_RUN_URL:-}" ]]; then
  echo -e "  ${CYAN}Backend${RESET}  → $BACKEND_CLOUD_RUN_URL"
fi
echo -e "  ${GREEN}Frontend${RESET} → Vercel dashboard for URL"
echo -e "  ${DIM}Next: set NEXT_PUBLIC_API_URL in Vercel environment variables${RESET}"
echo ""
