"""Synthetic demo dataset for DISHA demo mode.

Every record carries an explicit marker: note contains "[DEMO]" and source
is 'synthetic_seed_data'. This data is for the competition demo ONLY — it is
never real marketplace data.
"""
from __future__ import annotations

import datetime as dt

DEMO_USERS = {
    "demo-shipper-01": "Demo Shipper 01",
    "demo-transporter-01": "Demo Transporter 01",
    "demo-transporter-02": "Demo Transporter 02",
    "demo-shipper-02": "Demo Shipper 02",
}


def _date(days_from_today: int) -> str:
    return (dt.date.today() + dt.timedelta(days=days_from_today)).isoformat()


TRIPS = [
    # id, transporter, origin, destination, departure, capacity_t, price/tonne, vehicle, reliability
    ("TRIP-0001", "demo-transporter-01", "rourkela", "ranchi", _date(1), 12.0, 3200, "open_body", 0.92),
    ("TRIP-0002", "demo-transporter-02", "rourkela", "ranchi", _date(2), 10.0, 3500, "open_body", 0.88),
    ("TRIP-0003", "demo-transporter-01", "rourkela", "ranchi", _date(3), 16.0, 3000, "trailer", 0.90),
    ("TRIP-0004", "demo-transporter-01", "rourkela", "kolkata", _date(1), 20.0, 2800, "trailer", 0.95),
    ("TRIP-0005", "demo-transporter-02", "ranchi", "kolkata", _date(1), 12.0, 2600, "open_body", 0.85),
    ("TRIP-0006", "demo-transporter-02", "ranchi", "patna", _date(2), 10.0, 2400, "covered_body", 0.82),
    ("TRIP-0007", "demo-transporter-01", "kolkata", "rourkela", _date(1), 18.0, 2900, "trailer", 0.93),
    ("TRIP-0008", "demo-transporter-02", "kolkata", "siliguri", _date(2), 14.0, 2750, "open_body", 0.87),
    ("TRIP-0009", "demo-transporter-01", "jamshedpur", "ranchi", _date(1), 8.0, 3100, "open_body", 0.84),
    ("TRIP-0010", "demo-transporter-02", "bhubaneswar", "rourkela", _date(2), 22.0, 2700, "trailer", 0.89),
    ("TRIP-0011", "demo-transporter-01", "rourkela", "nagpur", _date(4), 16.0, 3300, "trailer", 0.91),
    ("TRIP-0012", "demo-transporter-02", "ranchi", "nagpur", _date(3), 12.0, 3200, "open_body", 0.86),
]

SHIPMENTS = [
    # id, shipper, origin, destination, pickup, weight_t, goods, vehicle, budget, status
    ("SHP-0001", "demo-shipper-01", "rourkela", "ranchi", _date(1), 8.0, "Industrial goods", "open_body", 40000, "pending"),
    ("SHP-0002", "demo-shipper-02", "ranchi", "kolkata", _date(1), 6.0, "Steel pipes", "open_body", 30000, "pending"),
    ("SHP-0003", "demo-shipper-01", "kolkata", "rourkela", _date(2), 15.0, "Machinery", "trailer", 60000, "pending"),
    ("SHP-0004", "demo-shipper-02", "jamshedpur", "ranchi", _date(2), 4.0, "Textile", "covered_body", 20000, "pending"),
    ("SHP-0005", "demo-shipper-01", "rourkela", "kolkata", _date(3), 10.0, "Cement", "open_body", 42000, "pending"),
    ("SHP-0006", "demo-shipper-02", "ranchi", "patna", _date(3), 7.0, "Rice", "covered_body", 28000, "pending"),
    ("SHP-0007", "demo-shipper-01", "kolkata", "siliguri", _date(4), 9.0, "Paper", "open_body", 35000, "pending"),
    ("SHP-0008", "demo-shipper-02", "bhubaneswar", "rourkela", _date(4), 12.0, "Iron ore", "trailer", 50000, "pending"),
]

REQUESTS = [
    # id, shipper, origin, dest, goods, weight, vehicle, date, budget, status, created days ago, confirmed days ago
    ("REQ-HIST1", "demo-shipper-01", "rourkela", "ranchi", "Industrial goods", 8.0, "open_body", _date(-1), 40000, "confirmed", -4, -3),
    ("REQ-HIST2", "demo-shipper-02", "ranchi", "kolkata", "Steel pipes", 6.0, "open_body", _date(-2), 30000, "confirmed", -5, -4),
    ("REQ-HIST3", "demo-shipper-01", "kolkata", "rourkela", "Machinery", 15.0, "trailer", _date(-3), 60000, "pending", -6, None),
]

OFFERS = [
    ("OFF-HIST1", "REQ-HIST1", "demo-transporter-01", "TRIP-0001", 35000, "accepted", -3),
    ("OFF-HIST2", "REQ-HIST1", "demo-transporter-02", "TRIP-0002", 36000, "declined", -3),
    ("OFF-HIST3", "REQ-HIST2", "demo-transporter-01", "TRIP-0005", 29000, "accepted", -4),
    ("OFF-HIST4", "REQ-HIST3", "demo-transporter-01", "TRIP-0007", 56000, "pending", -2),
    ("OFF-HIST5", "REQ-HIST3", "demo-transporter-02", "TRIP-0003", 57500, "pending", -2),
]

NOTIFICATIONS = [
    ("demo-transporter-01", "offer", "New shipment matched", "A load from Rourkela to Ranchi (8t) matches your trip TRIP-0001. [DEMO]"),
    ("demo-shipper-01", "request", "Request created", "Your request REQ-HIST3 is pending. [DEMO]"),
    ("demo-transporter-02", "offer", "New shipment matched", "A load from Rourkela to Ranchi (8t) matches your trip TRIP-0002. [DEMO]"),
]
