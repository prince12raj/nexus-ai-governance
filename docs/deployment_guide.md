# Deployment Guide

## Local Development

```bash
pip install -r requirements.txt
python scripts/setup_env.py
streamlit run app.py
```

## Docker

```bash
cd docker
docker compose up --build -d
# Access: http://localhost
```

## Environment Variables

Copy `.env` to `.env.production` and set:
- `OPENAI_API_KEY=sk-...`
- `APP_SECRET_KEY=<32-char random string>`
- `APP_ENV=production`

## Production Checklist

- [ ] Set `APP_SECRET_KEY` to a strong random value
- [ ] Configure HTTPS in nginx.conf
- [ ] Set `OPENAI_API_KEY` or configure local LLM
- [ ] Mount persistent volumes for `data/` and `logs/`
- [ ] Enable log rotation
- [ ] Replace demo `USERS_DB` with a real database
- [ ] Use bcrypt for password hashing (replace `auth/security.py`)
