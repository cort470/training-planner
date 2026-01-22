"""
SQLAlchemy Database Models for Training Planner

Provides persistent storage for:
- Athlete profiles and Strava OAuth tokens
- Training plan records and planned sessions
- Completed activities from Strava
- Activity-to-plan adherence tracking
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session

Base = declarative_base()


class Athlete(Base):
    """
    User account with optional Strava integration.

    Attributes:
        id: Primary key
        athlete_id: Unique identifier matching UserProfile.athlete_id
        strava_athlete_id: Strava's athlete ID (null if not connected)
        strava_access_token: OAuth access token (should be encrypted)
        strava_refresh_token: OAuth refresh token (should be encrypted)
        strava_token_expires_at: When the access token expires
        last_strava_sync: Last successful activity sync timestamp
        created_at: Account creation timestamp
    """

    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(String, unique=True, nullable=False, index=True)
    strava_athlete_id = Column(Integer, nullable=True, unique=True)
    strava_access_token = Column(String, nullable=True)
    strava_refresh_token = Column(String, nullable=True)
    strava_token_expires_at = Column(DateTime, nullable=True)
    last_strava_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    profiles = relationship("ProfileSnapshot", back_populates="athlete", cascade="all, delete-orphan")
    plans = relationship("TrainingPlanRecord", back_populates="athlete", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="athlete", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Athlete(athlete_id='{self.athlete_id}', strava_connected={self.strava_athlete_id is not None})>"


class ProfileSnapshot(Base):
    """
    Versioned snapshots of user profiles.

    Enables tracking profile changes over time and analyzing
    how athlete state evolves during training.

    Attributes:
        id: Primary key
        athlete_id: Foreign key to athletes table
        profile_date: Date this profile snapshot represents
        profile_data: Full UserProfile as JSON
        created_at: When this snapshot was saved
    """

    __tablename__ = "profile_snapshots"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    profile_date = Column(DateTime, nullable=False, index=True)
    profile_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    athlete = relationship("Athlete", back_populates="profiles")

    def __repr__(self):
        return f"<ProfileSnapshot(athlete_id={self.athlete_id}, profile_date='{self.profile_date}')>"


class TrainingPlanRecord(Base):
    """
    Saved training plans with metadata.

    Stores complete generated plans and enables adherence tracking
    by linking planned sessions to actual activities.

    Attributes:
        id: Primary key
        athlete_id: Foreign key to athletes table
        methodology_id: ID of methodology used (e.g., 'polarized_80_20_v1')
        plan_start_date: When the plan begins
        plan_duration_weeks: Total plan length
        fragility_score: Calculated risk score
        plan_data: Full TrainingPlan as JSON
        created_at: When this plan was generated
        is_active: Whether this is the athlete's current active plan
    """

    __tablename__ = "training_plans"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    methodology_id = Column(String, nullable=False)
    plan_start_date = Column(DateTime, nullable=False, index=True)
    plan_duration_weeks = Column(Integer, nullable=False)
    fragility_score = Column(Float, nullable=False)
    plan_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    athlete = relationship("Athlete", back_populates="plans")
    sessions = relationship("PlannedSession", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TrainingPlanRecord(id={self.id}, methodology='{self.methodology_id}', weeks={self.plan_duration_weeks}, active={self.is_active})>"


class PlannedSession(Base):
    """
    Individual planned workout sessions.

    Extracted from training plans to enable granular adherence tracking.
    Links to Activity table to compare planned vs. actual workouts.

    Attributes:
        id: Primary key
        plan_id: Foreign key to training_plans table
        week_number: Week number within the plan (1-indexed)
        day_of_week: Day name ('monday', 'tuesday', etc.)
        scheduled_date: Calculated date for this session
        session_type: Workout type ('run', 'bike', 'swim', etc.)
        primary_zone: Target intensity zone
        duration_minutes: Planned duration
        description: Workout description
        workout_details: Structured workout details (intervals, etc.)
    """

    __tablename__ = "planned_sessions"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False)
    day_of_week = Column(String, nullable=False)
    scheduled_date = Column(DateTime, nullable=True, index=True)
    session_type = Column(String, nullable=False)
    primary_zone = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    workout_details = Column(JSON, nullable=True)

    # Relationships
    plan = relationship("TrainingPlanRecord", back_populates="sessions")
    activities = relationship("Activity", back_populates="planned_session")

    def __repr__(self):
        return f"<PlannedSession(week={self.week_number}, day='{self.day_of_week}', type='{self.session_type}', zone='{self.primary_zone}')>"


class Activity(Base):
    """
    Completed workouts from Strava or manual entry.

    Links to PlannedSession to enable adherence tracking.
    Stores performance metrics for overtraining detection.

    Attributes:
        id: Primary key
        athlete_id: Foreign key to athletes table
        planned_session_id: Foreign key to planned_sessions (null if unplanned)
        strava_activity_id: Strava's unique activity ID
        activity_date: When the activity occurred
        activity_type: Type from Strava ('Run', 'Ride', 'Swim', etc.)
        name: Activity title
        description: User's activity notes (for sentiment analysis)
        duration_seconds: Total duration
        distance_meters: Total distance
        elevation_gain_meters: Total elevation gain
        average_heartrate: Average HR (bpm)
        max_heartrate: Maximum HR (bpm)
        average_power: Average power (watts)
        normalized_power: Normalized power (watts)
        average_pace: Average pace (seconds per km/mile)
        perceived_zone: Inferred intensity zone from metrics
        adherence_score: 0-1 score comparing to planned session
        data_source: Source of activity ('strava', 'manual', 'import')
        raw_data: Full Strava API response
        created_at: When this activity was saved
    """

    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    planned_session_id = Column(Integer, ForeignKey("planned_sessions.id"), nullable=True, index=True)

    # Strava fields
    strava_activity_id = Column(Integer, nullable=True, unique=True, index=True)
    activity_date = Column(DateTime, nullable=False, index=True)
    activity_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Performance metrics
    duration_seconds = Column(Integer, nullable=False)
    distance_meters = Column(Float, nullable=True)
    elevation_gain_meters = Column(Float, nullable=True)
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Float, nullable=True)
    average_power = Column(Float, nullable=True)
    normalized_power = Column(Float, nullable=True)
    average_pace = Column(Float, nullable=True)

    # Computed fields
    perceived_zone = Column(String, nullable=True)
    adherence_score = Column(Float, nullable=True)

    # Metadata
    data_source = Column(String, default="strava", nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    athlete = relationship("Athlete", back_populates="activities")
    planned_session = relationship("PlannedSession", back_populates="activities")

    def __repr__(self):
        return f"<Activity(id={self.id}, type='{self.activity_type}', date='{self.activity_date}', duration={self.duration_seconds}s)>"


# Database connection and session management

def get_engine(database_url: str = "sqlite:///training_planner.db"):
    """
    Create SQLAlchemy engine.

    Args:
        database_url: Database connection string (default: SQLite file)

    Returns:
        SQLAlchemy Engine instance
    """
    return create_engine(database_url, echo=False)


def get_session_factory(engine):
    """
    Create session factory.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        Session factory (sessionmaker)
    """
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_database(database_url: str = "sqlite:///training_planner.db") -> Session:
    """
    Initialize database and create all tables.

    Args:
        database_url: Database connection string

    Returns:
        SQLAlchemy Session instance
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    SessionFactory = get_session_factory(engine)
    return SessionFactory()


def get_db_session(database_url: str = "sqlite:///training_planner.db"):
    """
    Dependency for FastAPI to get database session.

    Yields:
        SQLAlchemy Session instance

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db_session)):
            ...
    """
    engine = get_engine(database_url)
    SessionFactory = get_session_factory(engine)
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
