import os
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_pace(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


def generate_training_with_ai(profile, workout_type: str) -> str:
    vo2_text = (
        str(profile.vo2max)
        if profile.vo2max is not None
        else "не указан"
    )

    prompt = f"""
Сгенерируй тренировку по плаванию на русском языке.

Данные пользователя:
- возрастная категория: {profile.age}
- уровень плавания: {profile.level}
- VO2max: {vo2_text}
- средняя скорость на 100 м: {format_pace(profile.pace_seconds)}
- тип тренировки: {workout_type}

Требования:
1. Тренировка должна быть безопасной.
2. Учитывай уровень пловца.
3. Учитывай возрастную категорию.
4. Учитывай текущий темп на 100 м.
5. Структура ответа:
   - краткое описание цели тренировки;
   - разминка;
   - основная часть;
   - заминка;
   - рекомендации по безопасности.
6. Не делай слишком длинный ответ.
7. Если тип тренировки — гипоксия, обязательно добавь предупреждение, что нельзя выполнять задержки дыхания в одиночку.
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return response.output_text