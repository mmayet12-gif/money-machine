from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Topic:
    idx: int
    title: str
    keyword: str
    hook: str
    volume: str
    monetization: List[str]
    structure: List[str]


@dataclass
class GenerationUnit:
    unit_id: str
    title: str
    prompt: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationResult:
    success: bool
    unit_id: str
    artifact_paths: List[str] = field(default_factory=list)
    error: str = ""
