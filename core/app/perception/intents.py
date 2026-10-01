import re
import string
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

class IntentType(str, Enum):
    OPEN_DOOR = "open_door"
    CLOSE_DOOR = "close_door"
    CHECK_VITALS = "check_vitals"
    EMERGENCY_STOP = "emergency_stop"
    MOVE_FORWARD = "move_forward"
    MOVE_BACKWARD = "move_backward"
    MOVE_STOP = "move_stop"
    CALL_NURSE = "call_nurse"
    UNKNOWN = "unknown"

class ParsedIntent(BaseModel):
    intent: IntentType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_text: str
    matched_rule: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "matched_rule": self.matched_rule,
            "parameters": self.parameters
        }

class RuleBasedIntentParser:
    def __init__(self) -> None:
        self.rules: List[Tuple[IntentType, re.Pattern, float]] = [
            (
                IntentType.EMERGENCY_STOP,
                re.compile(r"\b(emergency\s*stop|e-?stop|abort|halt\s*now|kill\s*power)\b", re.IGNORECASE),
                1.0
            ),
            (
                IntentType.OPEN_DOOR,
                re.compile(r"\b(open|unlock)\b.*\b(door|compartment|cabinet)\b|\bopen\s*door\b", re.IGNORECASE),
                0.95
            ),
            (
                IntentType.CLOSE_DOOR,
                re.compile(r"\b(close|shut|lock)\b.*\b(door|compartment|cabinet)\b|\bclose\s*door\b", re.IGNORECASE),
                0.95
            ),
            (
                IntentType.CHECK_VITALS,
                re.compile(r"\b(check|measure|read|record|take|get)\b.*\b(vitals?|heart|pulse|spo2)\b|\bvitals?\b", re.IGNORECASE),
                0.90
            ),
            (
                IntentType.CALL_NURSE,
                re.compile(r"\b(call|alert|page|notify|need)\b.*\b(nurse|doctor|staff|help)\b|\bhelp\s*me\b", re.IGNORECASE),
                0.95
            ),
            (
                IntentType.MOVE_FORWARD,
                re.compile(r"\b(move|go|drive|step)\s+(forward|ahead|front)\b", re.IGNORECASE),
                0.90
            ),
            (
                IntentType.MOVE_BACKWARD,
                re.compile(r"\b(move|go|drive|step)\s+(backward|back|reverse)\b", re.IGNORECASE),
                0.90
            ),
            (
                IntentType.MOVE_STOP,
                re.compile(r"\b(stop\s+moving|stop\s+driving|brake|hold\s+position|stop)\b", re.IGNORECASE),
                0.85
            ),
        ]

    def _normalize(self, text: str) -> str:
        clean = text.translate(str.maketrans("", "", string.punctuation))
        return " ".join(clean.lower().split())

    def parse(self, text: str) -> ParsedIntent:
        if not text or not text.strip():
            return ParsedIntent(intent=IntentType.UNKNOWN, confidence=0.0, raw_text=text or "")
        normalized = self._normalize(text)
        for intent_type, pattern, conf in self.rules:
            match = pattern.search(normalized)
            if match:
                return ParsedIntent(
                    intent=intent_type,
                    confidence=conf,
                    raw_text=text,
                    matched_rule=match.group(0),
                    parameters={}
                )
        return ParsedIntent(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=text,
            matched_rule=None,
            parameters={}
        )

intent_parser = RuleBasedIntentParser()
