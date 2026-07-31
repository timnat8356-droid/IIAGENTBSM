cat > /home/claude/bsm-content-bot/app/handlers.py << 'PYEOF'
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from . import config, content, catalog
from .keyboards import draft_keyboard, text_only_keyboard, rubric_keyboard
from .storage import state, Draft

router = Router()
log = logging.getLogger(__name__)

PHOTO_REQUEST_HINT = "\n\n📷 Пришлите фото для этого поста — просто отправьте его сюда (или ответом на это сообщение, если черновиков несколько)."


def _owner_only(message_or_cb) -> bool:
    chat_id = (
        message_or_cb.chat.id
        if isinstance(message_or_cb, Message)
        else message_or_cb.message.chat.id
    )
    return chat_id == config.OWNER_CHAT_ID


async def build_text_draft(rubric: str) -> Draft:
    if rubric == "product":
        product = catalog.pick_random_product(exclude_names=state.recently_posted)
        text = content.generate_product_post(product)
        product_name = product["name"]
    elif rubric == "info":
        text = content.generate_info_post()
        product_name = ""
    elif rubric == "fun":
        text = content.generate_fun_post()
        product_name = ""
    elif rubric == "meme":
        text = content.generate_meme_caption()
        product_name = ""
    else:
        raise ValueError(f"Неизвестная рубрика: {rubric}")
    return state.new_draft(text=text, product_name=product_name, rubric=rubric)


async def send_text_request(bot, chat_id: int, draft: Draft):
    msg = await bot.send_message(
        chat_id=chat_id,
        text=draft.text + PHOTO_REQUEST_HINT,
        reply_markup=text_only_keyboard(draft.id),
    )
    draft.request_message_id = msg.message_id


async def send_ready_draft(bot, chat_id: int, draft: Draft):
    await bot.send_photo(
        chat_id=chat_id,
        photo=draft.photo_file_id,
        caption=draft.text,
        reply_markup=draft_keyboard(draft.id),
    )


async def send_rubric_prompt(bot, chat_id: int):
    await bot.send_message(
        chat_id=chat_id,
        text="Какую рубрику готовим?",
        reply_markup=rubric_keyboard(),
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    if not _owner_only(message):
        return
    await message.answer(
        "Привет! Я контент-бот Beauty Supply Moscow.\n\n"
        "/generate — выбрать рубрику и подготовить пост прямо сейчас.\n"
        "После генерации текста пришлите мне фото для поста в личку — соберу черновик с кнопками.\n"
        "Каждый день (может быть несколько раз) буду присылать выбор рубрики автоматически."
    )


@router.message(Command("generate"))
async def cmd_generate(message: Message):
    if not _owner_only(message):
        return
    await send_rubric_prompt(message.bot, message.chat.id)


@router.callback_query(F.data.startswith("rubric:"))
async def cb_rubric(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    rubric = callback.data.split(":", 1)[1]
    await callback.answer("Готовлю текст…")
    try:
        draft = await build_text_draft(rubric)
    except Exception as e:
        log.exception("Ошибка генерации черновика")
        await callback.message.answer(f"Не получилось сгенерировать черновик: {e}")
        return
    rubric_label = content.RUBRIC_NAMES.get(rubric, rubric)
    await callback.message.edit_text(text=f"Рубрика: {rubric_label}. Готовлю черновик ниже ⬇️")
    await send_text_request(callback.bot, callback.message.chat.id, draft)


@router.message(F.photo)
async def handle_photo(message: Message):
    if not _owner_only(message):
        return
    reply_id = message.reply_to_message.message_id if message.reply_to_message else None
    draft = state.pop_awaiting_photo(reply_id)
    if not draft:
        await message.answer(
            "Не нашёл черновик, который ждёт фото. Сначала запросите пост через /generate."
        )
        return
    draft.photo_file_id = message.photo[-1].file_id
    draft.status = "ready"
    await send_ready_draft(message.bot, message.chat.id, draft)


@router.callback_query(F.data.startswith("draft:publish:"))
async def cb_publish(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    draft_id = callback.data.split(":", 2)[2]
    draft = state.drafts.get(draft_id)
    if not draft or draft.status != "ready" or not draft.photo_file_id:
        return await callback.answer("Этот черновик уже неактуален", show_alert=True)
    await callback.bot.send_photo(
        chat_id=config.CHANNEL_ID,
        photo=draft.photo_file_id,
        caption=draft.text,
    )
    if draft.product_name:
        state.remember(draft.product_name)
    state.drafts.pop(draft_id, None)
    await callback.message.edit_caption(caption=draft.text + "\n\n✅ Опубликовано в канал")
    await callback.answer("Опубликовано!")


@router.callback_query(F.data.startswith("draft:reject:"))
async def cb_reject(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    draft_id = callback.data.split(":", 2)[2]
    draft = state.drafts.pop(draft_id, None)
    if draft_id in state.awaiting_photo_order:
        state.awaiting_photo_order.remove(draft_id)
    if draft and draft.status == "ready":
        await callback.message.edit_caption(caption="❌ Черновик отклонён")
    else:
        await callback.message.edit_text(text="❌ Черновик отклонён")
    await callback.answer()


@router.callback_query(F.data.startswith("draft:reroll:"))
async def cb_reroll(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    draft_id = callback.data.split(":", 2)[2]
    old_draft = state.drafts.pop(draft_id, None)
    if draft_id in state.awaiting_photo_order:
        state.awaiting_photo_order.remove(draft_id)
    rubric = old_draft.rubric if old_draft else "product"
    await callback.answer("Готовлю новый вариант…")
    try:
        new_draft = await build_text_draft(rubric)
    except Exception as e:
        log.exception("Ошибка перегенерации")
        await callback.message.answer(f"Не получилось сгенерировать черновик: {e}")
        return
    await callback.message.edit_text(text="🔄 Заменено на новый вариант ниже")
    await send_text_request(callback.bot, callback.message.chat.id, new_draft)


@router.callback_query(F.data.startswith("draft:rephoto:"))
async def cb_rephoto(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    draft_id = callback.data.split(":", 2)[2]
    draft = state.drafts.get(draft_id)
    if not draft:
        return await callback.answer("Этот черновик уже неактуален", show_alert=True)
    draft.photo_file_id = None
    draft.status = "awaiting_photo"
    if draft_id not in state.awaiting_photo_order:
        state.awaiting_photo_order.append(draft_id)
    await callback.answer()
    await callback.message.delete()
    await send_text_request(callback.bot, callback.message.chat.id, draft)


@router.callback_query(F.data.startswith("draft:edit:"))
async def cb_edit(callback: CallbackQuery):
    if not _owner_only(callback):
        return await callback.answer()
    draft_id = callback.data.split(":", 2)[2]
    draft = state.drafts.get(draft_id)
    if not draft:
        return await callback.answer("Этот черновик уже неактуален", show_alert=True)
    state.awaiting_edit_for = draft_id
    await callback.answer()
    await callback.message.answer("Пришлите новый текст поста одним сообщением.")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_edit_text(message: Message):
    if not _owner_only(message):
        return
    draft_id = state.awaiting_edit_for
    if not draft_id:
        return  # обычное сообщение вне режима редактирования — игнорируем
    draft = state.drafts.get(draft_id)
    state.awaiting_edit_for = None
    if not draft:
        await message.answer("Этот черновик уже неактуален.")
        return
    draft.text = message.text
    await message.answer("Текст обновлён:")
    if draft.status == "ready":
        await send_ready_draft(message.bot, message.chat.id, draft)
    else:
        if draft.id not in state.awaiting_photo_order:
            state.awaiting_photo_order.append(draft.id)
        await send_text_request(message.bot, message.chat.id, draft)
PYEOF
echo written
