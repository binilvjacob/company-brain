"""CSV adapter: operational spreadsheets → one KnowledgeObject per row.

Two known sheets ship in the corpus:
- ops/resolutions.csv     — resolved exception-queue cases with specialist reasoning
- ops/payer-notes.csv     — the tribal-knowledge payer quirks sheet
Each row becomes its own retrievable object so "the 2 most similar past
resolutions" is a retrieval query, not a table scan.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.models import KnowledgeObject


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


class CSVAdapter:
    def load(self, root: Path) -> Iterable[KnowledgeObject]:
        res = root / "ops" / "resolutions.csv"
        if res.exists():
            with res.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    body = (
                        f"Payer: {row['payer']}\nProcedure: {row['procedure']}\n"
                        f"Flag reason: {row['flag_reason']}\n"
                        f"Portal/source output: {row['portal_output']}\n\n"
                        f"Decision: {row['decision']}\n"
                        f"Specialist reasoning: {row['reasoning']}\n"
                        f"Outcome: {row['outcome']}"
                    )
                    yield KnowledgeObject(
                        id=f"resolution-{row['case_id'].lower()}",
                        title=f"Resolved exception {row['case_id']}: {row['payer']} {row['procedure']} — {row['flag_reason']}",
                        body=body,
                        source_type="csv",
                        source_url="corpus/ops/resolutions.csv",
                        team="ops",
                        doc_type="resolution",
                        owner=row["specialist"],
                        updated_at=_dt(row["resolved_at"]),
                        entities=[row["payer"], row["procedure"]],
                    )

        notes = root / "ops" / "payer-notes.csv"
        if notes.exists():
            with notes.open(encoding="utf-8") as f:
                for i, row in enumerate(csv.DictReader(f)):
                    yield KnowledgeObject(
                        id=f"payer-note-{i:03d}",
                        title=f"Payer note: {row['payer']} — {row['topic']}",
                        body=f"{row['note']}\n\nAdded by: {row['added_by']}",
                        source_type="csv",
                        source_url="corpus/ops/payer-notes.csv",
                        team="ops",
                        doc_type="notes",
                        owner=row["added_by"],
                        updated_at=_dt(row["updated_at"]),
                        entities=[row["payer"]],
                    )
