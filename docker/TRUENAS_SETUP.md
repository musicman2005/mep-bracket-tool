# TrueNAS SCALE deployment (Docker Compose)

This guide assumes you already run Docker-based apps on TrueNAS SCALE and have a dataset for app data.

## 1) Create datasets (recommended)
Create a dataset such as:
- `tank/apps/mep-bracket/`
  - `db/`
  - `pdfs/`
  - `config/` (optional)

You can do this in **Storage → Datasets**.

## 2) Copy the repo onto TrueNAS
- Option A: `git clone` into a dataset (best)
- Option B: upload the zip and extract into the dataset

Example path:
`/mnt/tank/apps/mep-bracket/mep-bracket-tool/`

## 3) Edit environment
Copy `.env.example` to `.env` and set:
- POSTGRES_PASSWORD
- JWT_SECRET (long random)
- CORS_ORIGINS (your URL, e.g. https://brackets.bumbledragon.xyz)

If you use a reverse proxy (Nginx Proxy Manager), set:
- PUBLIC_API_BASE=https://brackets.bumbledragon.xyz/api
- CORS_ORIGINS=https://brackets.bumbledragon.xyz

## 4) Bind volumes to your datasets (recommended)
In `docker-compose.yml`, replace the named volumes with bind mounts:

### db service
Replace:
`mep_bracket_db:/var/lib/postgresql/data`
with:
`/mnt/tank/apps/mep-bracket/db:/var/lib/postgresql/data`

### backend service
Replace:
`mep_bracket_pdfs:${PDF_OUTPUT_DIR}`
with:
`/mnt/tank/apps/mep-bracket/pdfs:${PDF_OUTPUT_DIR}`

## 5) Run Docker Compose on TrueNAS
If you use the TrueNAS UI for compose:
- Apps → (Custom App / Compose) → paste the compose
OR use a tool like Dockge/Portainer.

CLI example (if you prefer):
```bash
cd /mnt/tank/apps/mep-bracket/mep-bracket-tool
cp .env.example .env
# edit .env
docker compose up -d --build
```

## 6) Reverse proxy (recommended)
If you use Nginx Proxy Manager:
- Create a Proxy Host: `brackets.bumbledragon.xyz` → `http://<truenas-ip>:3000`
- Add a Custom location for `/api` → `http://<truenas-ip>:8000`
- Force SSL + request a Let's Encrypt cert
- Enable Websockets (safe)

**Path routing**:
- `/` (frontend)
- `/api/*` (backend)

Also set:
- `CORS_ORIGINS=https://brackets.bumbledragon.xyz`
- `PUBLIC_API_BASE=https://brackets.bumbledragon.xyz/api`

## 7) First run
Open the frontend, register a user, import CSV templates, create a project, generate a PDF.

If anything fails, check logs:
```bash
docker compose logs -f backend
docker compose logs -f db
```
