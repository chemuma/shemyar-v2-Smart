import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

supabase = create_client(
    os.getenv('VITE_SUPABASE_URL'),
    os.getenv('VITE_SUPABASE_ANON_KEY')
)

REGISTER_NAME, REGISTER_STUDENT_ID, REGISTER_MAJOR, REGISTER_YEAR = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id

    existing_user = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()

    if existing_user.data:
        user_data = existing_user.data[0]
        if user_data['is_verified']:
            keyboard = [
                [InlineKeyboardButton("اعلان‌ها", callback_data='announcements'),
                 InlineKeyboardButton("رویدادها", callback_data='events')],
                [InlineKeyboardButton("منابع", callback_data='resources'),
                 InlineKeyboardButton("پرسش و پاسخ", callback_data='qa')],
                [InlineKeyboardButton("پروفایل من", callback_data='profile')]
            ]

            if user_data['role'] in ['admin', 'superadmin']:
                keyboard.append([InlineKeyboardButton("پنل مدیریت", callback_data='admin_panel')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"سلام {user_data['first_name']}!\n\n"
                "به ربات انجمن مهندسی شیمی خوش آمدید.\n"
                "لطفا یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "حساب کاربری شما در انتظار تایید است.\n"
                "پس از تایید توسط مدیران، به شما اطلاع داده خواهد شد."
            )
    else:
        await update.message.reply_text(
            "به ربات انجمن مهندسی شیمی خوش آمدید!\n\n"
            "برای استفاده از امکانات ربات، لطفا ثبت‌نام کنید.\n"
            "از دستور /register استفاده کنید."
        )

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "برای ثبت‌نام، لطفا نام و نام خانوادگی خود را وارد کنید:"
    )
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "شماره دانشجویی خود را وارد کنید:"
    )
    return REGISTER_STUDENT_ID

async def register_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['student_id'] = update.message.text
    await update.message.reply_text(
        "رشته تحصیلی خود را وارد کنید:"
    )
    return REGISTER_MAJOR

async def register_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['major'] = update.message.text
    await update.message.reply_text(
        "سال ورودی خود را وارد کنید (مثال: 1402):"
    )
    return REGISTER_YEAR

async def register_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['year'] = int(update.message.text)

    name_parts = context.user_data['name'].split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    try:
        supabase.table('users').insert({
            'telegram_id': user.id,
            'username': user.username,
            'first_name': first_name,
            'last_name': last_name,
            'student_id': context.user_data['student_id'],
            'major': context.user_data['major'],
            'year': context.user_data['year'],
            'is_verified': False,
            'is_active': True
        }).execute()

        await update.message.reply_text(
            "ثبت‌نام شما با موفقیت انجام شد!\n\n"
            "اطلاعات شما در انتظار تایید مدیران است.\n"
            "پس از تایید، به شما اطلاع داده خواهد شد."
        )

        admins = supabase.table('users').select('telegram_id').in_('role', ['admin', 'superadmin']).execute()
        for admin in admins.data:
            try:
                await context.bot.send_message(
                    chat_id=admin['telegram_id'],
                    text=f"درخواست عضویت جدید:\n\n"
                         f"نام: {context.user_data['name']}\n"
                         f"شماره دانشجویی: {context.user_data['student_id']}\n"
                         f"رشته: {context.user_data['major']}\n"
                         f"سال ورودی: {context.user_data['year']}\n"
                         f"تلگرام: @{user.username or 'ندارد'}"
                )
            except:
                pass

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await update.message.reply_text(
            "خطایی در ثبت‌نام رخ داد. لطفا دوباره تلاش کنید."
        )

    return ConversationHandler.END

async def register_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ثبت‌نام لغو شد.")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = supabase.table('users').select('*').eq('telegram_id', user.id).execute()

    if not user_data.data or not user_data.data[0]['is_verified']:
        await query.edit_message_text("شما دسترسی ندارید.")
        return

    current_user = user_data.data[0]

    if query.data == 'announcements':
        await show_announcements(query, context)
    elif query.data == 'events':
        await show_events(query, context, current_user)
    elif query.data == 'resources':
        await show_resources(query, context)
    elif query.data == 'qa':
        await show_qa(query, context)
    elif query.data == 'profile':
        await show_profile(query, context, current_user)
    elif query.data == 'admin_panel':
        if current_user['role'] in ['admin', 'superadmin']:
            await show_admin_panel(query, context, current_user)
        else:
            await query.edit_message_text("شما دسترسی به پنل مدیریت ندارید.")
    elif query.data.startswith('back_'):
        await handle_back(query, context, current_user)

async def show_announcements(query, context):
    announcements = supabase.table('announcements').select('*').eq('is_published', True).order('created_at', desc=True).limit(10).execute()

    if not announcements.data:
        await query.edit_message_text("اعلانی موجود نیست.")
        return

    keyboard = []
    for ann in announcements.data:
        priority_icon = {
            'urgent': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(ann['priority'], '⚪')

        keyboard.append([InlineKeyboardButton(
            f"{priority_icon} {ann['title'][:40]}...",
            callback_data=f"ann_{ann['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "اعلان‌های اخیر:",
        reply_markup=reply_markup
    )

async def show_events(query, context, user):
    events = supabase.table('events').select('*').eq('is_active', True).order('event_date').execute()

    if not events.data:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("رویدادی موجود نیست.", reply_markup=reply_markup)
        return

    keyboard = []
    for event in events.data:
        event_date = datetime.fromisoformat(event['event_date'].replace('Z', '+00:00'))
        keyboard.append([InlineKeyboardButton(
            f"{event['title']} - {event_date.strftime('%Y/%m/%d')}",
            callback_data=f"event_{event['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "رویدادهای پیش‌رو:",
        reply_markup=reply_markup
    )

async def show_resources(query, context):
    keyboard = [
        [InlineKeyboardButton("کتاب‌ها", callback_data='res_book'),
         InlineKeyboardButton("مقالات", callback_data='res_paper')],
        [InlineKeyboardButton("ویدیوها", callback_data='res_video'),
         InlineKeyboardButton("ابزارها", callback_data='res_tool')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "منابع آموزشی:\n\nدسته مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def show_qa(query, context):
    keyboard = [
        [InlineKeyboardButton("سوالات اخیر", callback_data='qa_recent')],
        [InlineKeyboardButton("پرسش سوال جدید", callback_data='qa_ask')],
        [InlineKeyboardButton("سوالات من", callback_data='qa_mine')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "بخش پرسش و پاسخ:",
        reply_markup=reply_markup
    )

async def show_profile(query, context, user):
    status = "تایید شده ✅" if user['is_verified'] else "در انتظار تایید ⏳"
    role_name = {
        'member': 'عضو',
        'admin': 'مدیر',
        'superadmin': 'مدیر ارشد'
    }.get(user['role'], 'عضو')

    profile_text = f"پروفایل شما:\n\n" \
                   f"نام: {user['first_name']} {user['last_name']}\n" \
                   f"شماره دانشجویی: {user['student_id']}\n" \
                   f"رشته: {user['major']}\n" \
                   f"سال ورودی: {user['year']}\n" \
                   f"نقش: {role_name}\n" \
                   f"وضعیت: {status}\n" \
                   f"تاریخ عضویت: {datetime.fromisoformat(user['joined_at'].replace('Z', '+00:00')).strftime('%Y/%m/%d')}"

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(profile_text, reply_markup=reply_markup)

async def show_admin_panel(query, context, user):
    pending_users = supabase.table('users').select('id').eq('is_verified', False).execute()
    pending_count = len(pending_users.data)

    keyboard = [
        [InlineKeyboardButton(f"تایید اعضا ({pending_count})", callback_data='admin_verify')],
        [InlineKeyboardButton("ارسال اعلان", callback_data='admin_announce')],
        [InlineKeyboardButton("مدیریت رویدادها", callback_data='admin_events')],
        [InlineKeyboardButton("آمار ربات", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_main')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "پنل مدیریت:",
        reply_markup=reply_markup
    )

async def handle_back(query, context, user):
    if query.data == 'back_main':
        keyboard = [
            [InlineKeyboardButton("اعلان‌ها", callback_data='announcements'),
             InlineKeyboardButton("رویدادها", callback_data='events')],
            [InlineKeyboardButton("منابع", callback_data='resources'),
             InlineKeyboardButton("پرسش و پاسخ", callback_data='qa')],
            [InlineKeyboardButton("پروفایل من", callback_data='profile')]
        ]

        if user['role'] in ['admin', 'superadmin']:
            keyboard.append([InlineKeyboardButton("پنل مدیریت", callback_data='admin_panel')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"سلام {user['first_name']}!\n\n"
            "به ربات انجمن مهندسی شیمی خوش آمدید.\n"
            "لطفا یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
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

    application.add_handler(register_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
