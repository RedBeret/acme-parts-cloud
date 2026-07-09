"""Deterministic synthetic data generators for AcmeParts Cloud.

All generated data is fictional. Meridian Fabrication Co. is a synthetic company.
Seed value controls all randomness — same seed + messiness → same output.
"""

import os
import random
from datetime import timedelta

from faker import Faker

SEED = int(os.getenv("SEED", "42"))
MESSINESS = os.getenv("MESSINESS", "medium")  # clean | medium | chaos

MESS_RATES = {
    "clean": {
        "part_fmt_drift": 0.02,
        "supplier_dupe": 0.03,
        "bad_email": 0.02,
        "state_case": 0.01,
        "date_flip": 0.01,
        "price_error": 0.01,
    },
    "medium": {
        "part_fmt_drift": 0.12,
        "supplier_dupe": 0.10,
        "bad_email": 0.08,
        "state_case": 0.10,
        "date_flip": 0.05,
        "price_error": 0.05,
    },
    "chaos": {
        "part_fmt_drift": 0.30,
        "supplier_dupe": 0.25,
        "bad_email": 0.20,
        "state_case": 0.25,
        "date_flip": 0.15,
        "price_error": 0.15,
    },
}

CATEGORIES = [
    "fastener",
    "structural",
    "electrical",
    "hydraulic",
    "pneumatic",
    "thermal",
    "optical",
    "sealing",
    "bearing",
    "drive",
]
UOMS = ["EA", "FT", "IN", "LB", "KG", "M", "MM", "L", "GAL", "PKG"]
CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP", "CAD", "MXN"]
ROLES = ["engineer", "manager", "technician", "buyer", "qa", "admin"]
CO_STATES_CLEAN = ["open", "in-review", "approved", "closed", "rejected"]
CO_STATES_DIRTY = [
    "open",
    "OPEN",
    "In-Work",
    "in_review",
    "Approved",
    "CLOSED",
    "closed",
    "rejected",
    "REJECTED",
]
PRIORITIES = ["low", "normal", "high", "critical"]


def _rng(extra: int = 0) -> random.Random:
    r = random.Random(SEED + extra)
    return r


def _fake(extra: int = 0) -> Faker:
    f = Faker()
    Faker.seed(SEED + extra)
    return f


def _rates() -> dict:
    return MESS_RATES.get(MESSINESS, MESS_RATES["medium"])


# ── Part number generation ────────────────────────────────────────────────────


def _part_number(idx: int, rng: random.Random) -> str:
    rates = _rates()
    # Three eras of part numbering schemes used at Meridian Fabrication Co.
    if rng.random() < rates["part_fmt_drift"]:
        # Old era: 2019-PN-{N}
        return f"2019-PN-{idx}"
    elif rng.random() < 0.15:
        # Very old era: P{N} (no padding)
        return f"P{idx}"
    else:
        # Current: PN-{N:04d}
        return f"PN-{idx:04d}"


# ── Parts ─────────────────────────────────────────────────────────────────────


def generate_parts(count: int = 5000) -> list[dict]:
    rng = _rng(1)
    fake = _fake(1)
    parts = []
    for i in range(1, count + 1):
        status = rng.choice(["active"] * 8 + ["obsolete", "discontinued"])
        sup_by = None
        if status in ("obsolete", "discontinued") and rng.random() < 0.6:
            sup_by = f"PN-{rng.randint(1, count):04d}"
        parts.append(
            {
                "part_number": _part_number(i, rng),
                "name": fake.bs().title()[:120],
                "category": rng.choice(CATEGORIES),
                "uom": rng.choice(UOMS),
                "status": status,
                "superseded_by": sup_by,
                "created_at": fake.date_time_between(start_date="-8y", end_date="now"),
            }
        )
    return parts


# ── Part revisions ────────────────────────────────────────────────────────────

_REV_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_REV_NUMS = [str(i) for i in range(1, 20)]


def generate_revisions(part_ids: list[int]) -> list[dict]:
    rng = _rng(2)
    fake = _fake(2)
    revisions = []
    rates = _rates()
    for part_id in part_ids:
        n_revs = rng.randint(1, 8)
        # Mix letter and numeric schemes (messiness: gaps + scheme mixing)
        scheme = rng.choice(["letters", "numbers"])
        pool = _REV_LETTERS if scheme == "letters" else _REV_NUMS
        chosen = sorted(rng.sample(pool, min(n_revs, len(pool))))
        # Occasionally mix schemes (messiness)
        if rng.random() < rates["part_fmt_drift"]:
            other = _REV_NUMS if scheme == "letters" else _REV_LETTERS
            chosen[-1] = rng.choice(other)

        base_date = fake.date_time_between(start_date="-5y", end_date="-6m")
        for j, code in enumerate(chosen):
            eff = base_date + timedelta(days=j * rng.randint(30, 180))
            # Date flip: retroactive date (closed before opened) — intentional defect
            if rng.random() < rates["date_flip"] and j > 0:
                eff = base_date - timedelta(days=rng.randint(1, 90))
            revisions.append(
                {
                    "part_id": part_id,
                    "rev_code": code,
                    "effective_date": eff,
                    "change_summary": fake.sentence(nb_words=rng.randint(6, 20)),
                }
            )
    return revisions


# ── Suppliers ────────────────────────────────────────────────────────────────

_BASE_SUPPLIERS = [
    "Vortex Metals",
    "Cascade Composites",
    "Pinnacle Alloys",
    "Summit Fasteners",
    "Apex Hydraulics",
    "Delta Seals",
    "Omega Bearings",
    "Titan Electrical",
    "Nova Pneumatics",
    "Meridian Thermal",
    "Stellar Optics",
    "Crest Drive Systems",
    "Horizon Polymers",
    "Zenith Coatings",
    "Atlas Springs",
]


def generate_suppliers(count: int = 400) -> list[dict]:
    rng = _rng(3)
    fake = _fake(3)
    rates = _rates()
    suppliers = []
    used_codes: set[str] = set()

    for i in range(count):
        base = _BASE_SUPPLIERS[i % len(_BASE_SUPPLIERS)]
        suffix = fake.company_suffix() if rng.random() > 0.4 else ""

        # Supplier name duplication: same company, different name formatting
        if rng.random() < rates["supplier_dupe"] and i > len(_BASE_SUPPLIERS):
            name = rng.choice(
                [
                    base.upper(),
                    base.lower(),
                    f"{base} Inc.",
                    f"{base} LLC",
                    base,
                ]
            )
        else:
            name = f"{base} {suffix}".strip() if suffix else base

        code = f"SUP-{i + 1:04d}"
        while code in used_codes:
            code = f"SUP-{rng.randint(1, 9999):04d}"
        used_codes.add(code)

        email = fake.company_email()
        if rng.random() < rates["bad_email"]:
            # Inject bad email formats
            email = rng.choice(
                [
                    email.replace("@", ""),
                    email + ".invalid",
                    "noreply",
                    fake.first_name(),
                ]
            )

        country = fake.country_code()
        suppliers.append(
            {
                "name": name,
                "code": code,
                "country": country,
                "contact_email": email,
                "active": rng.random() > 0.08,  # some defunct suppliers
            }
        )
    return suppliers


# ── Change orders ────────────────────────────────────────────────────────────


def generate_change_orders(
    part_ids: list[int], user_names: list[str], count: int = 20000
) -> list[dict]:
    rng = _rng(4)
    fake = _fake(4)
    rates = _rates()
    orders = []
    for i in range(1, count + 1):
        # State messiness: inconsistent vocabulary
        if rng.random() < rates["state_case"]:
            state = rng.choice(CO_STATES_DIRTY)
        else:
            state = rng.choice(CO_STATES_CLEAN)

        opened = fake.date_time_between(start_date="-4y", end_date="-1d")
        closed = None
        if state in ("closed", "CLOSED", "approved", "Approved", "rejected", "REJECTED"):
            closed = opened + timedelta(days=rng.randint(1, 120))
            # Date flip: closed before opened (intentional defect)
            if rng.random() < rates["date_flip"]:
                closed = opened - timedelta(days=rng.randint(1, 30))

        orders.append(
            {
                "co_number": f"CO-{i:06d}",
                "part_id": rng.choice(part_ids),
                "state": state,
                "priority": rng.choice(PRIORITIES),
                "description": fake.paragraph(nb_sentences=rng.randint(1, 4)),
                "requested_by": rng.choice(user_names) if user_names else None,
                "opened_at": opened,
                "closed_at": closed,
            }
        )
    return orders


# ── Purchase orders ──────────────────────────────────────────────────────────


def generate_purchase_orders(
    supplier_ids: list[int], part_ids: list[int], count: int = 30000
) -> list[dict]:
    rng = _rng(5)
    fake = _fake(5)
    rates = _rates()
    orders = []
    for _ in range(count):
        price = round(rng.uniform(0.10, 5000.00), 2)
        # Price magnitude error (intentional defect)
        if rng.random() < rates["price_error"]:
            price = price * rng.choice([100, 0.01, 1000])

        currency = rng.choice(CURRENCIES)
        orders.append(
            {
                "supplier_id": rng.choice(supplier_ids),
                "part_id": rng.choice(part_ids),
                "qty": rng.randint(1, 10000),
                "unit_price": price,
                "currency": currency,
                "order_date": fake.date_time_between(start_date="-6y", end_date="now"),
            }
        )
    return orders


# ── Users ────────────────────────────────────────────────────────────────────


def generate_users(count: int = 150) -> list[dict]:
    rng = _rng(6)
    fake = _fake(6)
    users = []
    used_emails: set[str] = set()
    for _ in range(count):
        email = fake.company_email()
        while email in used_emails:
            email = fake.company_email()
        used_emails.add(email)
        users.append(
            {
                "name": fake.name(),
                "email": email,
                "role": rng.choice(ROLES),
                "active": rng.random() > 0.15,  # ~15% ex-employees
            }
        )
    return users
