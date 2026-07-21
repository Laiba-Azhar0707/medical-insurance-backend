---
title: Medical Insurance Claims Backend
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Medical Insurance Claims Processing — Backend

FastAPI backend for AI-powered medical insurance claims processing. Handles auth, claim
submission, multi-document OCR (Groq vision), structured data extraction, prescribed-vs-billed
comparison, and deduction calculation, with a review-flagging safety net against AI fabrication
on illegible documents.

## Stack
- FastAPI + SQLAlchemy
- Groq (`qwen/qwen3.6-27b` for vision OCR, `openai/gpt-oss-120b` for structured extraction)
- PostgreSQL (persistent storage)

## Required secrets (set in Space settings, not committed)
- `GROQ_API_KEY`
- `SECRET_KEY` — JWT signing key
- `DATABASE_URL` — Postgres connection string
- `FRONTEND_ORIGIN` — deployed frontend URL(s), comma-separated