"""
Loads data-layer JSON (schemas/data_layer.schema.json, Phase 1) into a
frozen DataLayer object, per DECISIONS.md D-011: in memory, no DB table.

Not needed by Phase 4's pure pass-through SNAP pilot (the schema's own
description says as much), but built now since Phase 1 already produced
real, schema-valid fixtures (schemas/examples/wic_co.json, wic_nc.json) to
validate this loader against.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SourceInfo:
    status: str  # "cited" | "unsourced" | "guessed" (DECISIONS.md D-005)
    citation: Optional[str]


@dataclass(frozen=True)
class DataLayer:
    program: str
    state: str
    category_amounts: dict[str, float]
    source: SourceInfo


def load_data_layer(data: dict) -> DataLayer:
    return DataLayer(
        program=data["program"],
        state=data["state"],
        category_amounts=dict(data["category_amounts"]),
        source=SourceInfo(status=data["source"]["status"], citation=data["source"]["citation"]),
    )


def load_data_layer_from_file(path: str | Path) -> DataLayer:
    return load_data_layer(json.loads(Path(path).read_text()))
