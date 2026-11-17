"""Deterministic demo planner — no LLM, no network.

Used only when no real LLM provider is configured (demo mode). It is an
honest, labeled alternative: the UI shows a DEMO MODE badge and the provider
name is reported as "demo" in every response envelope. It never pretends to
be an AI model.

Recognition is deliberately simple and transparent. It handles Romanized
Hinglish/English freight requests and a fixed set of explicit commands.
Unsupported intents produce an honest reply explaining what is available.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from .base import BaseProvider

# Canonical locations (subset known to the demo seed).
LOCATIONS = {
    "rourkela": "Rourkela",
    "ranchi": "Ranchi",
    "kolkata": "Kolkata",
    "jamshedpur": "Jamshedpur",
    "bhubaneswar": "Bhubaneswar",
    "cuttack": "Cuttack",
    "patna": "Patna",
    "siliguri": "Siliguri",
    "durgapur": "Durgapur",
    "asansol": "Asansol",
    "paradip": "Paradip",
    "nagpur": "Nagpur",
    "raipur": "Raipur",
    "bhilai": "Bhilai",
    "bilaspur": "Bilaspur",
    "gaya": "Gaya",
    "dhanbad": "Dhanbad",
    "bokaro": "Bokaro",
    "balasore": "Balasore",
    "berhampur": "Berhampur",
}

VEHICLE_TYPES = {
    "open": "open_body",
    "open body": "open_body",
    "trailer": "trailer",
    "container": "container",
    "covered": "covered_body",
    "covered body": "covered_body",
    "truck": "open_body",
    "6 wheeler": "6_wheeler",
    "10 wheeler": "10_wheeler",
    "14 wheeler": "14_wheeler",
    "flatbed": "flatbed",
}


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())


def _find_location(text: str) -> tuple[str | None, str | None]:
    found = []
    for key, canonical in LOCATIONS.items():
        if key in text:
            found.append((text.index(key), canonical))
    if not found:
        return None, None
    found.sort()
    # First mention is treated as origin, last as destination (common in
    # "from X to Y" phrasing; explicit words are handled by the caller).
    return found[0][1], found[-1][1]


def _extract_weight(text: str) -> float | None:
    # Allow hyphenated units: "14-tonne", "8 tons", "5 tonne".
    m = re.search(r"(\d+(?:\.\d+)?)\s*-?\s*(tonnes|tonne|tons|ton|tn)\b", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", text)
    if m:
        return float(m.group(1)) / 1000.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(quintal|qtl)\b", text)
    if m:
        return float(m.group(1)) / 10.0
    return None


def _extract_date(text: str) -> str | None:
    today = dt.date.today()
    if "parso" in text or "day after tomorrow" in text:
        return (today + dt.timedelta(days=2)).isoformat()
    if "kal" in text or "tomorrow" in text:
        return (today + dt.timedelta(days=1)).isoformat()
    if "aaj" in text or "today" in text:
        return today.isoformat()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return dt.date(y, mo, d).isoformat()
        except ValueError:
            return None
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    for name, idx in days.items():
        if name in text:
            delta = (idx - today.weekday()) % 7
            if delta == 0:
                delta = 7
            return (today + dt.timedelta(days=delta)).isoformat()
    return None


def _extract_budget(text: str) -> float | None:
    m = re.search(r"(?:rs\.?|inr|rupees?|₹)\s*(\d+(?:,\d{3})*(?:\.\d+)?)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"budget\s+(\d+(?:,\d{3})*)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    # Numeric-only amounts after a preposition: "at 38000", "to 34000",
    # "for 30000" — currency symbol is optional.
    m = re.search(r"\b(?:at|to|for|of)\s+(\d+(?:,\d{3})*(?:\.\d+)?)\b", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _extract_vehicle(text: str) -> str | None:
    for key, canonical in VEHICLE_TYPES.items():
        if key in text:
            return canonical
    return None


def _extract_goods(text: str) -> str | None:
    keywords = ["steel", "cement", "coal", "rice", "wheat", "iron", "pipe",
                "machinery", "industrial", "textile", "grain", "fertilizer",
                "chemical", "paper", "brick", "stone", "sand", "food"]
    for kw in keywords:
        if kw in text:
            return kw.title()
    return None


def _extract_any_id(text: str) -> str | None:
    """Find a marketplace id like REQ-XXXX / OFF-XXXX / TRIP-XXXX."""
    m = re.search(r"\b(REQ|OFF|TRIP)-[A-Z0-9]{4,16}\b", text.upper())
    return m.group(0) if m else None


class DemoProvider(BaseProvider):
    name = "demo"

    def complete(self, system: str, user: str) -> str:
        intent = self.plan(user)
        if intent.get("clarification"):
            return intent["clarification"]
        if intent["action"] == "help":
            return ("I'm Disha, running in demo mode (no AI provider configured). "
                    "I can find trucks for a shipment, find loads for a truck, and "
                    "create requests/offers with your approval. Try: "
                    "'Rourkela se Ranchi, 8 ton industrial goods, kal'.")
        if intent["action"] == "track":
            return ("Live tracking is not available in demo mode. I can help you "
                    "find trucks, find loads, and create/confirm requests.")
        if intent["action"] == "chat":
            return ("I understood your message. To help, tell me a route like "
                    "'from Rourkela to Ranchi' with weight and date, or ask me to "
                    "'find loads' for your truck.")
        return intent.get("summary") or "OK"

    # -- intent engine -----------------------------------------------------
    def plan(self, message: str) -> dict[str, Any]:
        text = _norm(message)
        intent: dict[str, Any] = {
            "action": "chat",
            "missing_fields": [],
            "summary": "",
            "provider": "demo",
        }

        # --- explicit commands -------------------------------------------
        if "remember that" in text or "yaad rakho" in text or "remember:" in text:
            idx = max(text.find("remember that"), text.find("yaad rakho"), text.find("remember:"))
            fact = text[idx:].split("remember", 1)[-1].lstrip(" :").strip()
            if fact:
                intent["action"] = "remember"
                intent["fact_text"] = fact
                intent["summary"] = f"Save memory: {fact}"
                return intent

        if "accept offer" in text or "accept the offer" in text:
            offer_id = _extract_any_id(text)
            if not offer_id or not offer_id.startswith("OFF-"):
                intent["action"] = "accept_offer"
                intent["clarification"] = "Which offer should I accept? Please give the offer id (e.g. OFF-XXXX)."
                return intent
            intent["action"] = "accept_offer"
            intent["offer_id"] = offer_id
            intent["summary"] = f"Accept offer {offer_id}"
            return intent

        if "confirm request" in text or "confirm the request" in text or "confirm booking" in text:
            req_id = _extract_any_id(text)
            if not req_id or not req_id.startswith("REQ-"):
                intent["action"] = "confirm_request"
                intent["clarification"] = "Which request should I confirm? Please give the request id (e.g. REQ-XXXX)."
                return intent
            intent["action"] = "confirm_request"
            intent["request_id"] = req_id
            intent["summary"] = f"Confirm request {req_id}"
            return intent

        # --- counter-offer / negotiation (before send-offer: "counter offer
        # on REQ-…" must never be treated as a fresh offer) ------------------
        if any(k in text for k in ("negotiate", "counter", "lower your offer",
                                   "reduce your offer", "kam karo", "best price")):
            offer_ref = _extract_any_id(text)
            if not offer_ref:
                intent["action"] = "counter_offer"
                intent["clarification"] = ("Which request/offer should I negotiate? "
                                           "Please give the request id (e.g. REQ-XXXX).")
                return intent
            intent["action"] = "counter_offer"
            intent["request_id"] = offer_ref
            price = _extract_budget(text)
            if price:
                intent["budget_inr"] = price
            intent["summary"] = f"Counter-offer on {offer_ref}" + (f" at ₹{int(price):,}" if price else "")
            return intent

        if "send offer" in text or "make an offer" in text or "offer on" in text:
            req_id = _extract_any_id(text)
            if not req_id or not req_id.startswith("REQ-"):
                intent["action"] = "send_offer"
                intent["clarification"] = "Which shipment/request should I make an offer on? Give the request id (e.g. REQ-XXXX)."
                return intent
            intent["action"] = "send_offer"
            intent["request_id"] = req_id
            price = _extract_budget(text)
            if price:
                intent["budget_inr"] = price
            intent["summary"] = f"Send offer on request {req_id}" + (f" at ₹{int(price):,}" if price else "")
            return intent

        if "track" in text:
            intent["action"] = "track"
            intent["summary"] = "Tracking requested"
            return intent

        if "help" in text or "kya kar sakte ho" in text:
            intent["action"] = "help"
            return intent

        # --- transporter vehicle availability ------------------------------
        demand_markers = ("need", "require", "transport", "chahiye", "chahie", "want")
        if ("vehicle" in text or "truck" in text or "gaadi" in text) and \
           ("available" in text or "confirm" in text) and \
           not any(m in text for m in demand_markers):
            origin, destination = _find_location(text)
            capacity = _extract_weight(text)
            vehicle = _extract_vehicle(text) or "open_body"
            missing = []
            if not origin:
                missing.append("origin")
            if not destination:
                missing.append("destination")
            if capacity is None:
                missing.append("capacity_tonnes")
            if missing:
                intent["action"] = "publish_availability"
                intent["missing_fields"] = missing
                intent["clarification"] = ("To publish your vehicle availability I need: " +
                                           ", ".join(missing) + ".")
                return intent
            intent["action"] = "publish_availability"
            intent["origin"] = origin
            intent["destination"] = destination
            intent["weight_tonnes"] = capacity
            intent["vehicle_type"] = vehicle
            if "confirm" not in text:
                intent["clarification"] = (f"Please confirm: publish your vehicle availability — "
                                           f"{capacity:g}-tonne from {origin} → {destination}?")
                return intent
            intent["summary"] = f"Publish vehicle availability {capacity:g}t {origin} → {destination}"
            return intent

        # --- explicit create-request command ------------------------------
        if any(k in text for k in ("create a request", "create request", "new request",
                                   "request banao", "request create karo")):
            origin, destination = _find_location(text)
            weight = _extract_weight(text)
            date_ = _extract_date(text)
            vehicle = _extract_vehicle(text)
            goods = _extract_goods(text)
            budget = _extract_budget(text)
            missing = []
            if not origin:
                missing.append("origin")
            if not destination:
                missing.append("destination")
            if not weight:
                missing.append("weight_tonnes")
            if not date_:
                missing.append("pickup_date")
            intent["action"] = "create_request"
            if origin:
                intent["origin"] = origin
            if destination:
                intent["destination"] = destination
            if weight is not None:
                intent["weight_tonnes"] = weight
            if date_:
                intent["pickup_date"] = date_
            if vehicle:
                intent["vehicle_type"] = vehicle
            if goods:
                intent["goods"] = goods
            if budget is not None:
                intent["budget_inr"] = budget
            if missing:
                intent["missing_fields"] = missing
                intent["clarification"] = ("I need more details to create the request: " +
                                           ", ".join(missing) + ".")
                return intent
            intent["summary"] = f"Create shipment request {origin} → {destination} ({weight:g}t)"
            return intent

        # --- price quote request ------------------------------------------
        if any(k in text for k in ("how much should i pay", "what should i pay",
                                   "quote", "estimate price", "kitna lagega")):
            origin, destination = _find_location(text)
            weight = _extract_weight(text)
            missing = []
            if not origin:
                missing.append("origin")
            if not destination:
                missing.append("destination")
            if weight is None:
                missing.append("weight_tonnes")
            if missing:
                intent["action"] = "price_quote"
                intent["missing_fields"] = missing
                intent["clarification"] = ("I need the route and weight to estimate freight: " +
                                           ", ".join(missing) + ".")
                return intent
            intent["action"] = "price_quote"
            intent["origin"] = origin
            intent["destination"] = destination
            intent["weight_tonnes"] = weight
            intent["summary"] = f"Estimate freight {origin} → {destination} ({weight:g}t)"
            return intent

        # --- find truck vs find load -------------------------------------
        origin, destination = _find_location(text)
        weight = _extract_weight(text)
        date_ = _extract_date(text)
        vehicle = _extract_vehicle(text)
        goods = _extract_goods(text)
        budget = _extract_budget(text)

        is_transporter = any(k in text for k in (
            "load milega", "load chahiye", "find load", "return load",
            "empty truck", "meri gaadi", "load dhoondh", "load kahan",
        ))

        action = "find_load" if is_transporter else "find_truck"

        # Loads are searched from the transporter's current route: if only
        # one city is given, treat it as the origin (truck location).
        missing: list[str] = []
        if not origin and action == "find_truck":
            missing.append("origin")
        if not destination and action == "find_truck":
            missing.append("destination")
        if action == "find_load":
            if not origin:
                missing.append("origin")
            if not destination:
                missing.append("destination")
        if action == "find_truck" and not weight:
            missing.append("weight_tonnes")
        if action == "find_truck" and not date_:
            missing.append("pickup_date")

        intent["action"] = action
        if origin:
            intent["origin"] = origin
        if destination:
            intent["destination"] = destination
        if weight is not None:
            intent["weight_tonnes"] = weight
        if date_:
            intent["pickup_date"] = date_
        if vehicle:
            intent["vehicle_type"] = vehicle
        if goods:
            intent["goods"] = goods
        if budget is not None:
            intent["budget_inr"] = budget

        if missing:
            intent["missing_fields"] = missing
            if "origin" in missing:
                intent["clarification"] = "Loading kahan se hai? (Where is pickup?)"
            elif "destination" in missing:
                intent["clarification"] = "Where is delivery (destination)?"
            elif "weight_tonnes" in missing:
                intent["clarification"] = "Kitna weight hai, tonnes mein? (Weight in tonnes?)"
            elif "pickup_date" in missing:
                intent["clarification"] = "Kab pickup chahiye? (Which pickup date?)"
            return intent

        summary_bits = []
        if origin:
            summary_bits.append(origin)
        if destination:
            summary_bits.append(f"to {destination}")
        if weight is not None:
            summary_bits.append(f"{weight:g} tonnes")
        if goods:
            summary_bits.append(goods)
        if date_:
            summary_bits.append(f"pickup {date_}")
        if budget is not None:
            summary_bits.append(f"budget ₹{int(budget):,}")
        intent["summary"] = f"{'Find loads for' if action == 'find_load' else 'Find trucks for'} " + ", ".join(summary_bits) if summary_bits else ""
        return intent
