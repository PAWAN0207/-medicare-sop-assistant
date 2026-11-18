"""Access control: plain code, no LLM involved. Fails closed on anything unknown."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ..errors import IngestError, UnknownUser


@dataclass(frozen=True)
class AccessPolicy:
    field_to_level: dict[str, str]
    role_levels: dict[str, frozenset[str]]

    @classmethod
    def load(cls, path: Path) -> "AccessPolicy":
        raw = json.loads(Path(path).read_text())
        return cls(
            field_to_level={k.strip().lower(): v for k, v in raw["access_field_to_level"].items()},
            role_levels={r: frozenset(v) for r, v in raw["role_levels"].items()},
        )

    def level_for_field(self, access_field: str) -> str:
        """Map the 'Access' text in an SOP header to a level. Unknown text aborts ingestion
        (fail closed) rather than defaulting to 'all'."""
        norm = " ".join(access_field.split()).lower()
        if norm not in self.field_to_level:
            raise IngestError(f"Unknown Access field {access_field!r}: add it to access_policy.json")
        return self.field_to_level[norm]

    def levels_for_role(self, role: str) -> frozenset[str]:
        # unknown role -> empty set -> sees nothing
        return self.role_levels.get(role, frozenset())


@dataclass(frozen=True)
class User:
    user_id: str
    name: str
    role: str


class UserDirectory:
    def __init__(self, users: dict[str, User]):
        self._users = users

    @classmethod
    def from_csv(cls, path: Path) -> "UserDirectory":
        with open(path, newline="") as f:
            users = {r["user_id"].strip(): User(r["user_id"].strip(), r["name"].strip(), r["role"].strip())
                     for r in csv.DictReader(f)}
        return cls(users)

    def get(self, user_id: str) -> User:
        u = self._users.get((user_id or "").strip())
        if u is None:
            raise UnknownUser("Unknown user id")
        return u
