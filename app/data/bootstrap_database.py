from __future__ import annotations

import argparse

from app.data.database import bootstrap_database, resolve_database_url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the Postgres schema and sync curated seed data."
    )
    parser.add_argument(
        "--database-url",
        help="Explicit Postgres database URL. Defaults to DATABASE_URL.",
    )
    args = parser.parse_args()
    bootstrap_database(args.database_url or resolve_database_url())


if __name__ == "__main__":
    main()
