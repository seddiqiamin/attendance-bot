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
    get_group,
    add_group,
    get_today_attendance,
    create_today_attendance,
    update_exit,
    update_group_settings,
    get_all_users,
    get_daily_report,
    get_monthly_user_report
)


# ==========================================
# تنظیمات گروه
# ==========================================

GROUP_ID = -1004408019392
ATTENDANCE_TOPIC_ID = 205


# ==========================================
# /start
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user_id=user.id,
        name=user.full_name
    )

    await update.message.reply_text(
        f"سلام {user.first_name} 👋\n\n"
        "اطلاعات شما با موفقیت ثبت شد. ✅\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 شناسه کاربری: {user.id}"
    )


# ==========================================
# اطلاعات گروه
# ==========================================

async def group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat

    await update.message.reply_text(
        f"🏢 اطلاعات گروه\n\n"
        f"نام گروه: {chat.title}\n"
        f"Group ID: {chat.id}\n"
        f"نوع: {chat.type}"
    )


# ==========================================
# اطلاعات Topic
# ==========================================

async def topic_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    await message.reply_text(
        f"📌 اطلاعات Topic\n\n"
        f"Group ID: {message.chat_id}\n"
        f"Topic ID: {message.message_thread_id}"
    )


# ==========================================
# پنل مدیریت
# ==========================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی به پنل مدیریت ندارید."
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
                "👥 مدیریت کاربران",
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

    await update.message.reply_text(
        "👨‍💼 پنل مدیریت\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================================
# حضور و غیاب
# ==========================================

async def attendance_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not message:
        return

    # فقط گروه مشخص
    if message.chat_id != GROUP_ID:
        return

    # فقط Topic حاضری
    if message.message_thread_id != ATTENDANCE_TOPIC_ID:
        return

    # دریافت متن یا Caption عکس
    text = message.text or message.caption

    if not text:
        return

    # حذف فاصله‌های اضافی
    text = " ".join(text.strip().split())

    user = message.from_user

    if not user:
        return

    # ثبت / بروزرسانی کاربر
    add_user(
        user_id=user.id,
        name=user.full_name
    )

    # زمان فعلی
    now = datetime.now()

    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    # ==========================================
    # دریافت تنظیمات گروه
    # ==========================================

    group = get_group(GROUP_ID)

    # اگر گروه هنوز ثبت نشده
    if not group:

        add_group(
            group_id=GROUP_ID,
            group_name=message.chat.title,
            topic_id=ATTENDANCE_TOPIC_ID
        )

        group = get_group(GROUP_ID)

    if not group:

        await message.reply_text(
            "❌ تنظیمات گروه پیدا نشد."
        )

        return

    (
        group_id,
        group_name,
        topic_id,
        entry_time,
        exit_time,
        late_entry_fine,
        early_exit_fine
    ) = group

    # ==========================================
    # ورود
    # ==========================================

    if text in [
        "سلام",
        "سلام!",
        "سلام !"
    ]:

        attendance = get_today_attendance(
            user.id,
            GROUP_ID,
            today
        )

        # ورود قبلاً ثبت شده
        if attendance:

            await message.reply_text(
                f"⚠️ ورود شما قبلاً ثبت شده است.\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {attendance[4]}"
            )

            return

        # محاسبه جریمه ورود
        entry_fine = 0

        if current_time > entry_time:

            entry_fine = late_entry_fine

        # ثبت ورود
        create_today_attendance(
            user_id=user.id,
            group_id=GROUP_ID,
            date=today,
            entry_time=current_time,
            entry_fine=entry_fine
        )

        # پیام
        if entry_fine > 0:

            await message.reply_text(
                f"⚠️ ورود ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {entry_time}\n\n"
                f"💰 جریمه تأخیر: "
                f"{entry_fine} افغانی"
            )

        else:

            await message.reply_text(
                f"🟢 ورود ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان ورود: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {entry_time}\n\n"
                f"💰 جریمه: 0 افغانی"
            )

        return

    # ==========================================
    # خروج
    # ==========================================

    if text in [
        "خدا حافظ",
        "خداحافظ",
        "خدا حافظ!",
        "خداحافظ!"
    ]:

        attendance = get_today_attendance(
            user.id,
            GROUP_ID,
            today
        )

        # ورود ثبت نشده
        if not attendance:

            await message.reply_text(
                f"⚠️ برای امروز ورود شما ثبت نشده است.\n\n"
                f"ابتدا باید ورود خود را ثبت کنید."
            )

            return

        # خروج قبلاً ثبت شده
        if attendance[5]:

            await message.reply_text(
                f"⚠️ خروج شما قبلاً ثبت شده است.\n\n"
                f"🕐 زمان خروج: {attendance[5]}"
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
                f"⚠️ خروج ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان خروج: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {exit_time}\n\n"
                f"💰 جریمه خروج زودهنگام: "
                f"{exit_fine} افغانی"
            )

        else:

            await message.reply_text(
                f"🔵 خروج ثبت شد\n\n"
                f"👤 {user.full_name}\n"
                f"🕐 زمان خروج: {current_time}\n"
                f"⏰ ساعت تعیین‌شده: {exit_time}\n\n"
                f"💰 جریمه: 0 افغانی"
            )

        return


# ==========================================
# Callback پنل مدیریت
# ==========================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user = query.from_user

    # فقط مدیر
    if user.id != ADMIN_ID:

        await query.answer(
            "⛔ شما دسترسی ندارید.",
            show_alert=True
        )

        return

    await query.answer()

    # ==========================================
    # تنظیمات حاضری
    # ==========================================

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
            "گزینه موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # تنظیم ساعت ورود
    # ==========================================

    if query.data == "set_entry_time":

        context.user_data["admin_action"] = "entry_time"

        await query.message.reply_text(
            "🕐 ساعت ورود جدید را ارسال کنید.\n\n"
            "فرمت صحیح:\n"
            "08:00"
        )

        return

    # ==========================================
    # تنظیم ساعت خروج
    # ==========================================

    if query.data == "set_exit_time":

        context.user_data["admin_action"] = "exit_time"

        await query.message.reply_text(
            "🕐 ساعت خروج جدید را ارسال کنید.\n\n"
            "فرمت صحیح:\n"
            "17:00"
        )

        return

    # ==========================================
    # تنظیم جریمه ورود
    # ==========================================

    if query.data == "set_late_fine":

        context.user_data["admin_action"] = "late_fine"

        await query.message.reply_text(
            "💰 مبلغ جریمه ورود دیر را ارسال کنید.\n\n"
            "مثال:\n"
            "50"
        )

        return

    # ==========================================
    # تنظیم جریمه خروج
    # ==========================================

    if query.data == "set_early_fine":

        context.user_data["admin_action"] = "early_fine"

        await query.message.reply_text(
            "💰 مبلغ جریمه خروج زود را ارسال کنید.\n\n"
            "مثال:\n"
            "50"
        )

        return

    # ==========================================
    # مشاهده تنظیمات
    # ==========================================

    if query.data == "show_settings":

        group = get_group(GROUP_ID)

        if not group:

            await query.message.reply_text(
                "⚠️ تنظیمات گروه هنوز ثبت نشده است."
            )

            return

        (
            group_id,
            group_name,
            topic_id,
            entry_time,
            exit_time,
            late_entry_fine,
            early_exit_fine
        ) = group

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="attendance_settings"
                )
            ]
        ]

        await query.message.edit_text(
            f"⚙️ تنظیمات حاضری\n\n"
            f"🏢 گروه: {group_name}\n"
            f"📌 Topic ID: {topic_id}\n\n"
            f"🕐 ساعت ورود: {entry_time}\n"
            f"🕐 ساعت خروج: {exit_time}\n\n"
            f"💰 جریمه ورود دیر: "
            f"{late_entry_fine} افغانی\n"
            f"💰 جریمه خروج زود: "
            f"{early_exit_fine} افغانی",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # مدیریت کاربران
    # ==========================================

    if query.data == "manage_users":

        users = get_all_users()

        if not users:

            text = "👥 هیچ کاربری ثبت نشده است."

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
                    f"📌 وضعیت: {status_text}\n\n"
                )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_admin"
                )
            ]
        ]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # گزارش امروز
    # ==========================================

    if query.data == "daily_report":

        today = datetime.now().strftime("%Y-%m-%d")

        report = get_daily_report(
            GROUP_ID,
            today
        )

        if not report:

            text = (
                f"📊 گزارش حضور امروز\n\n"
                f"📅 تاریخ: {today}\n\n"
                "هنوز هیچ حضور و غیابی ثبت نشده است."
            )

        else:

            text = (
                f"📊 گزارش حضور امروز\n\n"
                f"📅 تاریخ: {today}\n\n"
            )

            total_fine = 0
            total_people = 0

            for number, row in enumerate(
                report,
                start=1
            ):

                name = row[0]
                entry = row[1] or "ثبت نشده"
                exit_time = row[2] or "ثبت نشده"
                entry_fine = row[3] or 0
                exit_fine = row[4] or 0

                fine = entry_fine + exit_fine

                total_fine += fine
                total_people += 1

                text += (
                    f"{number}. {name}\n"
                    f"🟢 ورود: {entry}\n"
                    f"🔵 خروج: {exit_time}\n"
                    f"💰 جریمه: {fine} افغانی\n\n"
                )

            text += (
                "━━━━━━━━━━━━\n"
                f"👥 تعداد ثبت‌شده: {total_people}\n"
                f"💰 مجموع جریمه: {total_fine} افغانی"
            )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_admin"
                )
            ]
        ]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # گزارش ماهانه
    # ==========================================

    if query.data == "monthly_report":

        now = datetime.now()

        year = now.year
        month = now.month

        users = get_all_users()

        if not users:

            text = "👥 هیچ کاربری ثبت نشده است."

        else:

            text = (
                f"📅 گزارش ماهانه حضور و غیاب\n\n"
                f"📆 ماه: {year}-{month:02d}\n\n"
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
                    GROUP_ID,
                    year,
                    month
                )

                days = report[0] or 0
                late_entries = report[1] or 0
                early_exits = report[2] or 0
                entry_fines = report[3] or 0
                exit_fines = report[4] or 0

                total_fine = (
                    entry_fines +
                    exit_fines
                )

                total_fine_all += total_fine

                text += (
                    f"{number}️⃣ {name}\n"
                    f"📆 روزهای ثبت‌شده: {days}\n"
                    f"🟡 ورودهای دیر: {late_entries}\n"
                    f"🔴 خروج‌های زود: {early_exits}\n"
                    f"💰 جریمه ورود: "
                    f"{entry_fines} افغانی\n"
                    f"💰 جریمه خروج: "
                    f"{exit_fines} افغانی\n"
                    f"💵 مجموع: "
                    f"{total_fine} افغانی\n\n"
                )

            text += (
                "━━━━━━━━━━━━\n"
                f"💰 مجموع جریمه همه کاربران: "
                f"{total_fine_all} افغانی"
            )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_admin"
                )
            ]
        ]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # مجموع جریمه‌ها
    # ==========================================

    if query.data == "total_fines":

        now = datetime.now()

        year = now.year
        month = now.month

        users = get_all_users()

        text = (
            "💰 مجموع جریمه‌ها\n\n"
            f"📆 ماه: {year}-{month:02d}\n\n"
        )

        grand_total = 0

        for user_data in users:

            user_id = user_data[0]
            name = user_data[1]

            report = get_monthly_user_report(
                user_id,
                GROUP_ID,
                year,
                month
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
            f"💰 مجموع کل: "
            f"{grand_total} افغانی"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_admin"
                )
            ]
        ]

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==========================================
    # بازگشت به پنل اصلی
    # ==========================================

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
                    "👥 مدیریت کاربران",
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
            "یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


# ==========================================
# دریافت مقدار تنظیمات مدیر
# ==========================================

async def admin_setting_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    # فقط مدیر
    if user.id != ADMIN_ID:
        return

    action = context.user_data.get(
        "admin_action"
    )

    # اگر مدیر در حال تنظیم چیزی نیست
    if not action:
        return

    if not update.message:
        return

    value = update.message.text.strip()

    # ==========================================
    # ساعت ورود
    # ==========================================

    if action == "entry_time":

        try:

            datetime.strptime(
                value,
                "%H:%M"
            )

        except ValueError:

            await update.message.reply_text(
                "❌ فرمت ساعت اشتباه است.\n\n"
                "فرمت صحیح:\n"
                "08:00"
            )

            return

        update_group_settings(
            group_id=GROUP_ID,
            entry_time=value
        )

        await update.message.reply_text(
            f"✅ ساعت ورود با موفقیت تغییر کرد.\n\n"
            f"🕐 ساعت جدید: {value}"
        )

    # ==========================================
    # ساعت خروج
    # ==========================================

    elif action == "exit_time":

        try:

            datetime.strptime(
                value,
                "%H:%M"
            )

        except ValueError:

            await update.message.reply_text(
                "❌ فرمت ساعت اشتباه است.\n\n"
                "فرمت صحیح:\n"
                "17:00"
            )

            return

        update_group_settings(
            group_id=GROUP_ID,
            exit_time=value
        )

        await update.message.reply_text(
            f"✅ ساعت خروج با موفقیت تغییر کرد.\n\n"
            f"🕐 ساعت جدید: {value}"
        )

    # ==========================================
    # جریمه ورود
    # ==========================================

    elif action == "late_fine":

        try:

            amount = int(value)

            if amount < 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ مبلغ نامعتبر است.\n\n"
                "فقط عدد وارد کنید.\n"
                "مثال:\n"
                "50"
            )

            return

        update_group_settings(
            group_id=GROUP_ID,
            late_entry_fine=amount
        )

        await update.message.reply_text(
            f"✅ جریمه ورود دیر تغییر کرد.\n\n"
            f"💰 مبلغ جدید: {amount} افغانی"
        )

    # ==========================================
    # جریمه خروج
    # ==========================================

    elif action == "early_fine":

        try:

            amount = int(value)

            if amount < 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ مبلغ نامعتبر است.\n\n"
                "فقط عدد وارد کنید.\n"
                "مثال:\n"
                "50"
            )

            return

        update_group_settings(
            group_id=GROUP_ID,
            early_exit_fine=amount
        )

        await update.message.reply_text(
            f"✅ جریمه خروج زود تغییر کرد.\n\n"
            f"💰 مبلغ جدید: {amount} افغانی"
        )

    # پاک کردن حالت تنظیم
    context.user_data.pop(
        "admin_action",
        None
    )


# ==========================================
# /users
# ==========================================

async def show_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    users = get_all_users()

    if not users:

        await update.message.reply_text(
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

    await update.message.reply_text(text)


# ==========================================
# /report
# ==========================================

async def daily_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    report = get_daily_report(
        GROUP_ID,
        today
    )

    if not report:

        await update.message.reply_text(
            f"📊 گزارش حضور امروز\n\n"
            f"📅 تاریخ: {today}\n\n"
            "هنوز هیچ حضور و غیابی ثبت نشده است."
        )

        return

    text = (
        f"📊 گزارش حضور امروز\n\n"
        f"📅 تاریخ: {today}\n\n"
    )

    total_fine = 0
    total_people = 0

    for number, row in enumerate(
        report,
        start=1
    ):

        name = row[0]
        entry_time = row[1]
        exit_time = row[2]
        entry_fine = row[3] or 0
        exit_fine = row[4] or 0

        fine = (
            entry_fine +
            exit_fine
        )

        total_fine += fine
        total_people += 1

        text += (
            f"{number}️⃣ {name}\n"
            f"🟢 ورود: "
            f"{entry_time or 'ثبت نشده'}\n"
            f"🔵 خروج: "
            f"{exit_time or 'ثبت نشده'}\n"
            f"💰 جریمه: "
            f"{fine} افغانی\n\n"
        )

    text += (
        "━━━━━━━━━━━━\n"
        f"👥 تعداد ثبت‌شده: {total_people}\n"
        f"💰 مجموع جریمه: {total_fine} افغانی"
    )

    await update.message.reply_text(text)


# ==========================================
# /monthly
# ==========================================

async def monthly_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی ندارید."
        )

        return

    now = datetime.now()

    year = now.year
    month = now.month

    users = get_all_users()

    if not users:

        await update.message.reply_text(
            "👥 هیچ کاربری ثبت نشده است."
        )

        return

    text = (
        f"📅 گزارش ماهانه حضور و غیاب\n\n"
        f"📆 ماه: {year}-{month:02d}\n\n"
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
            GROUP_ID,
            year,
            month
        )

        days = report[0] or 0
        late_entries = report[1] or 0
        early_exits = report[2] or 0
        entry_fines = report[3] or 0
        exit_fines = report[4] or 0

        total_fine = (
            entry_fines +
            exit_fines
        )

        total_fine_all += total_fine

        text += (
            f"{number}️⃣ {name}\n"
            f"📆 روزهای ثبت‌شده: {days}\n"
            f"🟡 ورودهای دیر: {late_entries}\n"
            f"🔴 خروج‌های زود: {early_exits}\n"
            f"💰 جریمه ورود: "
            f"{entry_fines} افغانی\n"
            f"💰 جریمه خروج: "
            f"{exit_fines} افغانی\n"
            f"💵 مجموع: "
            f"{total_fine} افغانی\n\n"
        )

    text += (
        "━━━━━━━━━━━━\n"
        f"💰 مجموع جریمه همه کاربران: "
        f"{total_fine_all} افغانی"
    )

    await update.message.reply_text(text)


# ==========================================
# اجرای ربات
# ==========================================

async def main():

    # ساخت جدول‌ها
    create_tables()

    # ساخت Application
    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ==========================================
    # Commands
    # ==========================================

    app.add_handler(
        CommandHandler(
            "start",
            start
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

    # ==========================================
    # دکمه‌های پنل مدیریت
    # ==========================================

    app.add_handler(
        CallbackQueryHandler(
            admin_callback
        )
    )

    # ==========================================
    # پیام‌های متنی مدیر
    # برای تنظیم ساعت و جریمه
    # ==========================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_setting_input
        )
    )

    # ==========================================
    # حضور و غیاب
    # ==========================================

    app.add_handler(
        MessageHandler(
            filters.ALL,
            attendance_handler
        )
    )

    # ==========================================
    # اجرای ربات
    # ==========================================

    print("Attendance Bot Started...")

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


# ==========================================
# اجرای اصلی
# ==========================================

if __name__ == "__main__":

    asyncio.run(main())