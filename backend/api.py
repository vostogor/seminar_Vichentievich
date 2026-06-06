from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.database import (
    init_db,
    get_user_profile,
    get_all_profiles,
    save_user_profile,
)
from backend.ai_generator import generate_training_with_ai


app = FastAPI(title="Training Bot API")


class UserProfileRequest(BaseModel):
    telegram_id: int
    age: str
    level: str
    vo2max: float | None = None
    pace_seconds: int


class WorkoutRequest(BaseModel):
    telegram_id: int
    workout_type: str


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Сервер работает!"}


@app.get("/users")
def get_users():
    users = get_all_profiles()

    return [
        {
            "telegram_id": user.telegram_id,
            "age": user.age,
            "level": user.level,
            "vo2max": user.vo2max,
            "pace_seconds": user.pace_seconds,
        }
        for user in users
    ]


@app.get("/users/{telegram_id}")
def get_user(telegram_id: int):
    user = get_user_profile(telegram_id)

    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "telegram_id": user.telegram_id,
        "age": user.age,
        "level": user.level,
        "vo2max": user.vo2max,
        "pace_seconds": user.pace_seconds,
    }


@app.post("/users")
def create_or_update_user(profile: UserProfileRequest):
    user = save_user_profile(
        telegram_id=profile.telegram_id,
        age=profile.age,
        level=profile.level,
        vo2max=profile.vo2max,
        pace_seconds=profile.pace_seconds,
    )

    return {
        "message": "Анкета сохранена",
        "telegram_id": user.telegram_id,
    }


@app.post("/workout")
def generate_workout(request: WorkoutRequest):
    user = get_user_profile(request.telegram_id)

    if user is None:
        raise HTTPException(status_code=404, detail="Сначала заполните анкету")

    workout = generate_training_with_ai(
        profile=user,
        workout_type=request.workout_type,
    )

    return {
        "telegram_id": request.telegram_id,
        "workout_type": request.workout_type,
        "workout": workout,
    }