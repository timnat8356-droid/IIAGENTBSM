import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config
from .handlers import router, build_text_draft, send_text_request

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)


async def scheduled_generate():
    log.info("Плановая генерация текста поста")
    try:
        draft = await build_text_draft()
    except Exception:
        log.exception("Плановая генерация не удалась")
        await bot.send_message(config.OWNER_CHAT_ID, "⚠️ Не удалось сгенерировать плановый черновик поста, проверьте логи.")
        return
    await send_text_request(bot, config.OWNER_CHAT_ID, draft)


async def on_startup(app: web.Application):
    await bot.set_webhook(config.WEBHOOK_URL)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    for hour in config.POST_HOURS_MSK:
        scheduler.add_job(
            scheduled_generate,
            CronTrigger(hour=hour, minute=0),
            id=f"scheduled_generate_{hour}",
        )
    scheduler.start()
    log.info("Запланированы черновики на часы (МСК): %s", config.POST_HOURS_MSK)
    app["scheduler"] = scheduler
    log.info("Бот запущен, вебхук установлен: %s", config.WEBHOOK_URL)


async def on_shutdown(app: web.Application):
    await bot.session.close()


def create_app() -> web.Application:
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    async def health(request):
        return web.Response(text="ok")

    app.router.add_get("/", health)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=config.PORT)
