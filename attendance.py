import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import BOT_TOKEN, ADMIN_ID

from database import (
    create_tables,
    add_user,
    add_group,
    get_group,
    get_all_groups,
    get_all_users,
    update_group_settings,
    get_today_attendance,
    create_today_attendance,
    update_exit,
    get_daily_report,
    get_monthly_user_report
)


# ============================================================
# ابزارهای کمکی
# ============================================================

def get_topic_id(message):
    """
    دریافت Topic ID.
    اگر پیام در Topic باشد message_thread_id برمی‌گردد.
    """

    return message.message_thread_id


def is_group_message(message):
    """
    بررسی می‌کند پیام از گروه یا سوپرگروه آمده باشد.
    """

    if not message:
        return False

    return message.chat.type in ["group", "supergroup"]


def get_current_group(message):
    """
    دریافت گروه + Topic فعلی از دیتابیس.
    """

    if not message:
        return None

    if not is_group_message(message):
        return None

    topic_id = get_topic_id(message)

    if topic_id is None:
        return None

    return get_group(
        message.chat.id,
        topic_id
    )


def normalize_text(text):
    """
    یکسان‌سازی متن.
    """

    if not text:
        return ""

    text = text.strip()

    text = " ".join(
        text.split()
    )

    return text


def is_hello(text):
    """
    تشخیص پیام ورود.
    """

    text = normalize_text(text)

    return text in [
        "سلام",
        "سلام!",
        "سلام !",
        "سلام 👋",
        "سلام👋"
    ]


def is_goodbye(text):
    """
    تشخیص پیام خروج.
    """

    text = normalize_text(text)

    return text in [
        "خدا حافظ",
        "خداحافظ",
        "خدا حافظ!",
        "خداحافظ!",
        "خدا حافظ 👋",
        "خداحافظ 👋",
        "خدا حافظ👋",
        "خداحافظ👋"
    ]


# ============================================================
# /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user_id=user.id,
        name=user.full_name
    )

    await update.effective_message.reply_text(
        f"سلام {user.first_name} 👋\n\n"
        "اطلاعات شما با موفقیت ثبت شد. ✅\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 شناسه کاربری: {user.id}"
    )


# ============================================================
# /groupinfo
# ============================================================

async def group_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ این دستور باید داخل گروه استفاده شود."
        )

        return

    await message.reply_text(
        f"🏢 اطلاعات گروه\n\n"
        f"نام گروه: {message.chat.title}\n"
        f"Group ID: {message.chat.id}\n"
        f"نوع: {message.chat.type}"
    )


# ============================================================
# /topicinfo
# ============================================================

async def topic_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ این دستور باید داخل گروه استفاده شود."
        )

        return

    topic_id = message.message_thread_id

    if topic_id is None:

        await message.reply_text(
            "⚠️ این پیام داخل یک Topic نیست."
        )

        return

    await message.reply_text(
        f"📌 اطلاعات Topic\n\n"
        f"🏢 Group ID: {message.chat.id}\n"
        f"📌 Topic ID: {topic_id}"
    )


# ============================================================
# /register
# ============================================================

async def register_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ این دستور باید داخل گروه استفاده شود."
        )

        return

    topic_id = message.message_thread_id

    if topic_id is None:

        await message.reply_text(
            "⚠️ لطفاً دستور /register را داخل Topic حاضری ارسال کنید."
        )

        return

    add_group(
        group_id=message.chat.id,
        group_name=message.chat.title,
        topic_id=topic_id
    )

    group = get_group(
        message.chat.id,
        topic_id
    )

    await message.reply_text(
        "✅ گروه با موفقیت ثبت شد.\n\n"
        f"🏢 گروه: {message.chat.title}\n"
        f"🆔 Group ID: {message.chat.id}\n"
        f"📌 Topic ID: {topic_id}\n\n"
        "⚙️ تنظیمات پیش‌فرض:\n"
        f"🕐 ورود: {group[3]}\n"
        f"🕐 خروج: {group[4]}\n"
        f"💰 جریمه ورود دیر: {group[5]} افغانی\n"
        f"💰 جریمه خروج زود: {group[6]} افغانی\n\n"
        "اکنون این Topic آماده استفاده است. ✅"
    )


# ============================================================
# پنل مدیریت
# ============================================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    message = update.effective_message

    if user.id != ADMIN_ID:

        await message.reply_text(
            "⛔ شما دسترسی به پنل مدیریت ندارید."
        )

        return

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ پنل مدیریت را داخل Topic حاضری گروه باز کنید."
        )

        return

    topic_id = message.message_thread_id

    if topic_id is None:

        await message.reply_text(
            "⚠️ لطفاً /admin را داخل Topic حاضری اجرا کنید."
        )

        return

    group = get_group(
        message.chat.id,
        topic_id
    )

    if not group:

        await message.reply_text(
            "⚠️ این Topic هنوز ثبت نشده است.\n\n"
            "ابتدا دستور زیر را اجرا کنید:\n"
            "/register"
        )

        return

    keyboard = [

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات حاضری",
                callback_data="attendance_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="manage_users"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 گزارش امروز",
                callback_data="daily_report"
            )
        ],

        [
            InlineKeyboardButton(
                "📅 گزارش ماهانه",
                callback_data="monthly_report"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 مجموع جریمه‌ها",
                callback_data="total_fines"
            )
        ]

    ]

    await message.reply_text(
        "👨‍💼 پنل مدیریت\n\n"
        f"🏢 گروه: {group[1]}\n"
        f"📌 Topic: {group[2]}\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# Callback پنل مدیریت
# ============================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if user.id != ADMIN_ID:

        await query.answer(
            "⛔ شما دسترسی ندارید.",
            show_alert=True
        )

        return

    message = query.message

    if not message:

        return

    group_id = message.chat.id
    topic_id = message.message_thread_id

    if topic_id is None:

        await query.message.reply_text(
            "⚠️ این پنل باید داخل Topic حاضری باشد."
        )

        return

    group = get_group(
        group_id,
        topic_id
    )

    if not group:

        await query.message.reply_text(
            "⚠️ این Topic ثبت نشده است.\n\n"
            "ابتدا /register را اجرا کنید."
        )

        return

    # ========================================================
    # تنظیمات حاضری
    # ========================================================

    if query.data == "attendance_settings":

        keyboard = [

            [
                InlineKeyboardButton(
                    "🕐 ساعت ورود",
                    callback_data="set_entry_time"
                )
            ],

            [
                InlineKeyboardButton(
                    "🕐 ساعت خروج",
                    callback_data="set_exit_time"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 جریمه ورود دیر",
                    callback_data="set_late_fine"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 جریمه خروج زود",
                    callback_data="set_early_fine"
                )
            ],

            [
                InlineKeyboardButton(
                    "📊 مشاهده تنظیمات",
                    callback_data="show_settings"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.message.edit_text(
            "⚙️ تنظیمات حاضری\n\n"
            f"🏢 گروه: {group[1]}\n"
            f"📌 Topic: {group[2]}\n\n"
            "گزینه موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # ساعت ورود
    # ========================================================

    if query.data == "set_entry_time":

        context.user_data["admin_action"] = "entry_time"

        await query.message.reply_text(
            "🕐 ساعت ورود جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "08:00"
        )

        return

    # ========================================================
    # ساعت خروج
    # ========================================================

    if query.data == "set_exit_time":

        context.user_data["admin_action"] = "exit_time"

        await query.message.reply_text(
            "🕐 ساعت خروج جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "17:00"
        )

        return

    # ========================================================
    # جریمه ورود
    # ========================================================

    if query.data == "set_late_fine":

        context.user_data["admin_action"] = "late_fine"

        await query.message.reply_text(
            "💰 مبلغ جریمه ورود دیر را ارسال کنید.\n\n"
            "مثال:\n"
            "50"
        )

        return

    # ========================================================
    # جریمه خروج
    # ========================================================

    if query.data == "set_early_fine":

        context.user_data["admin_action"] = "early_fine"

        await query.message.reply_text(
            "💰 مبلغ جریمه خروج زود را ارسال کنید.\n\n"
            "مثال:\n"
            "50"
        )

        return

    # ========================================================
    # نمایش تنظیمات
    # ========================================================

    if query.data == "show_settings":

        await query.message.reply_text(
            "⚙️ تنظیمات حاضری\n\n"
            f"🏢 گروه: {group[1]}\n"
            f"📌 Topic ID: {group[2]}\n\n"
            f"🕐 ساعت ورود: {group[3]}\n"
            f"🕐 ساعت خروج: {group[4]}\n\n"
            f"💰 جریمه ورود دیر: {group[5]} افغانی\n"
            f"💰 جریمه خروج زود: {group[6]} افغانی"
        )

        return

    # ========================================================
    # مدیریت کاربران
    # ========================================================

    if query.data == "manage_users":

        users = get_all_users()

        if not users:

            text = "👥 هنوز هیچ کاربری ثبت نشده است."

        else:

            text = "👥 کاربران ثبت‌شده\n\n"

            for number, user_data in enumerate(
                users,
                start=1
            ):

                user_id = user_data[0]
                name = user_data[1]
                status = user_data[2]

                status_text = (
                    "فعال ✅"
                    if status == "active"
                    else "غیرفعال ❌"
                )

                text += (
                    f"{number}. {name}\n"
                    f"🆔 {user_id}\n"
                    f"📌 {status_text}\n\n"
                )

        keyboard = [[
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_admin"
            )
        ]]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # گزارش امروز
    # ========================================================

    if query.data == "daily_report":

        today = datetime.now().strftime("%Y-%m-%d")

        report = get_daily_report(
            group_id,
            topic_id,
            today
        )

        if not report:

            text = (
                "📊 گزارش امروز\n\n"
                f"📅 {today}\n\n"
                "هنوز اطلاعاتی ثبت نشده است."
            )

        else:

            text = (
                "📊 گزارش امروز\n\n"
                f"📅 {today}\n\n"
            )

            total_fine = 0

            for number, row in enumerate(
                report,
                start=1
            ):

                name = row[0]
                entry = row[1] or "—"
                exit_time = row[2] or "—"

                entry_fine = row[3] or 0
                exit_fine = row[4] or 0

                total = entry_fine + exit_fine

                total_fine += total

                text += (
                    f"{number}. {name}\n"
                    f"🟢 ورود: {entry}\n"
                    f"🔵 خروج: {exit_time}\n"
                    f"💰 جریمه: {total} افغانی\n\n"
                )

            text += (
                "━━━━━━━━━━━━\n"
                f"💰 مجموع جریمه: {total_fine} افغانی"
            )

        keyboard = [[
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_admin"
            )
        ]]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # گزارش ماهانه
    # ========================================================

    if query.data == "monthly_report":

        now = datetime.now()

        users = get_all_users()

        text = (
            "📅 گزارش ماهانه\n\n"
            f"📆 {now.year}-{now.month:02d}\n\n"
        )

        total_fine_all = 0

        for number, user_data in enumerate(
            users,
            start=1
        ):

            user_id = user_data[0]
            name = user_data[1]

            report = get_monthly_user_report(
                user_id,
                group_id,
                topic_id,
                now.year,
                now.month
            )

            days = report[0] or 0
            late = report[1] or 0
            early = report[2] or 0

            entry_fine = report[3] or 0
            exit_fine = report[4] or 0

            total = entry_fine + exit_fine

            total_fine_all += total

            text += (
                f"{number}. {name}\n"
                f"📆 روزهای ثبت‌شده: {days}\n"
                f"🟡 ورود دیر: {late}\n"
                f"🔴 خروج زود: {early}\n"
                f"💰 جریمه ورود: {entry_fine} افغانی\n"
                f"💰 جریمه خروج: {exit_fine} افغانی\n"
                f"💵 مجموع: {total} افغانی\n\n"
            )

        text += (
            "━━━━━━━━━━━━\n"
            f"💰 مجموع جریمه‌ها: "
            f"{total_fine_all} افغانی"
        )

        keyboard = [[
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_admin"
            )
        ]]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # مجموع جریمه‌ها
    # ========================================================

    if query.data == "total_fines":

        now = datetime.now()

        users = get_all_users()

        text = "💰 مجموع جریمه‌ها\n\n"

        grand_total = 0

        for user_data in users:

            user_id = user_data[0]
            name = user_data[1]

            report = get_monthly_user_report(
                user_id,
                group_id,
                topic_id,
                now.year,
                now.month
            )

            entry_fine = report[3] or 0
            exit_fine = report[4] or 0

            total = entry_fine + exit_fine

            grand_total += total

            text += (
                f"👤 {name}\n"
                f"💵 {total} افغانی\n\n"
            )

        text += (
            "━━━━━━━━━━━━\n"
            f"💰 مجموع کل: {grand_total} افغانی"
        )

        keyboard = [[
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_admin"
            )
        ]]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ========================================================
    # بازگشت
    # ========================================================

    if query.data == "back_admin":

        keyboard = [

            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات حاضری",
                    callback_data="attendance_settings"
                )
            ],

            [
                InlineKeyboardButton(
                    "👥 کاربران",
                    callback_data="manage_users"
                )
            ],

            [
                InlineKeyboardButton(
                    "📊 گزارش امروز",
                    callback_data="daily_report"
                )
            ],

            [
                InlineKeyboardButton(
                    "📅 گزارش ماهانه",
                    callback_data="monthly_report"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 مجموع جریمه‌ها",
                    callback_data="total_fines"
                )
            ]

        ]

        await query.message.edit_text(
            "👨‍💼 پنل مدیریت\n\n"
            f"🏢 گروه: {group[1]}\n"
            f"📌 Topic: {group[2]}\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


# ============================================================
# دریافت تنظیمات مدیر
# ============================================================

async def admin_setting_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    message = update.effective_message

    if user.id != ADMIN_ID:
        return

    action = context.user_data.get("admin_action")

    if not action:
        return

    if not message:
        return

    if not is_group_message(message):
        return

    topic_id = message.message_thread_id

    if topic_id is None:
        return

    group = get_group(
        message.chat.id,
        topic_id
    )

    if not group:

        await message.reply_text(
            "⚠️ این Topic ثبت نشده است.\n\n"
            "ابتدا /register را اجرا کنید."
        )

        context.user_data.pop(
            "admin_action",
            None
        )

        return

    value = normalize_text(
        message.text
    )

    # ========================================================
    # ساعت ورود
    # ========================================================

    if action == "entry_time":

        try:

            datetime.strptime(
                value,
                "%H:%M"
            )

        except ValueError:

            await message.reply_text(
                "❌ فرمت ساعت اشتباه است.\n\n"
                "مثال صحیح:\n"
                "08:00"
            )

            return

        update_group_settings(
            group_id=message.chat.id,
            topic_id=topic_id,
            entry_time=value
        )

        await message.reply_text(
            "✅ ساعت ورود تغییر کرد.\n\n"
            f"🕐 ساعت جدید: {value}"
        )

    # ========================================================
    # ساعت خروج
    # ========================================================

    elif action == "exit_time":

        try:

            datetime.strptime(
                value,
                "%H:%M"
            )

        except ValueError:

            await message.reply_text(
                "❌ فرمت ساعت اشتباه است.\n\n"
                "مثال صحیح:\n"
                "17:00"
            )

            return

        update_group_settings(
            group_id=message.chat.id,
            topic_id=topic_id,
            exit_time=value
        )

        await message.reply_text(
            "✅ ساعت خروج تغییر کرد.\n\n"
            f"🕐 ساعت جدید: {value}"
        )

    # ========================================================
    # جریمه ورود
    # ========================================================

    elif action == "late_fine":

        try:

            amount = int(value)

            if amount < 0:
                raise ValueError

        except ValueError:

            await message.reply_text(
                "❌ مبلغ نامعتبر است.\n\n"
                "فقط عدد وارد کنید.\n\n"
                "مثال:\n"
                "50"
            )

            return

        update_group_settings(
            group_id=message.chat.id,
            topic_id=topic_id,
            late_entry_fine=amount
        )

        await message.reply_text(
            "✅ جریمه ورود دیر تغییر کرد.\n\n"
            f"💰 مبلغ جدید: {amount} افغانی"
        )

    # ========================================================
    # جریمه خروج
    # ========================================================

    elif action == "early_fine":

        try:

            amount = int(value)

            if amount < 0:
                raise ValueError

        except ValueError:

            await message.reply_text(
                "❌ مبلغ نامعتبر است.\n\n"
                "فقط عدد وارد کنید.\n\n"
                "مثال:\n"
                "50"
            )

            return

        update_group_settings(
            group_id=message.chat.id,
            topic_id=topic_id,
            early_exit_fine=amount
        )

        await message.reply_text(
            "✅ جریمه خروج زود تغییر کرد.\n\n"
            f"💰 مبلغ جدید: {amount} افغانی"
        )

    context.user_data.pop(
        "admin_action",
        None
    )


# ============================================================
# حضور و غیاب
# ============================================================

async def attendance_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not message:
        return

    if not is_group_message(message):
        return

    topic_id = message.message_thread_id

    if topic_id is None:
        return

    # --------------------------------------------------------
    # دریافت متن یا Caption
    # --------------------------------------------------------

    text = message.text or message.caption

    if not text:
        return

    text = normalize_text(text)

    # فقط سلام یا خداحافظ
    if not is_hello(text) and not is_goodbye(text):
        return

    # --------------------------------------------------------
    # ثبت کاربر
    # --------------------------------------------------------

    user = message.from_user

    if not user:
        return

    add_user(
        user_id=user.id,
        name=user.full_name
    )

    # --------------------------------------------------------
    # دریافت گروه
    # --------------------------------------------------------

    group = get_group(
        message.chat.id,
        topic_id
    )

    # اگر گروه ثبت نشده
    if not group:

        await message.reply_text(
            "⚠️ این Topic هنوز برای حضور و غیاب ثبت نشده است.\n\n"
            "مدیر گروه باید داخل همین Topic دستور زیر را ارسال کند:\n\n"
            "/register"
        )

        return

    (
        group_id,
        group_name,
        saved_topic_id,
        entry_time,
        exit_time,
        late_entry_fine,
        early_exit_fine,
        status
    ) = group

    # گروه غیرفعال
    if status != "active":
        return

    # --------------------------------------------------------
    # زمان فعلی
    # --------------------------------------------------------

    now = datetime.now()

    today = now.strftime(
        "%Y-%m-%d"
    )

    current_time = now.strftime(
        "%H:%M"
    )

    # ========================================================
    # ورود
    # ========================================================

    if is_hello(text):

        attendance = get_today_attendance(
            user.id,
            group_id,
            saved_topic_id,
            today
        )

        # ورود قبلاً ثبت شده
        if attendance:

            await message.reply_text(
                "⚠️ ورود شما قبلاً ثبت شده است.\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {attendance[5]}"
            )

            return

        # محاسبه جریمه
        entry_fine = 0

        if current_time > entry_time:

            entry_fine = late_entry_fine

        # ثبت
        create_today_attendance(
            user_id=user.id,
            group_id=group_id,
            topic_id=saved_topic_id,
            date=today,
            entry_time=current_time,
            entry_fine=entry_fine
        )

        # پیام جریمه
        if entry_fine > 0:

            await message.reply_text(
                "⚠️ ورود ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {entry_time}\n\n"
                f"💰 جریمه تأخیر: "
                f"{entry_fine} افغانی"
            )

        else:

            await message.reply_text(
                "🟢 ورود ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {entry_time}\n\n"
                "💰 جریمه: 0 افغانی"
            )

        return

    # ========================================================
    # خروج
    # ========================================================

    if is_goodbye(text):

        attendance = get_today_attendance(
            user.id,
            group_id,
            saved_topic_id,
            today
        )

        # ورود ثبت نشده
        if not attendance:

            await message.reply_text(
                "⚠️ برای امروز ورود شما ثبت نشده است.\n\n"
                "ابتدا باید ورود خود را با پیام «سلام» ثبت کنید."
            )

            return

        # خروج قبلاً ثبت شده
        if attendance[6]:

            await message.reply_text(
                "⚠️ خروج شما قبلاً ثبت شده است.\n\n"
                f"🕐 زمان خروج: {attendance[6]}"
            )

            return

        # محاسبه جریمه خروج
        exit_fine = 0

        if current_time < exit_time:

            exit_fine = early_exit_fine

        # ثبت خروج
        update_exit(
            attendance_id=attendance[0],
            exit_time=current_time,
            exit_fine=exit_fine
        )

        # پیام
        if exit_fine > 0:

            await message.reply_text(
                "⚠️ خروج ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان خروج: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {exit_time}\n\n"
                f"💰 جریمه خروج زودهنگام: "
                f"{exit_fine} افغانی"
            )

        else:

            await message.reply_text(
                "🔵 خروج ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان خروج: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {exit_time}\n\n"
                "💰 جریمه: 0 افغانی"
            )

        return


# ============================================================
# کاربران
# ============================================================

async def show_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.effective_message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    users = get_all_users()

    if not users:

        await update.effective_message.reply_text(
            "👥 هنوز هیچ کاربری ثبت نشده است."
        )

        return

    text = "👥 کاربران ثبت‌شده\n\n"

    for number, user_data in enumerate(
        users,
        start=1
    ):

        user_id = user_data[0]
        name = user_data[1]
        status = user_data[2]

        status_text = (
            "فعال ✅"
            if status == "active"
            else "غیرفعال ❌"
        )

        text += (
            f"{number}. {name}\n"
            f"🆔 {user_id}\n"
            f"📌 وضعیت: {status_text}\n\n"
        )

    await update.effective_message.reply_text(
        text
    )


# ============================================================
# گزارش روزانه
# ============================================================

async def daily_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    message = update.effective_message

    if user.id != ADMIN_ID:

        await message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ این دستور باید داخل Topic حاضری باشد."
        )

        return

    topic_id = message.message_thread_id

    if topic_id is None:

        await message.reply_text(
            "⚠️ این دستور باید داخل Topic حاضری باشد."
        )

        return

    group = get_group(
        message.chat.id,
        topic_id
    )

    if not group:

        await message.reply_text(
            "⚠️ این Topic ثبت نشده است.\n\n"
            "ابتدا /register را اجرا کنید."
        )

        return

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    report = get_daily_report(
        message.chat.id,
        topic_id,
        today
    )

    if not report:

        await message.reply_text(
            "📊 گزارش امروز\n\n"
            f"📅 تاریخ: {today}\n\n"
            "هنوز هیچ حضور و غیابی ثبت نشده است."
        )

        return

    text = (
        "📊 گزارش حضور امروز\n\n"
        f"🏢 گروه: {group[1]}\n"
        f"📌 Topic: {topic_id}\n"
        f"📅 تاریخ: {today}\n\n"
    )

    total_fine = 0

    for number, row in enumerate(
        report,
        start=1
    ):

        name = row[0]
        entry = row[1] or "ثبت نشده"
        exit_time = row[2] or "ثبت نشده"

        entry_fine = row[3] or 0
        exit_fine = row[4] or 0

        total = entry_fine + exit_fine

        total_fine += total

        text += (
            f"{number}️⃣ {name}\n"
            f"🟢 ورود: {entry}\n"
            f"🔵 خروج: {exit_time}\n"
            f"💰 جریمه: {total} افغانی\n\n"
        )

    text += (
        "━━━━━━━━━━━━\n"
        f"💰 مجموع جریمه: {total_fine} افغانی"
    )

    await message.reply_text(
        text
    )


# ============================================================
# گزارش ماهانه
# ============================================================

async def monthly_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    message = update.effective_message

    if user.id != ADMIN_ID:

        await message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    if not is_group_message(message):

        await message.reply_text(
            "⚠️ این دستور باید داخل Topic حاضری باشد."
        )

        return

    topic_id = message.message_thread_id

    if topic_id is None:

        await message.reply_text(
            "⚠️ این دستور باید داخل Topic حاضری باشد."
        )

        return

    group = get_group(
        message.chat.id,
        topic_id
    )

    if not group:

        await message.reply_text(
            "⚠️ این Topic ثبت نشده است."
        )

        return

    now = datetime.now()

    users = get_all_users()

    if not users:

        await message.reply_text(
            "👥 هیچ کاربری ثبت نشده است."
        )

        return

    text = (
        "📅 گزارش ماهانه حضور و غیاب\n\n"
        f"🏢 گروه: {group[1]}\n"
        f"📌 Topic: {topic_id}\n"
        f"📆 ماه: {now.year}-{now.month:02d}\n\n"
    )

    total_fine_all = 0

    for number, user_data in enumerate(
        users,
        start=1
    ):

        user_id = user_data[0]
        name = user_data[1]

        report = get_monthly_user_report(
            user_id,
            message.chat.id,
            topic_id,
            now.year,
            now.month
        )

        days = report[0] or 0
        late = report[1] or 0
        early = report[2] or 0

        entry_fine = report[3] or 0
        exit_fine = report[4] or 0

        total = entry_fine + exit_fine

        total_fine_all += total

        text += (
            f"{number}️⃣ {name}\n"
            f"📆 روزهای ثبت‌شده: {days}\n"
            f"🟡 ورود دیر: {late}\n"
            f"🔴 خروج زود: {early}\n"
            f"💰 جریمه ورود: {entry_fine} افغانی\n"
            f"💰 جریمه خروج: {exit_fine} افغانی\n"
            f"💵 مجموع: {total} افغانی\n\n"
        )

    text += (
        "━━━━━━━━━━━━\n"
        f"💰 مجموع جریمه همه کاربران: "
        f"{total_fine_all} افغانی"
    )

    await message.reply_text(
        text
    )


# ============================================================
# اجرای ربات
# ============================================================

async def main():

    # ساخت دیتابیس
    create_tables()

    # ساخت Application
    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # دستورات
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "register",
            register_group
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_panel
        )
    )

    app.add_handler(
        CommandHandler(
            "users",
            show_users
        )
    )

    app.add_handler(
        CommandHandler(
            "groupinfo",
            group_info
        )
    )

    app.add_handler(
        CommandHandler(
            "topicinfo",
            topic_info
        )
    )

    app.add_handler(
        CommandHandler(
            "report",
            daily_report
        )
    )

    app.add_handler(
        CommandHandler(
            "monthly",
            monthly_report
        )
    )

    # --------------------------------------------------------
    # دکمه‌های پنل
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_callback
        )
    )

    # --------------------------------------------------------
    # تنظیمات مدیر
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            admin_setting_input
        ),
        group=0
    )

    # --------------------------------------------------------
    # حضور و غیاب
    #
    # filters.ALL باعث می‌شود:
    # عکس + Caption
    # متن
    # و سایر پیام‌ها بررسی شوند.
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND,
            attendance_handler
        ),
        group=1
    )

    print(
        "===================================="
    )

    print(
        "Attendance Bot Started..."
    )

    print(
        "Multi Group / Multi Topic Mode"
    )

    print(
        "===================================="
    )

    # --------------------------------------------------------
    # اجرای ربات
    # --------------------------------------------------------

    await app.initialize()

    await app.start()

    await app.updater.start_polling()

    try:

        await asyncio.Event().wait()

    except (
        KeyboardInterrupt,
        SystemExit
    ):

        pass

    finally:

        await app.updater.stop()

        await app.stop()

        await app.shutdown()


# ============================================================
# شروع
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )