"""Keyboards and the button labels the handlers match on."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_WRITE = "✍️ Писать работу"
BTN_TECH = "🧮 Задачи и код"
BTN_EDIT = "📝 Редактор и перевод"
BTN_CHEAT = "🎓 Шпаргалки и экзамен"
BTN_SUB = "💎 Подписка"
BTN_NEW = "🧹 Новый диалог"

MODE_BUTTONS = {BTN_WRITE: "writer", BTN_TECH: "tech", BTN_EDIT: "editor"}

MODE_TITLES = {
    "general": "Свободный режим",
    "writer": "Академический писатель",
    "tech": "Технический эксперт",
    "editor": "Редактор и переводчик",
    "cheat": "Шпаргалка",
    "exam": "Вредный преподаватель",
}

MODE_INTRO = {
    "writer": ("✍️ <b>Академический писатель</b>\n\nПомогу с курсовой, рефератом, эссе или дипломной: план, оглавление, введение, "
               "главы, выводы, список литературы.\n\nНапишите тему и, если знаете, объём и стандарт оформления вуза. "
               "Например: <i>«Курсовая по маркетингу, тема: digital-стратегии ресторанов, 30 страниц, ГОСТ»</i>."),
    "tech": ("🧮 <b>Технический эксперт</b>\n\nРешаю задачи по математике, физике, экономике и программированию "
             "с пошаговым объяснением. Код пишу рабочим, с комментариями и инструкцией запуска.\n\nПришлите условие задачи или текст задания."),
    "editor": ("📝 <b>Редактор и переводчик</b>\n\nПроверю орфографию и логику, сделаю академический рерайт без потери смысла, "
               "переведу научный текст с сохранением терминологии.\n\nПришлите текст или файл (.txt, .pdf, .docx) и напишите, что сделать."),
    "cheat": ("📋 <b>Шпаргалка</b>\n\nПришлите конспект, лекцию или файл (.txt, .pdf, .docx), и я сделаю краткую выжимку: "
              "определения, формулы, ключевые мысли."),
    "exam": ("😈 <b>Вредный преподаватель</b>\n\nПришлите тему или текст курсовой, и я буду задавать каверзные вопросы по одному, "
             "как на защите. Отвечайте, а я скажу, что слабо.\n\nЧтобы начать, напишите: <i>«Начинай»</i> и дайте тему работы."),
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_WRITE), KeyboardButton(text=BTN_TECH)],
                  [KeyboardButton(text=BTN_EDIT), KeyboardButton(text=BTN_CHEAT)],
                  [KeyboardButton(text=BTN_SUB), KeyboardButton(text=BTN_NEW)]],
        resize_keyboard=True, input_field_placeholder="Напишите вопрос или пришлите файл")


def cheat_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Шпаргалка из материала", callback_data="mode:cheat")],
        [InlineKeyboardButton(text="😈 Вредный преподаватель", callback_data="mode:exam")]])


def subscribe_button(label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="pay")]])
