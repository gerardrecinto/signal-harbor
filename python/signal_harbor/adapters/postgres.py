from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class SignalOrm(Base):
    __tablename__ = "signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name = Column(String, nullable=False, index=True)
    environment = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=False)


class PostgresSignalRepository:
    # LSP: implements both SignalReader and SignalWriter — any downstream using either
    #      Protocol can substitute this class without knowing it's Postgres under the hood
    # DIP: it satisfies the Protocol contracts; callers depend on the ports, not this class

    def __init__(self, session_factory: sessionmaker) -> None:
        # DIP: receives the session factory rather than constructing its own engine
        self._session_factory = session_factory

    # --- SignalWriter ---
    def save(self, signal: dict) -> dict:
        # SRP: write path only — no query logic lives here
        with self._session_factory() as session:
            orm = SignalOrm(
                id=str(uuid.uuid4()),
                service_name=signal["service_name"],
                environment=signal["environment"],
                signal_type=signal["signal_type"],
                severity=signal["severity"],
                observed_at=signal["observed_at"],
                summary=signal["summary"],
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_dict(orm)

    # --- SignalReader ---
    def find_by_service_after(self, service_name: str, after: datetime) -> list[dict]:
        # SRP: read path only — no mutation logic lives here
        with self._session_factory() as session:
            rows = (
                session.query(SignalOrm)
                .filter(
                    SignalOrm.service_name == service_name,
                    SignalOrm.observed_at >= after,
                )
                .all()
            )
            return [_to_dict(r) for r in rows]


def _to_dict(orm: SignalOrm) -> dict:
    return {
        "id": orm.id,
        "service_name": orm.service_name,
        "environment": orm.environment,
        "signal_type": orm.signal_type,
        "severity": orm.severity,
        "observed_at": orm.observed_at,
        "summary": orm.summary,
    }


def build_session_factory(database_url: str) -> sessionmaker:
    connect_args: dict = {}
    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False
        if "uri=true" in database_url:
            connect_args["uri"] = True
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
