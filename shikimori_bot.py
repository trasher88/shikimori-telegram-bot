from telegram import Update
from config import TOKEN, ALLOWED_USERS
from shikimori_one import ShikimoriParser
from telegram.ext import Application, CommandHandler, ContextTypes

# Конфигурация
CACHE_FILE = 'shikimori_cache.json'

# Инициализируем парсер
parser = ShikimoriParser()

# Глобальный словарь для хранения активных чатов
active_chats = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id
    active_chats.add(chat_id)  # Добавляем чат в активные

    await update.message.reply_text(
        "🔔 Бот уведомлений о новых аниме с Shikimori!\n"
        "Я буду присылать вам обновления автоматически."
    )


async def send_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновляет данные и отправляет уведомления"""
    try:
        # Получаем свежие данные
        data = parser.get_data(use_cache=False)

        if data['status'] != 'success':
            # Отправляем сообщение об ошибке всем активным чатам
            for chat_id in active_chats:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Не удалось получить данные с Shikimori"
                    )
                except Exception as e:
                    print(f"Ошибка отправки в чат {chat_id}: {e}")
            return

        # Отправляем обновления всем активным чатам
        for chat_id in active_chats:
            try:
                # 1. Отправляем новые серии
                if data.get('episodes'):
                    for episode in data['episodes'][:5]:
                        message = (
                            f"🎬 <b>{episode['title']}</b>\n"
                            f"📅 <i>{episode['date']}</i>\n"
                            f"🔹 {episode['episode_info']}"
                        )
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='HTML'
                        )

                # 2. Отправляем новости
                if data.get('news'):
                    for news in data['news'][:3]:
                        news_msg = (
                            f"📢 <b>{news['title']}</b>\n"
                            f"📅 {news['date']}\n"
                            f"{news['content'][:200]}..."
                        )
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=news_msg,
                            parse_mode='HTML'
                        )
            except Exception as e:
                print(f"Ошибка при отправке в чат {chat_id}: {e}")

    except Exception as e:
        print(f"Ошибка при отправке: {e}")


def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Настраиваем автоматическую проверку каждые 6 часов
    job_queue = application.job_queue
    job_queue.run_repeating(
        callback=send_updates,
        interval=2 * 3600,
        #interval=60,
        first=10
    )

    # Запуск бота
    print("Бот запущен! Ожидание обновлений...")
    application.run_polling()


if __name__ == '__main__':
    main()