"""Seed the Brain from the corpus. Idempotent; --if-empty for boot-time use."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import db  # noqa: E402
from app.adapters import load_corpus  # noqa: E402
from app.ingest import ingest_all  # noqa: E402
from app.recipes import seed_recipes_from_dir  # noqa: E402

ROOT = Path(__file__).parent.parent
DEMO_GAPS = [
    # Pre-seeded so the Gaps dashboard tells its story on first click.
    # Marked source='seeded-demo'; disclosed in DATA.md.
    ("Does Humana require prior auth history for D4341 SRP?", "ops"),
    ("What is the Denti-Cal (California Medicaid) eligibility flow?", "product"),
    ("Which clearinghouse do we use for the claims beta and what are its outage hours?", "eng"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true",
                        help="skip if documents already exist (boot-time seeding)")
    args = parser.parse_args()

    conn = db.connect()
    db.init_schema(conn)

    if args.if_empty and db.counts(conn)["docs"] > 0:
        print(f"seed: skipped, already populated: {db.counts(conn)}")
        return 0

    objects = load_corpus(ROOT / "corpus")
    stats = ingest_all(conn, objects)
    n_recipes = seed_recipes_from_dir(conn, ROOT / "corpus" / "recipes")

    from app.answer import _normalize_question
    for q, team in DEMO_GAPS:
        conn.execute(
            """INSERT INTO gaps (question, normalized, asked_by_role, routed_owner, team_guess, source)
               VALUES (%s, %s, 'everyone', %s, %s, 'seeded-demo')
               ON CONFLICT (normalized) DO NOTHING""",
            (q, _normalize_question(q), {"ops": "priya", "product": "lena", "eng": "nakul"}[team], team),
        )

    print(f"seed: {stats['docs']} documents, {stats['chunks']} chunks, "
          f"{stats['redactions']} redactions, {n_recipes} recipes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
