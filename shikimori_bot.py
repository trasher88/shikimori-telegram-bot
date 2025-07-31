from telegram import Update
from config import TOKEN, CHAT_ID
from shikimori_one import ShikimoriParser
from telegram.ext import Application, CommandHandler, ContextTypes

# Конфигурация (перенес в config.py для GitHub)
CACHE_FILE = 'shikimori_cache.json'  # Файл с данными от парсера

# Инициализируем парсер
parser = ShikimoriParser()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🔔 Бот уведомлений о новых аниме с Shikimori!\n"
        "Я буду присылать вам обновления автоматически."
    )


async def send_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновляет данные и отправляет уведомления"""
    try:
        # Получаем свежие данные
        data = parser.get_data(use_cache=False)  # Всегда получаем свежие данные

        if data['status'] != 'success':
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text="⚠️ Не удалось получить данные с Shikimori"
            )
            return

        # 1. Отправляем новые серии
        if data.get('episodes'):
            for episode in data['episodes'][:5]:  # Первые 5 в списке
                message = (
                    f"🎬 <b>{episode['title']}</b>\n"
                    f"📅 <i>{episode['date']}</i>\n"
                    f"🔹 {episode['episode_info']}"
                )
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=message,
                    parse_mode='HTML'
                )

        # 2. Отправляем новости
        if data.get('news'):
            for news in data['news'][:3]:  # Последние 3 новости
                news_msg = (
                    f"📢 <b>{news['title']}</b>\n"
                    f"📅 {news['date']}\n"
                    f"{news['content'][:200]}..."  # Обрезаем длинный текст
                )
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=news_msg,
                    parse_mode='HTML'
                )

    except Exception as e:
        print(f"Ошибка при отправке: {e}")


def main() -> None:
    #response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json()
    #print(response)  # Скопируйте 'id' из 'chat'

    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Настраиваем автоматическую проверку каждые 6 часов
    job_queue = application.job_queue
    job_queue.run_repeating(
        callback=send_updates,
        interval=6 * 3600,  # Интервал в секундах (6 часов)
        #interval=60, # каждую минуту, для тестирования
        first=10  # Первый запуск через 10 сек после старта
    )

    # Запуск бота
    print("Бот запущен! Ожидание обновлений...")
    application.run_polling()


if __name__ == '__main__':
    main()