from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from or_trace.domain.models import EntityKind

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntityInput(StrictModel):
    id: Identifier
    kind: EntityKind
    display_name: str = Field(min_length=1, max_length=200)


class AccountInput(StrictModel):
    id: Identifier
    entity_id: Identifier
    institution: str = Field(min_length=1, max_length=100)


class TransactionInput(StrictModel):
    id: Identifier
    source_account_id: Identifier
    destination_account_id: Identifier
    amount: Decimal = Field(gt=0, max_digits=28, decimal_places=8, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    occurred_at: datetime
    source_system: Identifier
    external_id: Identifier

    @field_validator("amount", mode="before", json_schema_input_type=str)
    @classmethod
    def require_decimal_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("amount must be a decimal string")
        return value

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value):
        if value.utcoffset() is None:
            raise ValueError("timestamp requires timezone")
        return value.astimezone(timezone.utc)


class IngestInput(StrictModel):
    transactions: List[TransactionInput] = Field(min_length=1, max_length=1000)


class FindingOutput(BaseModel):
    code: str
    weight: int
    transaction_ids: List[str]
    account_ids: List[str]
    explanation: str


class PathOutput(BaseModel):
    account_ids: List[str]
    transaction_ids: List[str]
    currency: str
    bottleneck_amount: Decimal
    elapsed_seconds: float
    risk_score: int
    findings: List[FindingOutput]
    terminated_by_cycle: bool


class TraceOutput(BaseModel):
    paths: List[PathOutput]
    truncated: bool
    expansions: int
    snapshot_sha256: str
    transaction_count: int
    rule_version: str
    attribution_method: str
    assumptions: List[str]


class IngestOutput(BaseModel):
    accepted: int
    duplicates: int
