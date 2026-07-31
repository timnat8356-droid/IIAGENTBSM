import re
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from . import config

client = GigaChat(
    credentials=config.GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",       # тариф для физлиц (бесплатный лимит 1 млн токенов/мес)
    model=config.GIGACHAT_MODEL,
    verify_ssl_certs=False,           # без установки российского корневого сертификата Минцифры
)

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # символы, пиктограммы, эмоции и т.д.
    "\U00002600-\U000027BF"  # разное + дингбаты
    "\U0001F1E6-\U0001F1FF"  # флаги
    "\U00002190-\U000021FF"  # стрелки (часть эмодзи-набора)
    "\U00002B00-\U00002BFF"  # доп. стрелки/символы
    "\U0000FE0F"              # variation selector, часто идёт с эмодзи
    "]+",
    flags=re.UNICODE,
)


def _clean_post_text(text: str) -> str:
    text = _EMOJI_PATTERN.sub("", text)
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[ \t]{2,}", " ", text)  # убираем двойные пробелы, оставшиеся после чистки
    return text.strip()

BRAND_CONTEXT = """
Ты — SMM-копирайтер бренда Beauty Supply Moscow.

О бизнесе: поставщик расходников для мастеров ногтевого сервиса, косметологов
и салонов красоты. На рынке 10 лет, более 1000 клиентов по всей России.
Слоган: «Надёжные расходники на каждый день».

Позиционирование:
- всё нужное в одном месте, не нужно собирать заказ у нескольких поставщиков;
- цены ниже, чем на маркетплейсах (Wildberries, Ozon, Яндекс Маркет), т.к. продажа напрямую;
- есть офлайн-точка: Автозаводская ул., 18, Москва, ТРЦ «Ривьера», -1 этаж, ряд 6, павильон 59-61,
  работает ежедневно 10:00-18:00. Можно приехать и посмотреть товар вживую;
- ассортимент в офлайн-точке идентичен онлайн-каталогу.

Контакты для заказа (указывай в конце поста кратко, не всё сразу):
WhatsApp/телефон 89263425467, Telegram-канал t.me/beautysupplymoscow, ВК vk.ru/beautysupplymoscow.

Тон: дружелюбный, простой, без канцелярита и пафоса. Обращение на "вы".
Без эмодзи — ни одного смайлика в тексте.
Без длинного тире «—» и среднего тире «–»: если нужна пауза или перечисление,
используй обычный дефис «-», запятую или отдельное предложение.
Аудитория: частные мастера маникюра/педикюра, косметологи, салоны красоты.

Формат поста: 3-6 коротких абзацев/строк, без markdown-заголовков.
Обязательно упомяни название товара и цену за упаковку.
В конце — мягкий призыв к действию (написать в WhatsApp/Telegram или приехать в шоурум).
Не выдумывай характеристики товара, которых нет в данных.
""".strip()


def generate_post(product: dict) -> str:
    user_prompt = f"""
Товар: {product['name']}
Цена: {product['price']} ₽
Количество в упаковке: {product.get('pack') or 'не указано'}

Напиши рекламный пост для Telegram-канала про этот товар по гайдлайнам выше.
""".strip()

    payload = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=BRAND_CONTEXT),
            Messages(role=MessagesRole.USER, content=user_prompt),
        ],
        max_tokens=600,
    )
    response = client.chat(payload)
    raw_text = response.choices[0].message.content.strip()
    return _clean_post_text(raw_text)
