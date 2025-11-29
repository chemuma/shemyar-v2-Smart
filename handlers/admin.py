import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('VITE_SUPABASE_URL'),
    os.getenv('VITE_SUPABASE_ANON_KEY')
)

ANNOUNCE_TITLE, ANNOUNCE_CONTENT, ANNOUNCE_CATEGORY, ANNOUNCE_PRIORITY = range(4)
EVENT_TITLE, EVENT_DESC, EVENT_DATE, EVENT_LOCATION, EVENT_CAPACITY = range(5)

async def verify_users_list(query, context):
    pending = supabase.table('users').select('*').eq('is_verified', False).execute()

    if not pending.data:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("کاربری در انتظار تایید نیست.", reply_markup=reply_markup)
        return

    keyboard = []
    for user in pending.data:
        keyboard.append([InlineKeyboardButton(
            f"{user['first_name']} {user['last_name']} - {user['student_id']}",
            callback_data=f"verify_{user['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "کاربران در انتظار تایید:",
        reply_markup=reply_markup
    )

async def verify_user_detail(query, context):
    user_id = query.data.replace('verify_', '')
    user = supabase.table('users').select('*').eq('id', user_id).execute()

    if not user.data:
        await query.answer("کاربر یافت نشد!")
        return

    user_data = user.data[0]

    user_info = f"اطلاعات کاربر:\n\n" \
                f"نام: {user_data['first_name']} {user_data['last_name']}\n" \
                f"شماره دانشجویی: {user_data['student_id']}\n" \
                f"رشته: {user_data['major']}\n" \
                f"سال ورودی: {user_data['year']}\n" \
                f"نام کاربری تلگرام: @{user_data['username'] or 'ندارد'}\n" \
                f"تاریخ ثبت‌نام: {datetime.fromisoformat(user_data['joined_at'].replace('Z', '+00:00')).strftime('%Y/%m/%d %H:%M')}"

    keyboard = [
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user_id}"),
         InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_verify')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(user_info, reply_markup=reply_markup)

async def approve_user(query, context):
    user_id = query.data.replace('approve_', '')

    try:
        supabase.table('users').update({
            'is_verified': True
        }).eq('id', user_id).execute()

        user = supabase.table('users').select('telegram_id, first_name').eq('id', user_id).execute()

        if user.data:
            try:
                await context.bot.send_message(
                    chat_id=user.data[0]['telegram_id'],
                    text=f"سلام {user.data[0]['first_name']}!\n\n"
                         "حساب کاربری شما توسط مدیران تایید شد.\n"
                         "اکنون می‌توانید از تمام امکانات ربات استفاده کنید.\n\n"
                         "از دستور /start استفاده کنید."
                )
            except:
                pass

        await query.answer("کاربر تایید شد!")
        await verify_users_list(query, context)

    except Exception as e:
        await query.answer(f"خطا: {str(e)}")

async def reject_user(query, context):
    user_id = query.data.replace('reject_', '')

    try:
        user = supabase.table('users').select('telegram_id, first_name').eq('id', user_id).execute()

        supabase.table('users').delete().eq('id', user_id).execute()

        if user.data:
            try:
                await context.bot.send_message(
                    chat_id=user.data[0]['telegram_id'],
                    text=f"سلام {user.data[0]['first_name']}!\n\n"
                         "متاسفانه درخواست عضویت شما توسط مدیران رد شد.\n"
                         "در صورت نیاز می‌توانید مجددا ثبت‌نام کنید."
                )
            except:
                pass

        await query.answer("کاربر رد شد!")
        await verify_users_list(query, context)

    except Exception as e:
        await query.answer(f"خطا: {str(e)}")

async def show_stats(query, context):
    total_users = supabase.table('users').select('id', count='exact').execute()
    verified_users = supabase.table('users').select('id', count='exact').eq('is_verified', True).execute()
    total_announcements = supabase.table('announcements').select('id', count='exact').execute()
    total_events = supabase.table('events').select('id', count='exact').execute()
    total_questions = supabase.table('questions').select('id', count='exact').execute()
    total_resources = supabase.table('resources').select('id', count='exact').execute()

    stats_text = f"آمار ربات:\n\n" \
                 f"👥 کل کاربران: {total_users.count}\n" \
                 f"✅ کاربران تایید شده: {verified_users.count}\n" \
                 f"📢 اعلان‌ها: {total_announcements.count}\n" \
                 f"📅 رویدادها: {total_events.count}\n" \
                 f"❓ سوالات: {total_questions.count}\n" \
                 f"📚 منابع: {total_resources.count}"

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def announce_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = supabase.table('users').select('role').eq('telegram_id', user.id).execute()

    if not user_data.data or user_data.data[0]['role'] not in ['admin', 'superadmin']:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

    await update.message.reply_text("عنوان اعلان را وارد کنید:")
    return ANNOUNCE_TITLE

async def announce_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['announce_title'] = update.message.text
    await update.message.reply_text("متن اعلان را وارد کنید:")
    return ANNOUNCE_CONTENT

async def announce_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['announce_content'] = update.message.text

    keyboard = [
        [InlineKeyboardButton("خبر", callback_data='cat_news'),
         InlineKeyboardButton("رویداد", callback_data='cat_event')],
        [InlineKeyboardButton("امتحان", callback_data='cat_exam'),
         InlineKeyboardButton("پروژه", callback_data='cat_project')],
        [InlineKeyboardButton("عمومی", callback_data='cat_general')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "دسته‌بندی اعلان را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return ANNOUNCE_CATEGORY

async def announce_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_map = {
        'cat_news': 'news',
        'cat_event': 'event',
        'cat_exam': 'exam',
        'cat_project': 'project',
        'cat_general': 'general'
    }

    context.user_data['announce_category'] = category_map.get(query.data, 'general')

    keyboard = [
        [InlineKeyboardButton("🔴 فوری", callback_data='pri_urgent'),
         InlineKeyboardButton("🟠 بالا", callback_data='pri_high')],
        [InlineKeyboardButton("🟡 متوسط", callback_data='pri_medium'),
         InlineKeyboardButton("🟢 پایین", callback_data='pri_low')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "اولویت اعلان را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return ANNOUNCE_PRIORITY

async def announce_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    priority_map = {
        'pri_urgent': 'urgent',
        'pri_high': 'high',
        'pri_medium': 'medium',
        'pri_low': 'low'
    }

    priority = priority_map.get(query.data, 'medium')

    user = update.effective_user
    user_data = supabase.table('users').select('id').eq('telegram_id', user.id).execute()

    try:
        result = supabase.table('announcements').insert({
            'title': context.user_data['announce_title'],
            'content': context.user_data['announce_content'],
            'category': context.user_data['announce_category'],
            'priority': priority,
            'created_by': user_data.data[0]['id'],
            'is_published': True
        }).execute()

        await query.edit_message_text(
            "اعلان با موفقیت منتشر شد!\n\n"
            f"عنوان: {context.user_data['announce_title']}\n"
            f"دسته: {context.user_data['announce_category']}\n"
            f"اولویت: {priority}"
        )

        verified_users = supabase.table('users').select('telegram_id').eq('is_verified', True).execute()

        priority_icon = {
            'urgent': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(priority, '⚪')

        for user_info in verified_users.data:
            try:
                await context.bot.send_message(
                    chat_id=user_info['telegram_id'],
                    text=f"{priority_icon} اعلان جدید\n\n"
                         f"📌 {context.user_data['announce_title']}\n\n"
                         f"{context.user_data['announce_content']}"
                )
            except:
                pass

    except Exception as e:
        await query.edit_message_text(f"خطا در انتشار اعلان: {str(e)}")

    return ConversationHandler.END

async def announce_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("انتشار اعلان لغو شد.")
    return ConversationHandler.END

async def create_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = supabase.table('users').select('role').eq('telegram_id', user.id).execute()

    if not user_data.data or user_data.data[0]['role'] not in ['admin', 'superadmin']:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

    await update.message.reply_text("عنوان رویداد را وارد کنید:")
    return EVENT_TITLE

async def event_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_title'] = update.message.text
    await update.message.reply_text("توضیحات رویداد را وارد کنید:")
    return EVENT_DESC

async def event_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_desc'] = update.message.text
    await update.message.reply_text("تاریخ و ساعت رویداد را وارد کنید (مثال: 1402/12/15 14:30):")
    return EVENT_DATE

async def event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_date'] = update.message.text
    await update.message.reply_text("محل برگزاری را وارد کنید:")
    return EVENT_LOCATION

async def event_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_location'] = update.message.text
    await update.message.reply_text("ظرفیت رویداد را وارد کنید (عدد):")
    return EVENT_CAPACITY

async def event_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_capacity'] = int(update.message.text)

    user = update.effective_user
    user_data = supabase.table('users').select('id').eq('telegram_id', user.id).execute()

    try:
        from datetime import datetime

        result = supabase.table('events').insert({
            'title': context.user_data['event_title'],
            'description': context.user_data['event_desc'],
            'event_date': context.user_data['event_date'],
            'location': context.user_data['event_location'],
            'capacity': context.user_data['event_capacity'],
            'created_by': user_data.data[0]['id'],
            'is_active': True
        }).execute()

        await update.message.reply_text(
            "رویداد با موفقیت ایجاد شد!\n\n"
            f"عنوان: {context.user_data['event_title']}\n"
            f"تاریخ: {context.user_data['event_date']}\n"
            f"محل: {context.user_data['event_location']}\n"
            f"ظرفیت: {context.user_data['event_capacity']}"
        )

    except Exception as e:
        await update.message.reply_text(f"خطا در ایجاد رویداد: {str(e)}")

    return ConversationHandler.END

async def event_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ایجاد رویداد لغو شد.")
    return ConversationHandler.END
