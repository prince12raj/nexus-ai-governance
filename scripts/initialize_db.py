#!/usr/bin/env python3
"""
scripts/initialize_db.py — Initialize all persistent directories and stores.
Run: python scripts/initialize_db.py
"""
import sys
from pathlib import Path
sys.path.insert(0, ".")


def main():
    for d in ["data/uploaded_docs","data/processed","data/vector_cache","logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✅ {d}/")

    from database.memory_store import MockVectorStore
    vs = MockVectorStore()
    print(f"✅ MockVectorStore — {vs.count()} docs, frameworks: {vs.frameworks()}")
    print("\n✅ Database initialised. Run: streamlit run app.py")


if __name__ == "__main__":
    main()
