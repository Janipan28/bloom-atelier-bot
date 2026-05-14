import html
from typing import Optional

def escape_html(text: str) -> str:
    """Безопасно экранирует текст для Telegram HTML."""
    if not text:
        return ""
    return html.escape(text)

def build_flower_post_html(title: str, price: Optional[int], description: Optional[str], composition: Optional[str] = None) -> str:
    """Формирует красивый HTML текст для поста в канале."""
    lines = []
    
    # Заголовок жирным
    lines.append(f"<b>{escape_html(title)}</b>")
    lines.append("")
    
    # Описание
    if description:
        lines.append(escape_html(description))
        lines.append("")
        
    # Состав (если есть)
    if composition:
        lines.append(f"💐 Состав: <i>{escape_html(composition)}</i>")
        lines.append("")
        
    # Цена
    if price:
        lines.append(f"Цена: <b>{price:,} ₽</b>".replace(',', ' '))
    else:
        lines.append("Цена: <b>по запросу</b>")
        
    lines.append("")
    lines.append("🚛 Можно оформить доставку или самовывоз из мастерской.")
    
    return "\n".join(lines)

def build_preview_text(text: str, btn_type: str) -> str:
    """Формирует текст предпросмотра для админа."""
    btn_labels = {
        "order": "Заказать",
        "order_shop": "Заказать + Магазин",
        "none": "Без кнопок"
    }
    label = btn_labels.get(btn_type, btn_type)
    return (
        f"👀 <b>Предпросмотр поста:</b>\n\n"
        f"{text}\n\n"
        f"<i>Кнопки: {label}</i>"
    )
