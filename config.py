"""
Configuration for IVR System on Vercel.

Reads from Vercel environment variables:
- POSTGRES_URL: Auto-set by Vercel Postgres (Neon)
- KV_REST_API_URL: Auto-set by Vercel Redis (Upstash)
- KV_REST_API_TOKEN: Auto-set by Vercel Redis (Upstash)
- PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN: Set manually in Vercel Settings
"""

import os


class Config:
    # ===== VERCEL POSTGRES (Neon) =====
    # Auto-configured when you connect Postgres via Vercel Storage tab
    # Vercel sets POSTGRES_URL with format: postgres://user:pass@host/db?sslmode=require
    # SQLAlchemy needs "postgresql://" prefix, so we fix it
    _raw_pg_url = os.getenv('POSTGRES_URL', '')
    if _raw_pg_url.startswith('postgres://'):
        DATABASE_URL = _raw_pg_url.replace('postgres://', 'postgresql://', 1)
    else:
        DATABASE_URL = _raw_pg_url or 'postgresql://localhost/ivr_db'

    # ===== VERCEL REDIS / UPSTASH =====
    # Auto-configured when you connect Redis via Vercel Storage tab
    KV_REST_API_URL = os.getenv('KV_REST_API_URL', '')
    KV_REST_API_TOKEN = os.getenv('KV_REST_API_TOKEN', '')

    # ===== PLIVO =====
    # Set these manually in Vercel Dashboard -> Settings -> Environment Variables
    PLIVO_AUTH_ID = os.getenv('PLIVO_AUTH_ID', '')
    PLIVO_AUTH_TOKEN = os.getenv('PLIVO_AUTH_TOKEN', '')
    PLIVO_PHONE_NUMBER = os.getenv('PLIVO_PHONE_NUMBER', '')

    # ===== FLASK =====
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'vercel-secret-key')

    # ===== IVR SETTINGS =====
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', 5))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    SESSION_TTL = int(os.getenv('SESSION_TTL', 1800))  # 30 minutes

    # ===== TRANSFER NUMBERS =====
    SALES_TRANSFER_NUMBER = os.getenv('SALES_TRANSFER_NUMBER', '')
    SUPPORT_TRANSFER_NUMBER = os.getenv('SUPPORT_TRANSFER_NUMBER', '')

    # ===== WEBHOOK BASE URL =====
    # Set this to your Vercel deployment URL (e.g., https://your-project.vercel.app)
    WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', '')


def get_config():
    return Config()
