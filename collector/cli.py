from __future__ import annotations

import argparse
import json
import logging

from collector.pipeline import run_collection


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor automático do ConcursoAI")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    results = run_collection()
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
