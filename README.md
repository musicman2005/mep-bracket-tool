# MEP Bracket Tool (Open Source Skeleton)

A self-hostable web app for sizing **trapeze brackets** for MEP services and generating **Golden Thread** PDF design records.

## What this repo includes (v0.1)
- FastAPI backend (auth, projects, revisions, CSV library import, PDF report)
- Postgres database
- Simple static frontend (single-page HTML) to prove the workflow
- CSV templates for manufacturer libraries (Hilti / Atkore placeholders)
- Docker Compose for self-hosting

> ⚠️ IMPORTANT: This repository ships **no manufacturer capacity data**. You must import data you are licensed to use.

## Quickstart (Docker)
1. Copy `.env.example` to `.env` and edit secrets.
2. Run:
   ```bash
   docker compose up -d --build
   ```
3. Open:
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs

## TrueNAS SCALE
See `docker/TRUENAS_SETUP.md`.
