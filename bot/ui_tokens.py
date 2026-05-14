"""
ui_tokens.py - единый слой UI-токенов для Telegram-бота.

E  -> fallback Unicode emoji
CE -> optional custom/premium emoji ids
STYLE -> Telegram button styles
"""

E: dict[str, str] = {
    "popular": "🌸",
    "bouquet": "💐",
    "choose": "🌿",
    "shop": "🛍",
    "cart": "🛒",
    "orders": "📦",
    "profile": "👤",
    "help": "💬",
    "details": "☰",
    "back": "↩️",
    "admin": "🛠",
    "post": "📸",
    "posts": "📝",
    "promo": "🎟",
    "branch": "📍",
    "stats": "📊",
    "florist": "👩‍🌾",
    "success": "✅",
    "danger": "❌",
    "pay": "💳",
    "delivery": "🚚",
    "pickup": "🏪",
    "date": "📅",
    "time": "🕒",
    "package": "🎁",
    "postcard": "💌",
    "next": "➡️",
    "prev": "⬅️",
    "publish": "🚀",
    "eye": "👀",
    "new": "✨",
    "warning": "⚠️",
    "info": "ℹ️",
    "edit": "✏️",
    "delete": "🗑",
    "toggle_on": "✅",
    "toggle_off": "🙈",
    "phone": "📱",
    "map": "🗺",
    "archive": "🕘",
    "comment": "✍️",
    "list": "📋",
    "add": "➕",
    "close": "✅",
    "consultation": "👩‍🌾",
    "birthday": "🎂",
    "love": "❤️",
    "sorry": "🙏",
    "flower": "🌸",
    "office": "💼",
    "other": "❓",
}

CE: dict[str, str] = {
    # Provisional floral premium mapping from Flowers_emoji_gray.
    # This is a composition-first pass to validate rendering in real Telegram UI.
    # Utility actions stay on Unicode fallback until better semantic premium icons are selected.
    "popular": "5413834889680165327",
    "bouquet": "5411333938813639401",
    "choose": "5413426330916132973",
    "shop": "5411276884468079837",
    "help": "5413482406009150856",
    "branch": "5413728065253582071",
    "florist": "5413456069269693845",
    "post": "5413342716492816429",
    "posts": "5413344584803589792",
    "publish": "5411127728843823885",
    "package": "5413843007168355432",
    "postcard": "5413580150874871328",
    "flower": "5413833296247300641",
}

STYLE: dict[str, str] = {
    "primary": "primary",
    "success": "success",
    "danger": "danger",
}
