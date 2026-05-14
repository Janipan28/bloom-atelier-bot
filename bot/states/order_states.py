from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    entry_choice = State()
    choose_delivery_type = State()
    choose_date = State()
    choose_time = State()
    get_phone = State()
    choose_branch = State()
    get_address = State()
    choose_services = State()
    get_card_text = State()
    get_comment = State()
    get_promo = State()
    spend_loyalty = State()
    # Объединённый экран промокод + баллы
    promo_and_loyalty = State()
    confirm = State()
    edit = State()

    # Состояния для анкеты (Survey)
    survey_occasion = State()
    survey_budget = State()

    # Флорист — ввод сообщения
    florist_message = State()
