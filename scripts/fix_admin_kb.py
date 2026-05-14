import os

path = r'C:\Users\saymo\Цветочный-БОТ\telegram-order-button-bot\bot\keyboards\admin.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. products menu
text = text.replace(
    '[\n            InlineKeyboardButton(text="🔥 Активные", callback_data="admin:products_active"),\n            InlineKeyboardButton(text="🙈 Скрытые", callback_data="admin:products_hidden")\n        ],',
    '[InlineKeyboardButton(text="📋 Список букетов", callback_data="admin:product_list")],'
)

# 2. product list view fix
text = text.replace(
    'callback_data=f"admin_product_view:{p.id}"',
    'callback_data=f"admin_prod_view:{p.id}"'
)

# 3. product detail toggle fix
text = text.replace(
    '[\n            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_product_edit:{product_id}"),\n            InlineKeyboardButton(text=toggle_text, callback_data=f"admin_product_toggle:{product_id}")\n        ],',
    '[InlineKeyboardButton(text=toggle_text, callback_data=f"admin_prod_toggle:{product_id}")],'
)

# 4. product delete fix
text = text.replace(
    'callback_data=f"admin_product_delete:{product_id}"',
    'callback_data=f"admin_prod_delete:{product_id}"'
)

# 5. posts menu fix
text = text.replace(
    '[\n            InlineKeyboardButton(text="📅 Планы", callback_data="admin:posts_scheduled"),\n            InlineKeyboardButton(text="🕘 Архив", callback_data="admin:posts_recent")\n        ],',
    '[InlineKeyboardButton(text="🕘 Архив", callback_data="admin:posts_recent")],'
)

# 6. post preview
text = text.replace(
    '[InlineKeyboardButton(text="✏️ Изменить текст", callback_data="post_action:edit_text")],\n        [InlineKeyboardButton(text="💾 В черновики", callback_data="post_action:draft")],',
    ''
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('Done fixing bot/keyboards/admin.py')
