from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def draft_keyboard(draft_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для готового черновика (текст + фото)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"draft:publish:{draft_id}"),
                InlineKeyboardButton(text="🖼 Другое фото", callback_data=f"draft:rephoto:{draft_id}"),
            ],
            [
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"draft:edit:{draft_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"draft:reject:{draft_id}"),
            ],
        ]
    )


def text_only_keyboard(draft_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для черновика, который ещё ждёт фото от владельца."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Другой товар", callback_data=f"draft:reroll:{draft_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"draft:reject:{draft_id}"),
            ],
        ]
    )
