import html
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ai_service import ai_service, ScamAnalysisResult
from keyboards import get_main_keyboard, get_cancel_keyboard, get_actions_keyboard
from database import register_or_update_user, save_message

router = Router()

class CheckState(StatesGroup):
    waiting_for_text = State()

def format_report(result: ScamAnalysisResult) -> str:
    # Иконки для уровней риска
    risk_icons = {
        "Низкий": "🟢",
        "Безопасно": "🟢",
        "Средний": "🟡",
        "Подозрительно": "🟡",
        "Высокий": "🔴",
        "Критический": "⛔️"
    }
    
    icon = "⚠️"
    for k, v in risk_icons.items():
        if k.lower() in result.risk_level.lower():
            icon = v
            break

    flags_text = "\n".join([f"• {html.escape(f)}" for f in result.red_flags])
    recs_text = "\n".join([f"👉 {html.escape(r)}" for r in result.recommendations])

    text = (
        f"<b>{icon} ЭКСПЕРТИЗА БЕЗОПАСНОСТИ</b>\n\n"
        f"<b>Уровень опасности:</b> <code>{html.escape(result.risk_level)}</code>\n"
        f"<b>Тип схемы:</b> <i>{html.escape(result.scam_type)}</i>\n\n"
        f"<b>Резюме:</b>\n{html.escape(result.summary)}\n\n"
    )

    if result.red_flags:
        text += f"<b>🚩 Тревожные признаки:</b>\n{flags_text}\n\n"

    if result.legal_warning:
        text += (
            f"<b>⚖️ ЮРИДИЧЕСКАЯ И УГОЛОВНАЯ ОПАСНОСТЬ:</b>\n"
            f"⚠️ <i>{html.escape(result.legal_warning)}</i>\n\n"
        )

    if result.recommendations:
        text += f"<b>🛡 Что делать:</b>\n{recs_text}"

    return text

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user

    # Получаем аватар пользователя через Telegram Bot API
    has_avatar = False
    avatar_file_id = None
    try:
        user_photos = await message.bot.get_user_profile_photos(user_id=user.id, limit=1)
        if user_photos.total_count > 0 and user_photos.photos:
            has_avatar = True
            # Берем фото в лучшем разрешении (последний элемент в первом наборе)
            avatar_file_id = user_photos.photos[0][-1].file_id
    except Exception:
        pass

    # Регистрируем или обновляем пользователя в базе данных
    is_new_user, visits_count = await register_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        has_avatar=has_avatar,
        avatar_file_id=avatar_file_id
    )

    # Формируем приветствие в зависимости от того, новый пользователь или вернулся
    nick_display = f"@{html.escape(user.username)}" if user.username else html.escape(user.first_name)
    avatar_status = "🖼 Есть аватарка" if has_avatar else "👤 Без аватарки"

    if is_new_user:
        greeting_header = (
            f"👋 Привет, <b>{nick_display}</b>!\n"
            f"<i>Рад знакомству! (Профиль: {avatar_status})</i>\n\n"
        )
    else:
        greeting_header = (
            f"🤝 <b>С возвращением, {nick_display}!</b>\n"
            f"<i>Рады снова тебя видеть! (Визит №{visits_count} | {avatar_status})</i>\n\n"
        )

    welcome_text = (
        greeting_header +
        f"Я — <b>АнтиМошенник (AntiScammer)</b>, твой персональный AI-ассистент по цифровой безопасности.\n\n"
        f"💡 <b>Что я умею:</b>\n"
        f"1. <b>Анализировать подозрительные сообщения</b> с помощью искусственного интеллекта на манипуляции, фишинг и шантаж.\n"
        f"2. <b>Защищать от «дропперства» и серых переводов:</b> когда просят перевести деньги на сторонние номера/карты (например, при покупке игровой валюты, робуксов, скинов), что часто ведет к статьям об экстремизме или отмывании денег.\n"
        f"3. Давать четкие инструкции, как не потерять деньги и не стать соучастником преступления.\n\n"
        f"👇 <i>Отправь мне любой текст сообщения прямо сейчас или выбери кнопку в меню!</i>"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    await save_message(user_id=user.id, sender="bot", text=welcome_text)

@router.message(F.text == "🔍 Проверить текст / схему")
@router.message(Command("check"))
async def start_check_prompt(message: Message, state: FSMContext):
    await state.set_state(CheckState.waiting_for_text)
    prompt_text = (
        "📝 <b>Отправьте подозрительное сообщение или опишите ситуацию:</b>\n\n"
        "<i>Например:\n"
        "— Текст переписки от продавца игровой валюты\n"
        "— Просьбу перевести деньги по номеру телефона третьему лицу\n"
        "— Ссылку на акцию или предложение лёгкого заработка</i>"
    )
    await message.answer(prompt_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await save_message(user_id=message.from_user.id, sender="bot", text=prompt_text)

@router.callback_query(F.data == "start_check")
async def cb_start_check(call: CallbackQuery, state: FSMContext):
    await state.set_state(CheckState.waiting_for_text)
    prompt_text = "📝 <b>Отправьте подозрительное сообщение или опишите ситуацию:</b>"
    await call.message.answer(prompt_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await save_message(user_id=call.from_user.id, sender="bot", text=prompt_text)
    await call.answer()

@router.callback_query(F.data == "cancel_action")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    cancel_text = "❌ Действие отменено."
    await call.message.answer(cancel_text, reply_markup=get_main_keyboard())
    await save_message(user_id=call.from_user.id, sender="bot", text=cancel_text)
    await call.answer()

@router.message(F.text == "🚨 Дропперство и переводы")
async def info_droppers(message: Message):
    text = (
        "🚨 <b>ВНИМАНИЕ: ОПАСНОСТЬ ДРОППЕРСТВА И СТАТЕЙ УК РФ</b>\n\n"
        "Часто мошенники не используют свои карты, а просят вас перевести деньги «на карту человека/по номеру телефона».\n\n"
        "⚠️ <b>В чем реальная опасность:</b>\n"
        "1. <b>Финансирование экстремизма / терроризма:</b>\n"
        "Деньги от покупки игровой валюты или «выгодных обменов» направляются на счета запрещенных организаций. Вы можете оказаться фигурантом уголовного дела (вплоть до 15–20 лет лишения свободы).\n"
        "2. <b>Дропперство (отмывание денег):</b>\n"
        "Мошенники крадут деньги у пенсионеров и прогоняют через вас или просят вас принять/отправить платеж.\n\n"
        "🛑 <b>Золотое правило:</b>\n"
        "Никогда не покупайте ценности (аккаунты, валюту, скины) переводом по СБП/телефону частным неизвестным лицам в мессенджерах!"
    )
    await message.answer(text, reply_markup=get_actions_keyboard(), parse_mode="HTML")
    await save_message(user_id=message.from_user.id, sender="bot", text=text)

@router.message(F.text == "🎮 Схемы в играх (валюта/скины)")
async def info_games(message: Message):
    text = (
        "🎮 <b>СХЕМЫ С ИГРОВОЙ ВАЛЮТОЙ И СКИНАМИ</b>\n"
        "<i>(Robux, Brawl Stars, CS:GO, Telegram Stars, Steam)</i>\n\n"
        "📌 <b>Как работает схема:</b>\n"
        "1. В Telegram/Discord/VK предлагают купить донат или валюту в 2–3 раза дешевле официальной цены.\n"
        "2. «Продавец» просит перевести оплату по номеру телефона на российскую карту/кошелек якобы «поставщика» или «партнера».\n"
        "3. После перевода продавец либо удаляет переписку, либо говорит «платёж не дошёл, нужно повторить».\n"
        "4. Худший сценарий — карта получателя числится в базах МВД/Росфинмониторинга как дропперская или террористическая.\n\n"
        "✅ <b>Защита:</b>\n"
        "• Покупайте валюту только внутри официальных магазинов или проверенных площадок с холдом средств (гарантом).\n"
        "• Если предлагают перевести физлицу по номеру телефона — это 100% скам или криминал!"
    )
    await message.answer(text, reply_markup=get_actions_keyboard(), parse_mode="HTML")
    await save_message(user_id=message.from_user.id, sender="bot", text=text)

@router.message(F.text == "🛡 Памятка безопасности")
async def info_memo(message: Message):
    text = (
        "🛡 <b>ПАМЯТКА ЦИФРОВОЙ БЕЗОПАСНОСТИ</b>\n\n"
        "1. <b>Правило паузы:</b> Вас торопят? Сделайте паузу на 10 минут. Мошенники всегда играют на эмоциях и спешке.\n"
        "2. <b>Никаких SMS-кодов:</b> Коды подтверждения от банков и Госуслуг нельзя сообщать никому, даже «сотрудникам банка».\n"
        "3. <b>Проверка ссылок:</b> Внимательно смотрите на адрес сайта (например, <code>sber-bank.security.com</code> — это фейк, а не sberbank.ru).\n"
        "4. <b>Сомнительные переводы:</b> Не соглашайтесь «принять деньги на карту и перевести другу за вознаграждение».\n\n"
        "<i>Всегда проверяйте сомнительные предложения через нашего бота!</i>"
    )
    await message.answer(text, reply_markup=get_actions_keyboard(), parse_mode="HTML")
    await save_message(user_id=message.from_user.id, sender="bot", text=text)

@router.callback_query(F.data == "what_if_scammed")
async def cb_what_if_scammed(call: CallbackQuery):
    text = (
        "🆘 <b>ЧТО ДЕЛАТЬ, ЕСЛИ ВЫ УЖЕ ПЕРЕВЕЛИ ДЕНЬГИ ИЛИ СООБЩИЛИ ДАННЫЕ:</b>\n\n"
        "1. <b>Срочно позвоните в банк</b> по номеру с обратной стороны карты:\n"
        "— Сообщите о мошеннической операции.\n"
        "— Заблокируйте скомпрометированную карту и доступ в онлайн-банк.\n"
        "2. <b>Зафиксируйте улики:</b>\n"
        "— Сделайте скриншоты переписки, профиля мошенника (с его ID/username), чека перевода.\n"
        "3. <b>Обратитесь в полицию:</b>\n"
        "— Напишите заявление в ближайшем отделении МВД или на официальном сайте мвд.рф.\n"
        "— Обязательно укажите реквизиты, куда ушли деньги (номер карты/телефона), чтобы вас не признали соучастником."
    )
    await call.message.answer(text, parse_mode="HTML")
    await save_message(user_id=call.from_user.id, sender="bot", text=text)
    await call.answer()

@router.message(CheckState.waiting_for_text)
@router.message(F.text)
async def process_user_text(message: Message, state: FSMContext):
    await state.clear()
    
    # Отправляем индикатор "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    waiting_msg = await message.answer("🤖 <i>Анализирую сообщение через нейросеть AntiScammer AI... Пожалуйста, подождите несколько секунд.</i>", parse_mode="HTML")
    
    try:
        report = await ai_service.analyze_text(message.text)
        formatted_text = format_report(report)
        await waiting_msg.edit_text(formatted_text, reply_markup=get_actions_keyboard(), parse_mode="HTML")
        await save_message(user_id=message.from_user.id, sender="bot", text=formatted_text)
    except Exception as e:
        error_msg = f"❌ Не удалось завершить анализ: {html.escape(str(e))}\n\nПопробуйте ещё раз позже."
        await waiting_msg.edit_text(
            error_msg,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        await save_message(user_id=message.from_user.id, sender="bot", text=error_msg)

