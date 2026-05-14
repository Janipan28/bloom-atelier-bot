# Telegram Order Button Bot

Локальный Telegram-бот, который автоматически добавляет кнопку **«Заказать»** под новые посты Telegram-канала.

## Что делает бот

Когда в канале появляется новый пост, бот добавляет под него inline-кнопку:

```text
[ Заказать ]
```

Кнопка ведёт на ссылку из переменной `ORDER_URL`, например:

```text
https://t.me/your_username
```

## Требования

- Python 3.10+
- Telegram-бот от @BotFather
- Бот добавлен администратором в канал
- У бота есть право редактировать сообщения канала

## Установка

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

## Настройка

Скопируйте `.env.example` в `.env`:

```bash
copy .env.example .env
```

На Linux/macOS:

```bash
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=ваш_токен_бота
ORDER_URL=https://t.me/your_username
BUTTON_TEXT=Заказать
TARGET_CHANNEL_ID=
```

`TARGET_CHANNEL_ID` можно оставить пустым.

## Запуск

Windows:

```bash
run.bat
```

Или вручную:

```bash
python bot.py
```

Linux/macOS:

```bash
./run.sh
```

## Проверка

1. Запустите бота.
2. Убедитесь, что в логах есть строка:

```text
Bot authorized as @...
Webhook deleted. Starting polling...
```

3. Опубликуйте новый пост в канале.
4. Под постом должна появиться кнопка **«Заказать»**.

## Если кнопка не появилась

Проверьте:

1. Бот добавлен в канал как администратор.
2. У бота есть право редактировать сообщения.
3. Бот запущен локально.
4. Пост был опубликован после запуска бота.
5. В `.env` указан корректный `BOT_TOKEN`.
6. `ORDER_URL` начинается с `https://`, `http://` или `tg://`.

## Важное ограничение

Бот обрабатывает новые посты, которые приходят через polling, пока бот запущен. Для старых постов отдельная обработка в этой версии не реализована.
