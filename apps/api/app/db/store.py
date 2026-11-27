import time
from collections import Counter
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import JSON, String, UniqueConstraint, create_engine, delete, func, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, aliased, mapped_column


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


class SampleReview(Base):
    __tablename__ = "sample_reviews"
    __table_args__ = (UniqueConstraint("report", "revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    report: Mapped[str] = mapped_column(String(64), index=True)
    campaign: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(254))
    label: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column()
    created: Mapped[int] = mapped_column(default=lambda: int(time.time()))


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

    def ready(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

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
                split_cases = set(session.scalars(select(Audit.campaign).where(
                    Audit.campaign.in_([item.id for item in candidates]), Audit.action == "split_sample"
                )))
                merged = [item.id for item in candidates if item is not campaign and not item.review_group
                          and item.id not in split_cases and campaign.id not in split_cases]
                if merged:
                    session.execute(update(Report).where(Report.campaign.in_(merged)).values(campaign=campaign.id))
                    session.execute(delete(Entity).where(Entity.campaign.in_(merged)))
                    session.execute(delete(Campaign).where(Campaign.id.in_(merged)))
            else:
                campaign = Campaign(group=claim["group"], risk=claim["risk"], signals=[])
                session.add(campaign)
                session.flush()
            snapshot = {field: claim[field] for field in ("keys", "risk", "group", "signals")}
            snapshot["inputs"] = claim.get("inputs", [])
            snapshot["forensics"] = claim.get("forensics", {})
            snapshot["sources"] = claim.get("sources", [])
            snapshots = list(session.scalars(select(Report.snapshot).where(Report.campaign == campaign.id)))
            self.rebuild(session, campaign, snapshots + [snapshot])
            session.add(Report(id=claim["id"], reporter=reporter, campaign=campaign.id, snapshot=snapshot))
            return campaign.id

    def delete_reports(self, reporter):
        with self.write() as session:
            ids = set(session.scalars(select(Report.campaign).where(Report.reporter == reporter)))
            owned = select(Report.id).where(Report.reporter == reporter)
            session.execute(delete(SampleReview).where(SampleReview.report.in_(owned)))
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

    def overview(self):
        since = int(time.time()) - 86400
        with Session(self.engine) as session:
            reports = session.scalar(select(func.count()).select_from(Report).where(Report.created >= since))
            counts = dict(session.execute(select(Campaign.state, func.count())
                                          .group_by(Campaign.state)).tuples().all())
            decisions = session.scalar(select(func.count()).select_from(Audit).where(
                Audit.created >= since, Audit.action.in_(("approve", "reject"))))
            return {"reports_24h": reports, "decisions_24h": decisions,
                    "pending": counts.get("pending", 0), "approved": counts.get("approved", 0)}

    def campaign_samples(self, campaign_id, after=""):
        with Session(self.engine) as session:
            if session.get(Campaign, campaign_id) is None:
                return None
            reports = list(session.scalars(select(Report).where(Report.campaign == campaign_id, Report.id > after)
                                           .order_by(Report.id).limit(51)))
            ids = [report.id for report in reports[:50]]
            reviews = {}
            query = (select(SampleReview).where(SampleReview.report.in_(ids))
                     .order_by(SampleReview.id))
            for row in session.scalars(query):
                reviews.setdefault(row.report, []).append({"label": row.label, "revision": row.revision,
                                                           "created": row.created, "actor": row.actor})
            return {"samples": [{"id": report.id, "created": report.created,
                                 **{key: report.snapshot.get(key) for key in ("risk", "group", "signals", "inputs")},
                                 "history": reviews.get(report.id, [])}
                                for report in reports[:50]],
                    "next_cursor": ids[-1] if len(reports) > 50 else None}

    def label_sample(self, campaign_id, report_id, actor, label, revision):
        with self.write() as session:
            report = session.get(Report, report_id)
            if report is None or report.campaign != campaign_id:
                return None
            latest = session.scalar(select(SampleReview).where(SampleReview.report == report_id)
                                    .order_by(SampleReview.id.desc()).limit(1))
            if revision != (latest.revision if latest else 0):
                return None
            item = SampleReview(report=report_id, campaign=campaign_id, actor=actor,
                                label=label, revision=revision + 1)
            session.add(item)
            session.flush()
            return {"label": item.label, "revision": item.revision, "actor": item.actor, "created": item.created}

    def split_sample(self, campaign_id, report_id, actor, revision):
        with self.write() as session:
            original = session.get(Campaign, campaign_id)
            report = session.get(Report, report_id)
            if (original is None or original.state != "pending" or original.revision != revision
                    or report is None or report.campaign != campaign_id):
                return None
            remaining = list(session.scalars(select(Report.snapshot).where(
                Report.campaign == campaign_id, Report.id != report_id)))
            if not remaining:
                return None
            split = Campaign(group=report.snapshot["group"], risk=report.snapshot["risk"], signals=[])
            session.add(split)
            session.flush()
            report.campaign = split.id
            original.revision += 1
            self.rebuild(session, original, remaining)
            self.rebuild(session, split, [report.snapshot])
            session.add_all(Audit(campaign=case, actor=actor, action="split_sample") for case in (campaign_id, split.id))
            return {"campaign_id": split.id, "previous_revision": original.revision}

    def reviewed_sample_export(self, after=""):
        with Session(self.engine) as session:
            current = aliased(SampleReview)
            latest_id = (select(func.max(current.id)).where(current.report == Report.id)
                         .correlate(Report).scalar_subquery())
            query = (select(Report, SampleReview).join(SampleReview, SampleReview.id == latest_id)
                     .where(Report.id > after, SampleReview.label.in_(("scam", "legit")))
                     .order_by(Report.id).limit(501))
            rows = session.execute(query).all()
            return {
                "schema_version": 1,
                "purpose": "reviewed_signals",
                "samples": [{"id": report.id, "group_id": report.campaign, "label": review.label,
                             "label_revision": review.revision, "reviewed_at": review.created,
                             "inputs": report.snapshot.get("inputs", []),
                             "signals": report.snapshot.get("signals", [])}
                            for report, review in rows[:500]],
                "next_cursor": rows[499][0].id if len(rows) > 500 else None,
            }

    def campaign_investigation(self, campaign_id):
        with Session(self.engine) as session:
            campaign = session.get(Campaign, campaign_id)
            if campaign is None:
                return None
            detail = self.describe(session, campaign)
            snapshots = session.execute(select(Report.snapshot, Report.created).where(Report.campaign == campaign_id)
                                        .order_by(Report.created.desc(), Report.id).limit(500))
            inputs = Counter()
            connections = Counter()
            connection_times = {}
            forensics = Counter()
            sources = Counter()
            for snapshot, created in snapshots:
                modalities = set(snapshot.get("inputs", ()))
                inputs.update(modalities)
                kinds = set(snapshot["keys"].values())
                for edge in ((kind, modality) for kind in kinds for modality in modalities):
                    connections[edge] += 1
                    connection_times.setdefault(edge, created)
                forensics.update(snapshot.get("forensics", {}))
                sources.update(snapshot.get("sources", ()))

            own = aliased(Entity)
            shared = func.count(Entity.digest).label("shared")
            query = (select(Campaign.id, Campaign.state, shared)
                     .join(Entity, Campaign.id == Entity.campaign)
                     .join(own, own.digest == Entity.digest)
                     .where(own.campaign == campaign_id, Campaign.id != campaign_id,
                            Campaign.state.in_(("pending", "approved")))
                     .group_by(Campaign.id, Campaign.state)
                     .order_by(shared.desc(), Campaign.id).limit(8))
            related = [{"id": row.id, "state": row.state, "shared_entities": row.shared}
                       for row in session.execute(query)]
            return detail, {"inputs": dict(inputs), "connections": connections, "related": related,
                            "connection_times": connection_times, "media_evidence": dict(forensics),
                            "source_counts": dict(sources)}

    def verified_feedback(self):
        with Session(self.engine) as session:
            has_reports = select(Report.id).where(Report.campaign == Campaign.id).exists()
            query = (select(Campaign).where(Campaign.state == "approved", has_reports)
                     .order_by(Campaign.created.desc(), Campaign.id).limit(500))
            return [{"campaign_id": row.id, "revision": row.revision,
                     "group": row.review_group or row.group, "signals": row.signals,
                     "review_label": "approved_campaign"} for row in session.scalars(query)]

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
