#!/usr/bin/env python3
"""
scripts/setup_env.py — Interactive environment setup helper.
Run: python scripts/setup_env.py
"""
import os
from pathlib import Path

DIRS = [
    "data/uploaded_docs",
    "data/processed",
    "data/vector_cache",
    "logs",
]

def main():
    print("⚖️  Nexus AI Governance — Environment Setup")
    print("=" * 50)

    # Create directories
    for d in DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {d}/")

    # .env setup
    env_path = Path(".env")
    if not env_path.exists():
        api_key = input("\nEnter your OpenAI API key (leave blank for mock mode): ").strip()
        env_content = f"""OPENAI_API_KEY={api_key}
OPENAI_MODEL=gpt-4o
OLLAMA_HOST=http://localhost:11434
APP_SECRET_KEY=nexus-change-me-in-production
APP_ENV=development
LOG_LEVEL=INFO
VECTOR_STORE_BACKEND=memory
"""
        env_path.write_text(env_content)
        print("✅ .env file created")
    else:
        print("ℹ️  .env already exists — skipping")

    print("\n🚀 Setup complete! Run: streamlit run app.py")


if __name__ == "__main__":
    main()
