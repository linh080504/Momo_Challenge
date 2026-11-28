import time

from sqlalchemy import JSON, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..evidence.brand_check import describe_brand
from .store import Base

ALERT_TTL_SECONDS = 30 * 86400


class BrandCase(Base):
    __tablename__ = "brand_cases"
    host: Mapped[str] = mapped_column(String(253), primary_key=True)
    state: Mapped[str] = mapped_column(String(16), index=True)
    revision: Mapped[int]
    sources: Mapped[dict] = mapped_column(JSON)
    assessment: Mapped[dict] = mapped_column(JSON)
    created: Mapped[int]
    updated: Mapped[int]
    expires: Mapped[int | None]


class BrandDecision(Base):
    __tablename__ = "brand_decisions"
    __table_args__ = (UniqueConstraint("host", "revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(253))
    revision: Mapped[int]
    decision: Mapped[str] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(254))
    created: Mapped[int]


def describe(row):
    return {
        "host": row.host, "state": row.state, "revision": row.revision, "sources": row.sources,
        "assessment": describe_brand(row.assessment), "created": row.created, "updated": row.updated,
        "expires": row.expires,
    }


def ingest(store, entries, source):
    now = int(time.time())
    created = 0
    updated = 0
    with store.write() as session:
        for host, assessment in entries.items():
            row = session.get(BrandCase, host)
            if row is None:
                session.add(BrandCase(host=host, state="pending", revision=1, sources={source: now},
                                      assessment=assessment, created=now, updated=now, expires=None))
                created += 1
            elif source not in row.sources:
                row.sources = {**row.sources, source: now}
                row.revision += 1
                row.updated = now
                updated += 1
    return {"created": created, "updated": updated, "matched": len(entries)}


def set_evidence(store, host, assessment, revision):
    with store.write() as session:
        row = session.get(BrandCase, host)
        if row is None or row.revision != revision or row.state == "approved":
            return None
        if row.assessment != assessment:
            row.state = "pending"
            row.assessment = assessment
            row.revision += 1
            row.updated = int(time.time())
        return describe(row)


def decide(store, host, decision, revision, actor):
    with store.write() as session:
        row = session.get(BrandCase, host)
        if row is None or row.revision != revision:
            return None
        allowed = (
            decision == "approve" and row.state == "pending" and row.assessment["verdict"] == "IMPOSTOR"
            or decision == "reject" and row.state == "pending"
            or decision == "revoke" and row.state == "approved"
        )
        if not allowed:
            return None
        now = int(time.time())
        row.state = {"approve": "approved", "reject": "rejected", "revoke": "pending"}[decision]
        row.expires = now + ALERT_TTL_SECONDS if decision == "approve" else None
        row.revision += 1
        row.updated = now
        session.add(BrandDecision(host=host, revision=row.revision, actor=actor, decision=decision, created=now))
        return describe(row)


def matching(store, hosts):
    if not hosts:
        return set()
    with Session(store.engine) as session:
        return set(session.scalars(select(BrandCase.host).where(
            BrandCase.host.in_(hosts), BrandCase.state == "approved", BrandCase.expires > int(time.time()),
        )))


def page(store, state, after=""):
    with Session(store.engine) as session:
        query = select(BrandCase).where(BrandCase.state == state, BrandCase.host > after).order_by(BrandCase.host)
        rows = list(session.scalars(query.limit(51)))
        return {"items": [describe(row) for row in rows[:50]], "next_cursor": rows[49].host if len(rows) > 50 else None}


def dossier(store, host):
    with Session(store.engine) as session:
        row = session.get(BrandCase, host)
        if row is None:
            return None
        events = session.scalars(select(BrandDecision).where(BrandDecision.host == host).order_by(BrandDecision.revision))
        return {**describe(row), "decisions": [{"decision": item.decision, "revision": item.revision,
                                                "created": item.created} for item in events]}
