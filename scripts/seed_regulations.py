#!/usr/bin/env python3
"""
scripts/seed_regulations.py — Seed the vector store with the full regulatory corpus.
Run: python scripts/seed_regulations.py
"""
import sys
sys.path.insert(0, ".")

from database.memory_store import MockVectorStore
from rag.regulations_seed import REGULATIONS_CORPUS


def main():
    print(f"Seeding {len(REGULATIONS_CORPUS)} regulations into MockVectorStore…")
    vs = MockVectorStore()
    print(f"✅ Vector store ready — {vs.count()} documents loaded.")
    print(f"   Frameworks: {', '.join(vs.frameworks())}")


if __name__ == "__main__":
    main()
