import logging
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config import config

logger = logging.getLogger(__name__)

class ScamAnalysisResult(BaseModel):
    is_scam: bool = Field(description="Является ли сообщение мошенническим или крайне подозрительным")
    risk_level: str = Field(description="Уровень риска: Низкий (Безопасно), Средний (Подозрительно), Высокий (Опасно), Критический (Мошенничество/Угроза УК)")
    scam_type: str = Field(description="Категория/тип схемы: 'Дропперство / Финансирование экстремизма', 'Покупка игровой валюты / Фишинг', 'Звонок службы безопасности/ФСБ', 'Фейковая работа/инвестиции', 'Бытовой перевод', 'Другое'")
    summary: str = Field(description="Краткий вердикт в 1-2 предложениях простым языком")
    red_flags: list[str] = Field(description="Список тревожных звоночков и признаков манипуляции")
    legal_warning: Optional[str] = Field(default=None, description="Предупреждение об уголовной/юридической ответственности, если схема связана с дропперством, переводами по чужим реквизитам или финансированием запрещенной деятельности")
    recommendations: list[str] = Field(description="Четкие инструкции для пользователя: что делать прямо сейчас")

SYSTEM_INSTRUCTION = """Ты — ведущий эксперт по кибербезопасности, противодействию мошенничеству (Anti-Fraud) и цифровой гигиене.
Твоя задача — анализировать подозрительные входящие сообщения, скриншоты, предложения незнакомцев в мессенджерах/соцсетях и определять признаки мошенничества и криминала.

Особое внимание уделяй схемам:
1. **Дропперство и «серые» переводы денег:**
   - Покупка игровой валюты (Robux, Brawl Stars, CS:GO, Telegram Stars) или крипты, где просят перевести деньги на сторонний номер телефона/карту физлица.
   - Просьбы «принять деньги и переслать дальше за процент».
   - ВНИМАНИЕ: Деньги могут идти на счета террористических/экстремистских организаций, спонсирование противоправной деятельности или обналичивание украденных средств. В таких случаях пользователь рискует стать соучастником уголовного преступления (ст. 205.1 УК РФ, ст. 174 УК РФ и др.)!
2. **Социальная инженерия:**
   - Срочность, давление («прямо сейчас, иначе заблокируют/сгорит скидка»), секретность («никому не говори»), угрозы («звонок из ФСБ/МВД/ЦБ»).
3. **Фишинг и поддельные ссылки:**
   - Поддельные сайты платежей, фейковые гарант-сервисы, формы ввода SMS-кодов или данных карты (CVC/CVV).

Отвечай честно, структурированно, без паники, но с четким предупреждением о последствиях.
"""

class AIService:
    def __init__(self):
        self.client = None
        if config.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=config.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Ошибка инициализации Gemini клиента: {e}")

    def is_configured(self) -> bool:
        return bool(self.client and config.GEMINI_API_KEY)

    async def analyze_text(self, text: str) -> ScamAnalysisResult:
        if not self.is_configured():
            # Если ключ еще не указан, даем тестовый ответ с напоминанием
            return ScamAnalysisResult(
                is_scam=True,
                risk_level="Критический (демо-режим)",
                scam_type="Анализ недоступен (не настроен GEMINI_API_KEY)",
                summary="Бот работает в демонстрационном режиме, так как не указан GEMINI_API_KEY в .env.",
                red_flags=[
                    "В конфигурации отсутствует действующий ключ Google Gemini API",
                    "Для полноценного анализа добавьте GEMINI_API_KEY в файл .env"
                ],
                legal_warning="Помните: любые переводы неизвестным третьим лицам могут сделать вас соучастником преступления (дропперство).",
                recommendations=[
                    "Получите бесплатный API ключ на https://aistudio.google.com/",
                    "Укажите ключ в .env файле проекта и перезапустите бота"
                ]
            )

        try:
            # Запрос к Gemini с принудительной структурированной схемой Pydantic
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=f"Проанализируй следующее сообщение/ситуацию на признаки мошенничества, манипуляций или уголовных рисков (дропперство, финансирование нелегальной деятельности):\n\n\"\"\"\n{text}\n\"\"\"",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=ScamAnalysisResult,
                    temperature=0.2,
                )
            )

            # Парсим JSON-ответ в Pydantic модель
            result = ScamAnalysisResult.model_validate_json(response.text)
            return result
        except Exception as e:
            logger.exception("Ошибка при вызове Gemini API")
            # Запасной вариант при сбое сети или модели
            return ScamAnalysisResult(
                is_scam=True,
                risk_level="Высокий (ошибка обработки)",
                scam_type="Не удалось завершить автоматический анализ",
                summary=f"Произошла ошибка при анализе ИИ: {str(e)[:150]}",
                red_flags=["Не удалось связаться с сервером ИИ для проверки"],
                legal_warning=None,
                recommendations=["Не переводите деньги и не переходите по ссылкам до подтверждения безопасности."]
            )

ai_service = AIService()
