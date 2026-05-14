"""
formatting.py — безопасное HTML-форматирование для Telegram.

Все пользовательские данные в caption/text должны проходить через h().
Telegram поддерживает: <b>, <i>, <code>, <pre>, <a>, <s>, <u>, <blockquote>
"""

import html as _html

from bot.ui_tokens import CE, E


MAX_TELEGRAM_PHOTO_CAPTION = 1024


def h(text: str) -> str:
    """Экранирует спецсимволы HTML. Обязательно для user-input данных."""
    return _html.escape(str(text), quote=False)


def b(text: str) -> str:
    """Жирный текст: <b>...</b>"""
    return f"<b>{h(text)}</b>"


def i(text: str) -> str:
    """Курсив: <i>...</i>"""
    return f"<i>{h(text)}</i>"


def code(text: str) -> str:
    """Моноширинный код: <code>...</code>"""
    return f"<code>{h(text)}</code>"


def pre(text: str, lang: str = "") -> str:
    """Блок кода: <pre>...</pre>"""
    if lang:
        return f'<pre><code class="language-{lang}">{h(text)}</code></pre>'
    return f"<pre>{h(text)}</pre>"


def quote(text: str) -> str:
    """Цитата: <blockquote>...</blockquote>"""
    return f"<blockquote>{h(text)}</blockquote>"


def link(url: str, text: str) -> str:
    """Гиперссылка: <a href="url">text</a>"""
    return f'<a href="{h(url)}">{h(text)}</a>'


def tg_emoji(key: str) -> str:
    """Возвращает premium/custom emoji HTML или Unicode fallback."""
    fallback = E.get(key, "")
    custom_id = CE.get(key)
    if not custom_id:
        return fallback
    return f'<tg-emoji emoji-id="{h(custom_id)}">{h(fallback)}</tg-emoji>'


def trim_caption(caption: str, limit: int = MAX_TELEGRAM_PHOTO_CAPTION) -> str:
    """Обрезает caption до лимита Telegram, сохраняя читаемый хвост."""
    if len(caption) <= limit:
        return caption
    return caption[: limit - 4].rstrip() + "\n\n…"


def build_post_caption(title: str, price: int | None, description: str | None = None) -> str:
    """
    Генерирует красивый HTML-caption для публикации в Telegram-канал.
    Использует только официальные Telegram HTML-теги.
    Все данные экранируются.
    """
    lines = []

    # Заголовок
    lines.append(f"💐 {b(title)}")

    # Описание в blockquote - обрезаем ДО обертки в HTML
    if description:
        lines.append("")
        # Резервируем место под заголовок и цену (~300 символов)
        # Описание обрезаем до ~700 символов
        safe_desc = description[:700] + "…" if len(description) > 700 else description
        lines.append(quote(safe_desc))
    
    # Цена
    lines.append("")
    if price:
        price_str = f"{price:,}".replace(",", " ")
        lines.append(f"💰 {b('Цена:')} от {b(price_str + ' ₽')}")
    else:
        lines.append(f"💰 {b('Цена:')} {i('по запросу')}")

    lines.append("")
    lines.append("Нажмите кнопку ниже, чтобы оформить заказ.")

    final_caption = "\n".join(lines)
    return trim_caption(final_caption)
