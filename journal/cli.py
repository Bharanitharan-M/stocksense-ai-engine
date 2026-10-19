import argparse

from pathlib import Path

from dotenv import load_dotenv

from .ingest import ingest
from .outcomes import fill_outcomes
from .report import build_report


def main() -> None:
    p = argparse.ArgumentParser(prog="journal")
    p.add_argument("cmd", choices=["ingest", "outcomes", "report"])
    load_dotenv(Path.home() / ".stocksense" / ".env")  # secrets live outside the repo
    load_dotenv()
    a = p.parse_args()
    if a.cmd == "ingest":
        print(f"{ingest()} new signals")
    elif a.cmd == "outcomes":
        print(f"{fill_outcomes()} signals updated")
    else:
        print(build_report())


if __name__ == "__main__":
    main()
