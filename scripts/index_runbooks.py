from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.indexer import RunbookIndex

def main():
    parser = argparse.ArgumentParser(description="Index Markdown runbooks into local Qdrant")
    parser.add_argument("--source", type=Path, default=Path("data/runbooks"))
    parser.add_argument("--index", type=Path, default=Path("data/qdrant"))
    args = parser.parse_args()
    RunbookIndex(args.index).build(sorted(args.source.glob("*.md")))
    print(f"Indexed runbooks into {args.index}")
if __name__ == "__main__": main()
