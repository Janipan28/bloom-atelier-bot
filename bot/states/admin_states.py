from aiogram.fsm.state import State, StatesGroup

class AdminPostFlow(StatesGroup):
    get_photo = State()
    get_title = State()
    get_price = State()
    get_description = State()
    choose_buttons = State()
    preview = State()

class AdminProductFlow(StatesGroup):
    get_photo = State()
    get_title = State()
    get_price = State()
    get_description = State()
    get_category = State()
    confirm = State()
    # Редактирование
    edit_title = State()
    edit_price = State()
    edit_description = State()
    edit_photo = State()
    edit_tags = State()


class AdminPromoFlow(StatesGroup):
    get_code = State()
    choose_discount_type = State()
    get_discount_value = State()
    get_usage_limit = State()
    get_valid_until = State()
    edit_discount = State()
    edit_limit = State()
    edit_valid_until = State()


class AdminReplyFlow(StatesGroup):
    get_message = State()
