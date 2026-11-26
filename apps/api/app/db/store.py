import time
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import JSON, String, create_engine, delete, func, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    state: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    group: Mapped[str | None] = mapped_column(String(10))
    review_group: Mapped[str | None] = mapped_column(String(10))
    risk: Mapped[str] = mapped_column(String(10))
    signals: Mapped[list] = mapped_column(JSON)
    created: Mapped[int] = mapped_column(default=lambda: int(time.time()))
    revision: Mapped[int] = mapped_column(default=1)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reporter: Mapped[str] = mapped_column(String(64), index=True)
    campaign: Mapped[str] = mapped_column(String(32), index=True)
    created: Mapped[int] = mapped_column(default=lambda: int(time.time()))
    snapshot: Mapped[dict] = mapped_column(JSON)


class Entity(Base):
    __tablename__ = "campaign_entities"
    campaign: Mapped[str] = mapped_column(String(32), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(12))


class Audit(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign: Mapped[str] = mapped_column(String(32), index=True)
    actor: Mapped[str] = mapped_column(String(254))
    action: Mapped[str] = mapped_column(String(16))
    created: Mapped[int] = mapped_column(default=lambda: int(time.time()))


class Login(Base):
    __tablename__ = "sessions"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(8))
    expires: Mapped[int] = mapped_column(index=True)


LEVELS = {"low": 0, "uncertain": 1, "medium": 2, "high": 3}


class Store:
    def __init__(self, url):
        if url.startswith(("postgres://", "postgresql://")):
            url = "postgresql+psycopg://" + url.split("://", 1)[1]
        self.engine = create_engine(url, pool_pre_ping=True)
        if self.engine.dialect.name == "postgresql":
            self.engine = self.engine.execution_options(schema_translate_map={None: "tkc"})

    @contextmanager
    def write(self):
        with Session(self.engine) as session:
            if self.engine.dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            elif self.engine.dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(7042026)"))
            yield session
            session.commit()

    def matches(self, digests):
        if not digests:
            return False
        with Session(self.engine) as session:
            query = select(Entity.digest).join(Campaign, Campaign.id == Entity.campaign)
            return session.scalar(query.where(
                Campaign.state == "approved", Entity.digest.in_(digests)
            ).limit(1)) is not None

    @staticmethod
    def rebuild(session, campaign, snapshots):
        keys = {}
        signals = {}
        strongest = max(snapshots, key=lambda row: LEVELS[row["risk"]])
        for row in snapshots:
            keys.update(row["keys"])
            for signal in row["signals"]:
                signals[signal] = None
        session.execute(delete(Entity).where(Entity.campaign == campaign.id))
        session.add_all(Entity(campaign=campaign.id, digest=key, kind=kind) for key, kind in keys.items())
        campaign.risk = strongest["risk"]
        campaign.group = strongest["group"]
        campaign.signals = list(signals)[:8]

    def report(self, claim, reporter):
        with self.write() as session:
            existing = session.get(Report, claim["id"])
            if existing:
                return existing.campaign if existing.reporter == reporter else None
            keys = claim["keys"]
            query = (
                select(Campaign).join(Entity, Campaign.id == Entity.campaign)
                .where(Campaign.state == "pending", Entity.digest.in_(keys))
                .order_by(Campaign.created, Campaign.id)
            )
            candidates = list(session.scalars(query).unique()) if keys else []
            if candidates:
                campaign = next((item for item in candidates if item.review_group), candidates[0])
                campaign.revision += 1
                merged = [item.id for item in candidates if item is not campaign and not item.review_group]
                if merged:
                    session.execute(update(Report).where(Report.campaign.in_(merged)).values(campaign=campaign.id))
                    session.execute(delete(Entity).where(Entity.campaign.in_(merged)))
                    session.execute(delete(Campaign).where(Campaign.id.in_(merged)))
            else:
                campaign = Campaign(group=claim["group"], risk=claim["risk"], signals=[])
                session.add(campaign)
                session.flush()
            snapshot = {field: claim[field] for field in ("keys", "risk", "group", "signals")}
            snapshots = list(session.scalars(select(Report.snapshot).where(Report.campaign == campaign.id)))
            self.rebuild(session, campaign, snapshots + [snapshot])
            session.add(Report(id=claim["id"], reporter=reporter, campaign=campaign.id, snapshot=snapshot))
            return campaign.id

    def delete_reports(self, reporter):
        with self.write() as session:
            ids = set(session.scalars(select(Report.campaign).where(Report.reporter == reporter)))
            removed = session.execute(delete(Report).where(Report.reporter == reporter)).rowcount
            for campaign_id in ids:
                campaign = session.get(Campaign, campaign_id)
                snapshots = list(session.scalars(select(Report.snapshot).where(Report.campaign == campaign_id)))
                if snapshots:
                    self.rebuild(session, campaign, snapshots)
                    campaign.revision += 1
                else:
                    session.execute(delete(Entity).where(Entity.campaign == campaign_id))
                    if campaign.state == "pending" and not campaign.review_group:
                        session.delete(campaign)
                    else:
                        if campaign.state == "pending":
                            campaign.state = "rejected"
                        campaign.signals = []
                        campaign.group = None
                        campaign.review_group = None
                        campaign.risk = "uncertain"
                        campaign.revision += 1
            return removed

    def campaigns(self, state):
        with Session(self.engine) as session:
            query = select(Campaign).order_by(Campaign.created.desc(), Campaign.id).limit(100)
            if state:
                query = query.where(Campaign.state == state)
            return [self.describe(session, campaign) for campaign in session.scalars(query)]

    def campaign(self, campaign_id):
        with Session(self.engine) as session:
            campaign = session.get(Campaign, campaign_id)
            return self.describe(session, campaign) if campaign else None

    @staticmethod
    def describe(session, campaign):
        report_count = session.scalar(select(func.count()).select_from(Report).where(Report.campaign == campaign.id))
        kinds = session.scalars(select(Entity.kind).where(Entity.campaign == campaign.id)).all()
        history = session.scalars(select(Audit).where(Audit.campaign == campaign.id).order_by(Audit.id))
        return {
            "id": campaign.id, "state": campaign.state, "group": campaign.review_group or campaign.group,
            "risk": campaign.risk, "signals": campaign.signals, "created": campaign.created,
            "revision": campaign.revision, "report_count": report_count,
            "entities": {kind: kinds.count(kind) for kind in sorted(set(kinds))},
            "history": [{"actor": row.actor, "action": row.action, "created": row.created} for row in history],
        }

    def review(self, campaign_id, actor, action, revision, group=None):
        with self.write() as session:
            campaign = session.get(Campaign, campaign_id)
            if campaign is None or campaign.state != "pending" or revision != campaign.revision:
                return None
            if action == "edit_group":
                campaign.review_group = group
            else:
                campaign.state = {"approve": "approved", "reject": "rejected"}[action]
            campaign.revision += 1
            session.add(Audit(campaign=campaign_id, actor=actor, action=action))
            session.flush()
            return self.describe(session, campaign)
