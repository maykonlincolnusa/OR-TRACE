"""Technology-independent financial records. Amounts never use binary floats."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class EntityKind(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"


@dataclass(frozen=True)
class Entity:
    id: str
    kind: EntityKind
    display_name: str


@dataclass(frozen=True)
class Account:
    id: str
    entity_id: str
    institution: str


@dataclass(frozen=True)
class Transaction:
    id: str
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    source_system: str
    external_id: str

    def __post_init__(self):
        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("amount must be positive and finite")
        if self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at requires timezone")
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency requires three uppercase letters")
        if self.source_account_id == self.destination_account_id:
            raise ValueError("self transfers are not supported")
        if not all((self.id, self.source_system, self.external_id)):
            raise ValueError("transaction identifiers are required")


@dataclass(frozen=True)
class Finding:
    code: str
    weight: int
    transaction_ids: tuple
    account_ids: tuple
    explanation: str


@dataclass(frozen=True)
class Path:
    account_ids: tuple
    transaction_ids: tuple
    currency: str
    bottleneck_amount: Decimal
    elapsed_seconds: float
    risk_score: int
    findings: tuple
    terminated_by_cycle: bool
