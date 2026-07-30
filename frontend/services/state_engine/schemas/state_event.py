"""
State Event Schemas
===================
Defines the input contract (IntelligenceEvent), output contract (StateEvent),
and bucket log entry for the State Engine.
"""

from enum import Enum
from typing import Any, Dict, Optional

import pydantic
from pydantic import BaseModel, Field

PYDANTIC_V2 = int(pydantic.VERSION.split(".", 1)[0]) >= 2
if PYDANTIC_V2:
    from pydantic import ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Risk levels exactly matching the upstream contract."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SystemState(str, Enum):
    """Deterministic system states consumed by UI and Mitra."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ALERT = "ALERT"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Input Contract — DO NOT CHANGE
# ---------------------------------------------------------------------------

class IntelligenceEvent(BaseModel):
    """
    Incoming event from Ankita / Sanskar.

    Pipeline:  Acoustic Node → Samachar → NICAI → Sanskar → **State Engine**
    """
    trace_id: Optional[str] = None
    vessel_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    anomaly_flag: bool = False
    explanation: str = ""

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:
        class Config:
            extra = "allow"


# ---------------------------------------------------------------------------
# Output Contract
# ---------------------------------------------------------------------------

class StateEvent(BaseModel):
    """
    Outgoing event produced by the State Engine.

    Consumed by: Bucket -> InsightFlow -> UI/Mitra
    """
    trace_id: str
    vessel_type: str
    risk_level: RiskLevel
    state: SystemState
    anomaly_flag: bool
    timestamp: str
    short_label: Optional[str] = None


# ---------------------------------------------------------------------------
# Bucket Log Entry
# ---------------------------------------------------------------------------

class BucketLogEntry(BaseModel):
    """Single line in the bucket JSONL log file."""
    log_type: str             # "incoming" | "outgoing" | "trace_error" | "state_stage"
    trace_id: Optional[str] = None
    stage: Optional[str] = None
    state: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str
