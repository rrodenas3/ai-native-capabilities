"""Mock CRM connector."""

from __future__ import annotations


class CustomerProfileConnector:
    def __init__(self) -> None:
        self.profiles = {"cust-1": {"customer_id": "cust-1", "preferences": {"category": "coffee"}}}

    def get_profile(self, customer_id: str) -> dict:
        return self.profiles.get(customer_id, {"customer_id": customer_id, "preferences": {}})

    def get_history(self, customer_id: str) -> list[dict]:
        return [{"order_id": "1001", "items": ["p-espresso"]}] if customer_id == "cust-1" else []

    def update_preferences(self, customer_id: str, preferences: dict) -> dict:
        profile = self.get_profile(customer_id)
        profile["preferences"] = {**profile.get("preferences", {}), **preferences}
        self.profiles[customer_id] = profile
        return profile
