import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from dotenv import load_dotenv

from bot import (
    start,
    register_start,
    register_name,
    register_student_id,
    register_major,
    register_year,
    register_cancel,
    button_handler,
    REGISTER_NAME,
    REGISTER_STUDENT_ID,
    REGISTER_MAJOR,
    REGISTER_YEAR
)

from handlers.admin import (
    verify_users_list,
    verify_user_detail,
    approve_user,
    reject_user,
    show_stats,
    announce_start,
    announce_title,
    announce_content,
    announce_category,
    announce_priority,
    announce_cancel,
    create_event_start,
    event_title,
    event_desc,
    event_date,
    event_location,
    event_capacity,
    event_cancel,
    ANNOUNCE_TITLE,
    ANNOUNCE_CONTENT,
    ANNOUNCE_CATEGORY,
    ANNOUNCE_PRIORITY,
    EVENT_TITLE,
    EVENT_DESC,
    EVENT_DATE,
    EVENT_LOCATION,
    EVENT_CAPACITY
)

from handlers.qa_resources import (
    show_recent_questions,
    show_question_detail,
    ask_question_start,
    ask_title,
    ask_content,
    ask_category,
    ask_cancel,
    show_resources_by_category,
    show_resource_detail,
    upload_resource_start,
    upload_title,
    upload_desc,
    upload_category,
    upload_file,
    upload_cancel,
    ASK_TITLE,
    ASK_CONTENT,
    ASK_CATEGORY,
    UPLOAD_TITLE,
    UPLOAD_DESC,
    UPLOAD_CATEGORY,
    UPLOAD_FILE
)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def extended_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == 'admin_verify':
        await verify_users_list(query, context)
    elif query.data.startswith('verify_'):
        await verify_user_detail(query, context)
    elif query.data.startswith('approve_'):
        await approve_user(query, context)
    elif query.data.startswith('reject_'):
        await reject_user(query, context)
    elif query.data == 'admin_stats':
        await show_stats(query, context)
    elif query.data == 'qa_recent':
        await show_recent_questions(query, context)
    elif query.data.startswith('q_'):
        await show_question_detail(query, context)
    elif query.data.startswith('res_'):
        await show_resources_by_category(query, context)
    elif query.data.startswith('resource_'):
        await show_resource_detail(query, context)
    else:
        await button_handler(update, context)

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        print("خطا: TELEGRAM_BOT_TOKEN در فایل .env موجود نیست")
        print("لطفا توکن ربات تلگرام خود را در فایل .env با کلید TELEGRAM_BOT_TOKEN اضافه کنید")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))

    register_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register_start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_student_id)],
            REGISTER_MAJOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_major)],
            REGISTER_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_year)],
        },
        fallbacks=[CommandHandler('cancel', register_cancel)]
    )

    announce_handler = ConversationHandler(
        entry_points=[CommandHandler('announce', announce_start)],
        states={
            ANNOUNCE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, announce_title)],
            ANNOUNCE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, announce_content)],
            ANNOUNCE_CATEGORY: [CallbackQueryHandler(announce_category, pattern='^cat_')],
            ANNOUNCE_PRIORITY: [CallbackQueryHandler(announce_priority, pattern='^pri_')],
        },
        fallbacks=[CommandHandler('cancel', announce_cancel)]
    )

    event_handler = ConversationHandler(
        entry_points=[CommandHandler('createevent', create_event_start)],
        states={
            EVENT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_title)],
            EVENT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_desc)],
            EVENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_date)],
            EVENT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_location)],
            EVENT_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_capacity)],
        },
        fallbacks=[CommandHandler('cancel', event_cancel)]
    )

    ask_handler = ConversationHandler(
        entry_points=[CommandHandler('ask', ask_question_start)],
        states={
            ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_title)],
            ASK_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_content)],
            ASK_CATEGORY: [CallbackQueryHandler(ask_category, pattern='^qcat_')],
        },
        fallbacks=[CommandHandler('cancel', ask_cancel)]
    )

    upload_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload_resource_start)],
        states={
            UPLOAD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_title)],
            UPLOAD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_desc)],
            UPLOAD_CATEGORY: [CallbackQueryHandler(upload_category, pattern='^ucat_')],
            UPLOAD_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_file)],
        },
        fallbacks=[CommandHandler('cancel', upload_cancel)]
    )

    application.add_handler(register_handler)
    application.add_handler(announce_handler)
    application.add_handler(event_handler)
    application.add_handler(ask_handler)
    application.add_handler(upload_handler)

    application.add_handler(CallbackQueryHandler(extended_button_handler))

    logger.info("ربات با موفقیت راه‌اندازی شد")
    print("ربات انجمن مهندسی شیمی راه‌اندازی شد...")
    print("برای توقف ربات از Ctrl+C استفاده کنید")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
