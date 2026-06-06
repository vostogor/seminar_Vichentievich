from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "sqlite:///training_bot.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)

    age = Column(String, nullable=True)
    level = Column(String, nullable=True)
    vo2max = Column(Float, nullable=True)
    pace_seconds = Column(Integer, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def save_user_profile(
    telegram_id: int,
    age: str,
    level: str,
    vo2max: float | None,
    pace_seconds: int
):
    db = SessionLocal()

    try:
        profile = db.query(UserProfile).filter(
            UserProfile.telegram_id == telegram_id
        ).first()

        if profile is None:
            profile = UserProfile(
                telegram_id=telegram_id,
                age=age,
                level=level,
                vo2max=vo2max,
                pace_seconds=pace_seconds
            )
            db.add(profile)
        else:
            profile.age = age
            profile.level = level
            profile.vo2max = vo2max
            profile.pace_seconds = pace_seconds

        db.commit()
        db.refresh(profile)
        return profile

    finally:
        db.close()


def get_user_profile(telegram_id: int):
    db = SessionLocal()

    try:
        return db.query(UserProfile).filter(
            UserProfile.telegram_id == telegram_id
        ).first()

    finally:
        db.close()


def delete_user_profile(telegram_id: int):
    db = SessionLocal()

    try:
        profile = db.query(UserProfile).filter(
            UserProfile.telegram_id == telegram_id
        ).first()

        if profile:
            db.delete(profile)
            db.commit()

    finally:
        db.close()


def get_all_profiles():
    db = SessionLocal()

    try:
        return db.query(UserProfile).all()

    finally:
        db.close()