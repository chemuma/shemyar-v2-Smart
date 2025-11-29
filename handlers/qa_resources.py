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

ASK_TITLE, ASK_CONTENT, ASK_CATEGORY = range(3)
UPLOAD_TITLE, UPLOAD_DESC, UPLOAD_CATEGORY, UPLOAD_FILE = range(4)

async def show_recent_questions(query, context):
    questions = supabase.table('questions').select('*, users(first_name, last_name)').order('created_at', desc=True).limit(10).execute()

    if not questions.data:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='qa')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("سوالی موجود نیست.", reply_markup=reply_markup)
        return

    keyboard = []
    for q in questions.data:
        status = "✅" if q['is_answered'] else "⏳"
        keyboard.append([InlineKeyboardButton(
            f"{status} {q['title'][:40]}...",
            callback_data=f"q_{q['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='qa')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "سوالات اخیر:",
        reply_markup=reply_markup
    )

async def show_question_detail(query, context):
    question_id = query.data.replace('q_', '')
    question = supabase.table('questions').select('*, users(first_name, last_name)').eq('id', question_id).execute()

    if not question.data:
        await query.answer("سوال یافت نشد!")
        return

    q = question.data[0]

    supabase.table('questions').update({
        'views_count': q['views_count'] + 1
    }).eq('id', question_id).execute()

    answers = supabase.table('answers').select('*, users(first_name, last_name)').eq('question_id', question_id).order('created_at').execute()

    question_text = f"❓ {q['title']}\n\n" \
                    f"{q['content']}\n\n" \
                    f"دسته: {q['category']}\n" \
                    f"توسط: {q['users']['first_name']} {q['users']['last_name']}\n" \
                    f"تاریخ: {datetime.fromisoformat(q['created_at'].replace('Z', '+00:00')).strftime('%Y/%m/%d')}\n" \
                    f"بازدید: {q['views_count'] + 1}\n\n"

    if answers.data:
        question_text += f"پاسخ‌ها ({len(answers.data)}):\n\n"
        for ans in answers.data:
            accepted = "✅ " if ans['is_accepted'] else ""
            question_text += f"{accepted}💬 {ans['users']['first_name']}: {ans['content'][:100]}...\n\n"
    else:
        question_text += "هنوز پاسخی ثبت نشده است."

    keyboard = [
        [InlineKeyboardButton("پاسخ دادن", callback_data=f"answer_{question_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='qa_recent')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(question_text, reply_markup=reply_markup)

async def ask_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = supabase.table('users').select('is_verified').eq('telegram_id', user.id).execute()

    if not user_data.data or not user_data.data[0]['is_verified']:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

    await update.message.reply_text("عنوان سوال خود را وارد کنید:")
    return ASK_TITLE

async def ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ask_title'] = update.message.text
    await update.message.reply_text("شرح کامل سوال خود را وارد کنید:")
    return ASK_CONTENT

async def ask_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ask_content'] = update.message.text

    keyboard = [
        [InlineKeyboardButton("تمرین", callback_data='qcat_homework'),
         InlineKeyboardButton("مفهومی", callback_data='qcat_concept')],
        [InlineKeyboardButton("امتحان", callback_data='qcat_exam'),
         InlineKeyboardButton("پروژه", callback_data='qcat_project')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "دسته‌بندی سوال را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return ASK_CATEGORY

async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_map = {
        'qcat_homework': 'homework',
        'qcat_concept': 'concept',
        'qcat_exam': 'exam',
        'qcat_project': 'project'
    }

    category = category_map.get(query.data, 'concept')

    user = update.effective_user
    user_data = supabase.table('users').select('id').eq('telegram_id', user.id).execute()

    try:
        result = supabase.table('questions').insert({
            'user_id': user_data.data[0]['id'],
            'title': context.user_data['ask_title'],
            'content': context.user_data['ask_content'],
            'category': category,
            'is_answered': False
        }).execute()

        await query.edit_message_text(
            "سوال شما با موفقیت ثبت شد!\n\n"
            f"عنوان: {context.user_data['ask_title']}\n"
            f"دسته: {category}\n\n"
            "به زودی اعضا به سوال شما پاسخ خواهند داد."
        )

    except Exception as e:
        await query.edit_message_text(f"خطا در ثبت سوال: {str(e)}")

    return ConversationHandler.END

async def ask_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ثبت سوال لغو شد.")
    return ConversationHandler.END

async def show_resources_by_category(query, context):
    category = query.data.replace('res_', '')

    resources = supabase.table('resources').select('*, users(first_name, last_name)').eq('category', category).order('created_at', desc=True).limit(10).execute()

    if not resources.data:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='resources')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("منبعی در این دسته موجود نیست.", reply_markup=reply_markup)
        return

    keyboard = []
    for res in resources.data:
        keyboard.append([InlineKeyboardButton(
            f"📄 {res['title'][:40]}...",
            callback_data=f"resource_{res['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='resources')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    category_name = {
        'book': 'کتاب‌ها',
        'paper': 'مقالات',
        'video': 'ویدیوها',
        'tool': 'ابزارها'
    }.get(category, 'منابع')

    await query.edit_message_text(
        f"{category_name}:",
        reply_markup=reply_markup
    )

async def show_resource_detail(query, context):
    resource_id = query.data.replace('resource_', '')
    resource = supabase.table('resources').select('*, users(first_name, last_name)').eq('id', resource_id).execute()

    if not resource.data:
        await query.answer("منبع یافت نشد!")
        return

    res = resource.data[0]

    supabase.table('resources').update({
        'downloads_count': res['downloads_count'] + 1
    }).eq('id', resource_id).execute()

    resource_text = f"📚 {res['title']}\n\n" \
                    f"{res['description']}\n\n" \
                    f"دسته: {res['category']}\n" \
                    f"نوع فایل: {res['file_type']}\n" \
                    f"آپلود توسط: {res['users']['first_name']} {res['users']['last_name']}\n" \
                    f"تاریخ: {datetime.fromisoformat(res['created_at'].replace('Z', '+00:00')).strftime('%Y/%m/%d')}\n" \
                    f"دانلودها: {res['downloads_count'] + 1}"

    if res['tags']:
        resource_text += f"\n\nبرچسب‌ها: {', '.join(res['tags'])}"

    keyboard = []
    if res['file_url']:
        keyboard.append([InlineKeyboardButton("دانلود فایل", url=res['file_url'])])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"res_{res['category']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(resource_text, reply_markup=reply_markup)

async def upload_resource_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = supabase.table('users').select('is_verified').eq('telegram_id', user.id).execute()

    if not user_data.data or not user_data.data[0]['is_verified']:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

    await update.message.reply_text("عنوان منبع را وارد کنید:")
    return UPLOAD_TITLE

async def upload_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_title'] = update.message.text
    await update.message.reply_text("توضیحات منبع را وارد کنید:")
    return UPLOAD_DESC

async def upload_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_desc'] = update.message.text

    keyboard = [
        [InlineKeyboardButton("کتاب", callback_data='ucat_book'),
         InlineKeyboardButton("مقاله", callback_data='ucat_paper')],
        [InlineKeyboardButton("ویدیو", callback_data='ucat_video'),
         InlineKeyboardButton("ابزار", callback_data='ucat_tool')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "دسته‌بندی منبع را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return UPLOAD_CATEGORY

async def upload_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_map = {
        'ucat_book': 'book',
        'ucat_paper': 'paper',
        'ucat_video': 'video',
        'ucat_tool': 'tool'
    }

    context.user_data['upload_category'] = category_map.get(query.data, 'book')

    await query.edit_message_text("لینک فایل را وارد کنید:")
    return UPLOAD_FILE

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_url = update.message.text

    user = update.effective_user
    user_data = supabase.table('users').select('id').eq('telegram_id', user.id).execute()

    try:
        result = supabase.table('resources').insert({
            'title': context.user_data['upload_title'],
            'description': context.user_data['upload_desc'],
            'category': context.user_data['upload_category'],
            'file_url': file_url,
            'file_type': file_url.split('.')[-1] if '.' in file_url else 'unknown',
            'uploaded_by': user_data.data[0]['id']
        }).execute()

        await update.message.reply_text(
            "منبع با موفقیت آپلود شد!\n\n"
            f"عنوان: {context.user_data['upload_title']}\n"
            f"دسته: {context.user_data['upload_category']}\n\n"
            "متشکریم از مشارکت شما!"
        )

    except Exception as e:
        await update.message.reply_text(f"خطا در آپلود منبع: {str(e)}")

    return ConversationHandler.END

async def upload_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("آپلود منبع لغو شد.")
    return ConversationHandler.END
