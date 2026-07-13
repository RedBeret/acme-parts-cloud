"""Deterministic synthetic data generators for AcmeParts Cloud.

All generated data is fictional. Meridian Fabrication Co. is a synthetic company.
Seed value controls all randomness — same seed + messiness → same output.
"""

import os
import random
from collections.abc import MutableMapping
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
    "APPROVED",
    "CLOSED",
    "closed",
    "rejected",
    "REJECTED",
]
PRIORITIES = ["low", "normal", "high", "critical"]
AUDIT_ACTIONS = ["create", "update", "import", "approve", "close"]


def _rng(extra: int = 0) -> random.Random:
    r = random.Random(SEED + extra)
    return r


def _fake(extra: int = 0) -> Faker:
    f = Faker()
    Faker.seed(SEED + extra)
    return f


def _rates() -> dict:
    try:
        return MESS_RATES[MESSINESS]
    except KeyError as exc:
        raise ValueError(f"MESSINESS must be one of: {', '.join(MESS_RATES)}") from exc


def _record(
    defects: MutableMapping[str, list[str | int]] | None,
    name: str,
    record_id: str | int,
) -> None:
    if defects is not None:
        defects.setdefault(name, []).append(record_id)


# ── Part number generation ────────────────────────────────────────────────────


def _part_number(idx: int, rng: random.Random) -> str:
    rates = _rates()
    # Three eras of part numbering schemes used at Meridian Fabrication Co.
    if rng.random() < rates["part_fmt_drift"]:
        if rng.random() < 0.5:
            return f"2019-PN-{idx}"
        return f"P{idx}"
    return f"PN-{idx:04d}"


# ── Parts ─────────────────────────────────────────────────────────────────────


def generate_parts(
    count: int = 5000,
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
) -> list[dict]:
    rng = _rng(1)
    fake = _fake(1)
    parts = []
    for i in range(1, count + 1):
        status = rng.choice(["active"] * 8 + ["obsolete", "discontinued"])
        part_number = _part_number(i, rng)
        if not part_number.startswith("PN-"):
            _record(defects, "part_fmt_drift_count", part_number)
        parts.append(
            {
                "part_number": part_number,
                "name": fake.bs().title()[:120],
                "category": rng.choice(CATEGORIES),
                "uom": rng.choice(UOMS),
                "status": status,
                "superseded_by": None,
                "created_at": fake.date_time_between(start_date="-8y", end_date="now"),
            }
        )
    supersession_rng = _rng(101)
    for index, part in enumerate(parts):
        if (
            len(parts) > 1
            and part["status"] in ("obsolete", "discontinued")
            and supersession_rng.random() < 0.6
        ):
            target_index = supersession_rng.randrange(len(parts) - 1)
            if target_index >= index:
                target_index += 1
            part["superseded_by"] = parts[target_index]["part_number"]
    return parts


# ── Part revisions ────────────────────────────────────────────────────────────

_REV_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_REV_NUMS = [str(i) for i in range(1, 20)]


def generate_revisions(
    part_ids: list[int],
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
) -> list[dict]:
    rng = _rng(2)
    fake = _fake(2)
    revisions = []
    rates = _rates()
    for part_id in part_ids:
        n_revs = rng.randint(1, 8)
        # Mix letter and numeric schemes (messiness: gaps + scheme mixing)
        scheme = rng.choice(["letters", "numbers"])
        pool = _REV_LETTERS if scheme == "letters" else _REV_NUMS
        chosen = sorted(
            rng.sample(pool, min(n_revs, len(pool))),
            key=int if scheme == "numbers" else None,
        )
        # Occasionally mix schemes (messiness)
        if len(chosen) > 1 and rng.random() < rates["part_fmt_drift"]:
            other = _REV_NUMS if scheme == "letters" else _REV_LETTERS
            chosen[-1] = rng.choice(other)
            _record(defects, "rev_scheme_mix_count", part_id)

        previous_date = None
        for j, code in enumerate(chosen):
            if previous_date is None:
                eff = fake.date_time_between(start_date="-5y", end_date="-6m")
            else:
                eff = previous_date + timedelta(days=rng.randint(30, 180))
            if previous_date is not None and rng.random() < rates["date_flip"]:
                eff = previous_date - timedelta(days=rng.randint(1, 90))
                _record(defects, "rev_date_flip_count", f"{part_id}:{code}")
            revisions.append(
                {
                    "part_id": part_id,
                    "rev_code": code,
                    "effective_date": eff,
                    "change_summary": fake.sentence(nb_words=rng.randint(6, 20)),
                }
            )
            previous_date = eff
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
    "Élan Components",
]


def generate_suppliers(
    count: int = 400,
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
) -> list[dict]:
    rng = _rng(3)
    fake = _fake(3)
    rates = _rates()
    suppliers = []
    used_codes: set[str] = set()

    for i in range(count):
        base = _BASE_SUPPLIERS[i % len(_BASE_SUPPLIERS)]
        code = f"SUP-{i + 1:04d}"
        if rng.random() < rates["supplier_dupe"] and suppliers:
            source = rng.choice(suppliers)
            source_name = source["name"]
            name = rng.choice(
                [
                    source_name.upper(),
                    source_name.lower(),
                    f"{source_name} Inc.",
                    f"{source_name} LLC",
                    source_name,
                ]
            )
            _record(defects, "supplier_dupe_count", f"{code}->{source['code']}")
        else:
            name = base if i < len(_BASE_SUPPLIERS) else f"{base} Division {i + 1:03d}"

        while code in used_codes:
            code = f"SUP-{rng.randint(1, 9999):04d}"
        used_codes.add(code)

        email = fake.company_email()
        if rng.random() < rates["bad_email"]:
            _record(defects, "bad_email_count", f"SUP-{i + 1:04d}")
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
    part_ids: list[int],
    user_names: list[str],
    count: int = 20000,
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
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
        if state not in CO_STATES_CLEAN:
            _record(defects, "co_state_mess_count", f"CO-{i:06d}")

        opened = fake.date_time_between(start_date="-4y", end_date="-1d")
        closed = None
        if state in ("closed", "CLOSED", "approved", "Approved", "rejected", "REJECTED"):
            closed = opened + timedelta(days=rng.randint(1, 120))
            # Date flip: closed before opened (intentional defect)
            if rng.random() < rates["date_flip"]:
                closed = opened - timedelta(days=rng.randint(1, 30))
                _record(defects, "co_date_flip_count", f"CO-{i:06d}")

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
    supplier_ids: list[int],
    part_ids: list[int],
    count: int = 30000,
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
) -> list[dict]:
    rng = _rng(5)
    fake = _fake(5)
    rates = _rates()
    orders = []
    for i in range(1, count + 1):
        price = round(rng.uniform(0.10, 5000.00), 2)
        # Price magnitude error (intentional defect)
        if rng.random() < rates["price_error"]:
            price = price * rng.choice([100, 0.01, 1000])
            _record(defects, "price_error_count", i)

        currency = rng.choice(CURRENCIES)
        if currency != "USD":
            _record(defects, "currency_mix_count", i)
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


# ── Audit log ────────────────────────────────────────────────────────────────


def generate_audit_log(
    entity_ids: dict[str, list[int]],
    user_names: list[str],
    count: int = 200000,
    *,
    defects: MutableMapping[str, list[str | int]] | None = None,
) -> list[dict]:
    rng = _rng(7)
    fake = _fake(7)
    entities = [name for name, ids in entity_ids.items() if ids]
    rows = []

    for i in range(1, count + 1):
        entity = rng.choice(entities)
        actor = rng.choice(user_names) if user_names and rng.random() > 0.12 else None
        if actor is None:
            _record(defects, "audit_missing_actor_count", i)
        ts = fake.date_time_between(start_date="-4y", end_date="now")

        rows.append(
            {
                "entity": entity,
                "entity_id": rng.choice(entity_ids[entity]),
                "action": rng.choice(AUDIT_ACTIONS),
                "actor": actor,
                "ts": ts,
            }
        )

    return rows
