"""The one canonical object every source adapter must emit."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeObject:
    id: str                    # stable slug; re-ingesting the same id replaces it
    title: str
    body: str                  # markdown-ish text
    source_type: str           # markdown | csv | slack_export | notion | capture
    team: str                  # ops | product | eng | gtm | ga | meta
    doc_type: str              # sop | playbook | prd | policy | slack_thread | resolution | ...
    owner: str                 # who a gap on this topic gets routed to
    updated_at: datetime       # drives freshness-aware ranking
    source_url: str = ""
    visibility: list[str] = field(default_factory=lambda: ["everyone"])
    entities: list[str] = field(default_factory=list)   # payers, CDT codes, PMS names
    provenance: dict | None = None                      # for captures: who/when/which case
