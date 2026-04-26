# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ─────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = 84994299

CHANNEL_BASIC   = "https://t.me/+0Nh0N4MbKrswMGRi"
CHANNEL_PREMIUM = "https://t.me/+0ZfO-9FlrMcxYTIy"

PAYMENT_DETAILS = (
    "💳 Ödəniş rekvizitləri:\n"
    "Kart: 4169 7388 5948 0232\n\n"
    "Ödənişdən sonra skrinşotu bura göndərin — "
    "bir neçə saat ərzində kanala girişinizi açacağıq 🙏"
)

LESSONS = {
    "protein": {
        "title":   "Zülal norması",
        "file_id": "BAACAgIAAxkBAAMDaeiyIblWBo0P4mddiDzfhPTkqxUAAuicAAIYVEFLgM-zu29fhl47BA",
        "caption": "🥚 *Zülal norması*\n\nDərsi izləyin, sualınız olsa — buradayıq 😊",
        "emoji":   "🥚",
    },
    "oils": {
        "title":   "Yağlar reytinqi",
        "file_id": "BAACAgIAAxkBAAMFaeiyrZJ8atjDFDMGjdJQUEtnQSIAAuqcAAIYVEFLz-PeK426BC87BA",
        "caption": "🫒 *Yağlar reytinqi*\n\nDərsi izləyin, sualınız olsa — buradayıq 😊",
        "emoji":   "🫒",
    },
    "recipe": {
        "title":   "Resept",
        "file_id": "BAACAgIAAxkBAAMHaeiy-GZ6Hc-l9aHR-Jukmtnr_P0AAuycAAIYVEFL5gtlRbyhyJs7BA",
        "caption": "🥗 *Resept*\n\nDərsi izləyin, sualınız olsa — buradayıq 😊",
        "emoji":   "🥗",
    },
}

PACKAGES = {
    "pkg_10d": {"name": "Mini təlim", "duration": "Mini təlim (10 gün)", "price": 10,  "premium": False},
    "pkg_3m":  {"name": "Tam təlim",  "duration": "Tam təlim (3 ay)",    "price": 29,  "premium": False},
    "pkg_6m":  {"name": "VİP təlim",  "duration": "VİP təlim (6 ay)",    "price": 100, "premium": True},
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

pending_followup: dict[int, asyncio.Task] = {}
pending_payment:  dict[int, str] = {}


# ════════════════════════════════════════
#  WEB SERVER — сайт отправляет сюда
# ════════════════════════════════════════
async def handle_web_order(request: web.Request):
    try:
        data = await request.post()
        name      = data.get('name', 'Naməlum')
        phone     = data.get('phone', '-')
        telegram  = data.get('telegram', '-')
        package   = data.get('package', '-')
        price     = data.get('price', '-')
        lesson    = data.get('lesson', '-')
        screenshot = data.get('screenshot')

        text = (
            f"🌐 *Saytdan yeni sifariş!*\n\n"
            f"👤 Ad: {name}\n"
            f"📱 Telefon: {phone}\n"
            f"💬 Telegram: {telegram}\n"
            f"📚 Dərs: {lesson}\n"
            f"📦 Paket: {package} — {price}\n"
        )

        if screenshot and hasattr(screenshot, 'file'):
            photo_bytes = screenshot.file.read()
            photo = BufferedInputFile(photo_bytes, filename="screenshot.jpg")

            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"webconfirm_{name}_{package}")
            kb.button(text="❌ Ləğv et",           callback_data=f"webcancel_0")
            kb.adjust(1)

            await bot.send_photo(
                ADMIN_ID,
                photo=photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=kb.as_markup()
            )
        else:
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"webconfirm_{name}_{package}")
            kb.button(text="❌ Ləğv et",           callback_data=f"webcancel_0")
            kb.adjust(1)

            await bot.send_message(
                ADMIN_ID,
                text,
                parse_mode="Markdown",
                reply_markup=kb.as_markup()
            )

        return web.Response(text="OK", status=200, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        logging.error(f"Web order error: {e}")
        return web.Response(text=str(e), status=500)


async def handle_options(request: web.Request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


# ════════════════════════════════════════
#  /start
# ════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("lesson_chosen"):
        await msg.answer("Salam! 👋 Artıq dərsinizi seçmisiniz.\n\nSualınız varsa — buradayıq 😊")
        return

    kb = InlineKeyboardBuilder()
    for key, lesson in LESSONS.items():
        kb.button(text=f"{lesson['emoji']} {lesson['title']}", callback_data=f"lesson_{key}")
    kb.adjust(1)

    await msg.answer(
        "Salam! 👋 Sizi burada görmək çox xoşdur!\n\n"
        "Mən nütrisioloqam və Sizin üçün pulsuz qidalanma dərsləri hazırlamışam. "
        "İndi hansı dərsi izləmək istədiyinizi seçin:",
        reply_markup=kb.as_markup()
    )


@dp.message(F.video)
async def handle_video(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(f"✅ `{msg.video.file_id}`", parse_mode="Markdown")


@dp.message(F.photo)
async def handle_screenshot(msg: Message):
    user = msg.from_user
    if user.id == ADMIN_ID:
        return
    logging.info(f"PHOTO from {user.id}, pending: {pending_payment}")
    name     = user.full_name
    username = f"@{user.username}" if user.username else "username yoxdur"
    pkg_key  = pending_payment.get(user.id)
    pkg_info = f"{PACKAGES[pkg_key]['duration']} — {PACKAGES[pkg_key]['price']} AZN" if pkg_key else "naməlum paket"

    kb = InlineKeyboardBuilder()
    if pkg_key:
        kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"confirm_{user.id}_{pkg_key}")
        kb.button(text="❌ Ləğv et",           callback_data=f"cancel_{user.id}")
        kb.adjust(1)

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=msg.photo[-1].file_id,
            caption=(
                f"🧾 *Ödəniş skrinşotu gəldi!*\n\n"
                f"👤 {name} ({username})\n"
                f"🆔 ID: `{user.id}`\n"
                f"📦 Paket: {pkg_info}"
            ),
            parse_mode="Markdown",
            reply_markup=kb.as_markup() if pkg_key else None
        )
    except Exception as e:
        logging.error(f"Screenshot forward error: {e}")

    await msg.answer("✅ Skrinşotunuz qəbul edildi! Yoxlandıqdan sonra sizə bildiriş göndərəcəyik 🙏")


@dp.callback_query(F.data.startswith("lesson_"))
async def send_lesson(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("lesson_chosen"):
        await call.answer("Artıq dərsinizi seçmisiniz!", show_alert=True)
        return

    key    = call.data.replace("lesson_", "")
    lesson = LESSONS.get(key)
    if not lesson:
        return

    await state.update_data(lesson_chosen=True, lesson_key=key)
    await call.message.edit_reply_markup()

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Dərsə baxdım", callback_data="watched")
    kb.adjust(1)

    await call.message.answer_video(
        video=lesson["file_id"],
        caption=lesson["caption"],
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()

    uid = call.from_user.id
    if uid in pending_followup and not pending_followup[uid].done():
        pending_followup[uid].cancel()
    pending_followup[uid] = asyncio.create_task(_followup_timer(uid))


@dp.callback_query(F.data == "watched")
async def lesson_watched(call: CallbackQuery):
    await call.message.edit_reply_markup()
    uid = call.from_user.id
    if uid in pending_followup and not pending_followup[uid].done():
        pending_followup[uid].cancel()

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Bəli, bütün dərsləri istəyirəm!", callback_data="interest_yes")
    kb.button(text="❌ Xeyr, sağ olun",                  callback_data="interest_no")
    kb.adjust(1)

    await call.message.answer(
        "Əla! 🙌\n\nDərs Sizin üçün faydalı oldumu? *Bütün dərslərə* giriş əldə etmək istərdinizmi?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


async def _followup_timer(user_id: int):
    await asyncio.sleep(10 * 60)
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Bəli, bütün dərsləri istəyirəm!", callback_data="interest_yes")
    kb.button(text="❌ Xeyr, sağ olun",                  callback_data="interest_no")
    kb.adjust(1)
    await bot.send_message(
        user_id,
        "Salam! 👋\n\nÜmid edirik ki, dərs Sizin üçün faydalı oldu 🙌\n\n"
        "Deyin görək, material xoşunuza gəldimi və *bütün dərslərə* giriş əldə etmək istərdinizmi?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "interest_no")
async def interest_no(call: CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Yaxşı, narahat etmirik 😊\n\nSizə sağlamlıq və enerji arzulayırıq! "
        "Fikriniz dəyişsə və ya sualınız olsa — həmişə buradayıq. Uğurlar! 🌿"
    )
    await call.answer()


@dp.callback_query(F.data == "interest_yes")
async def interest_yes(call: CallbackQuery):
    await call.message.edit_reply_markup()
    kb = InlineKeyboardBuilder()
    for key, pkg in PACKAGES.items():
        extra = " 🎁" if pkg["premium"] else ""
        star  = "⭐️ " if pkg["premium"] else ""
        kb.button(text=f"{star}{pkg['duration']} — {pkg['price']} AZN{extra}", callback_data=f"buy_{key}")
    kb.adjust(1)
    await call.message.answer(
        "Əla! 🎉 Sizin üçün hazırladıqlarımız:\n\n"
        "📚 *Bütün dərslərlə Telegram kanalına giriş:*\n\n"
        "▪️ *Mini təlim* (10 gün) — 10 AZN\n"
        "⭐️ *Tam təlim* (3 ay) — 29 AZN\n_+ yay kolleksiyası (5 yeni dərs) + online vərdiş cədvəli_\n\n"
        "🏆 *VİP təlim* (6 ay) — 100 AZN\n_+ 30 dəqiqəlik fərdi konsultasiya + idman/yuxu təlimlərinə 30% endirim_\n\n"
        "Uyğun variantı seçin:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def buy_package(call: CallbackQuery):
    key = call.data.replace("buy_", "")
    pkg = PACKAGES.get(key)
    if not pkg:
        return
    await call.message.edit_reply_markup()
    extra_text = "\n🎁 *Yay və payızda çıxacaq bütün yeni dərslər daxildir!*" if pkg["premium"] else ""
    await call.message.answer(
        f"Əla seçim! 🙌\n\nSeçdiniz: *{pkg['duration']}* — *{pkg['price']} AZN*{extra_text}\n\n{PAYMENT_DETAILS}",
        parse_mode="Markdown"
    )
    pending_payment[call.from_user.id] = key
    user = call.from_user
    username = f"@{user.username}" if user.username else "username yoxdur"
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"confirm_{user.id}_{key}")
    kb.button(text="❌ Ləğv et",           callback_data=f"cancel_{user.id}")
    kb.adjust(1)
    await bot.send_message(
        ADMIN_ID,
        f"💰 *Yeni sifariş!*\n\n👤 {user.full_name} ({username})\n🆔 ID: `{user.id}`\n📦 Paket: {pkg['duration']} — {pkg['price']} AZN\n\nSkrinşot gözləyin:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    _, user_id_str, *pkg_parts = call.data.split("_")
    user_id = int(user_id_str)
    pkg_key = "_".join(pkg_parts)
    pkg     = PACKAGES.get(pkg_key)
    if not pkg:
        await call.message.answer(f"⚠️ Paket tapılmadı: {pkg_key}")
        await call.answer()
        return
    await call.message.edit_reply_markup()
    channel = CHANNEL_PREMIUM if pkg["premium"] else CHANNEL_BASIC
    kb = InlineKeyboardBuilder()
    kb.button(text="📺 Kanala daxil ol", url=channel)
    if pkg["premium"]:
        kb.button(text="📺 Əsas kanala da daxil ol", url=CHANNEL_BASIC)
    kb.adjust(1)
    try:
        sent = await bot.send_message(
            user_id,
            "🎉 Ödənişiniz təsdiqləndi!\n\nTəşəkkür edirik! Aşağıdakı düyməyə basaraq kanala qoşulun:",
            reply_markup=kb.as_markup()
        )
        await call.message.answer(f"✅ Təsdiq göndərildi. ID: `{user_id}`", parse_mode="Markdown")
        asyncio.create_task(_remove_buttons(user_id, sent.message_id))
    except Exception as e:
        await call.message.answer(f"⚠️ Xəta: {e}")
    pending_payment.pop(user_id, None)
    await call.answer()


async def _remove_buttons(chat_id: int, message_id: int):
    await asyncio.sleep(30)
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    except Exception:
        pass


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    user_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup()
    try:
        await bot.send_message(user_id, "Təəssüf ki, ödənişiniz təsdiqlənmədi. Probleminiz varsa bizimlə əlaqə saxlayın.")
    except Exception as e:
        await call.message.answer(f"⚠️ Xəta: {e}")
    await call.message.answer(f"❌ Ləğv edildi. ID: `{user_id}`", parse_mode="Markdown")
    pending_payment.pop(user_id, None)
    await call.answer()


# ════════════════════════════════════════
#  İşə salma — bot + web server birlikdə
# ════════════════════════════════════════
async def main():
    app = web.Application()
    app.router.add_post('/order', handle_web_order)
    app.router.add_route('OPTIONS', '/order', handle_options)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("Web server started on port 8080")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
