"""Rule-based fast intent classifier for Cap-03."""

from __future__ import annotations

import re

from cap03_schema_loader import IntentClass, IntentResult

PATTERNS = [
    (IntentClass.ESCALATION, r"\b(human|representative|manager|supervisor|legal|regulatory)\b", "human_escalation"),
    (IntentClass.COMPLAINT, r"\b(angry|complaint|terrible|unacceptable|broken|refund now)\b", "complaint"),
    (IntentClass.SUPPORT, r"\b(order|return|refund|shipment|tracking|warranty|cancel)\b", "order_support"),
    (IntentClass.REORDER, r"\b(reorder|buy again|same as last|repeat order)\b", "reorder"),
    (IntentClass.COMPARISON, r"\b(compare|versus|vs\.?|difference|better than)\b", "comparison"),
    (IntentClass.DISCOVERY, r"\b(need|looking for|recommend|best|find|gift|search)\b", "product_discovery"),
    (IntentClass.BROWSE, r"\b(show me|browse|category|what do you have)\b", "browse"),
]


def classify_intent(message: str) -> IntentResult:
    lowered = message.lower().strip()
    for intent, pattern, sub_intent in PATTERNS:
        if re.search(pattern, lowered):
            return IntentResult(intent_class=intent, intent_confidence=0.95, sub_intent=sub_intent)
    if len(lowered.split()) <= 2:
        return IntentResult(intent_class=IntentClass.CLARIFICATION, intent_confidence=0.55, sub_intent="too_short")
    return IntentResult(intent_class=IntentClass.CLARIFICATION, intent_confidence=0.65, sub_intent="ambiguous")
