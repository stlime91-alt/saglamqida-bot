# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ─────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = 84994299  # ← öz Telegram ID-ni yaz

CHANNEL_BASIC   = "https://t.me/+0Nh0N4MbKrswMGRi"
CHANNEL_PREMIUM = "https://t.me/+0ZfO-9FlrMcxYTIy"

PAYMENT_DETAILS = (
    "💳 Ödəniş rekvizitləri:\n"
    "Kart: 4169 7388 5948 0232\n"
    "Alıcı: Ad Soyad\n\n"
    "Ödənişdən sonra skrinşotu bura göndərin — "
    "bir neçə saat ərzində kanala girişinizi açacağıq 🙏"
)

# ─────────────────────────────────────────
#  VİDEO FAYLLAR
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
#  PAKETLƏR
# ─────────────────────────────────────────
PACKAGES = {
    "pkg_1m":  {"name": "1 ay",  "duration": "1 aylıq giriş",  "price": 10, "premium": False},
    "pkg_3m":  {"name": "3 ay",  "duration": "3 aylıq giriş",  "price": 25, "premium": False},
    "pkg_6m":  {"name": "6 ay",  "duration": "6 aylıq giriş",  "price": 45, "premium": True},
    "pkg_12m": {"name": "1 il",  "duration": "1 illik giriş",  "price": 60, "premium": True},
}

# ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

pending_followup: dict[int, asyncio.Task] = {}
pending_payment:  dict[int, str] = {}


# ════════════════════════════════════════
#  /start — salamlama + dərs seçimi
# ════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    data = await state.get_data()

    if data.get("lesson_chosen"):
        await msg.answer(
            "Salam! 👋 Artıq dərsinizi seçmisiniz.\n\n"
            "Sualınız varsa — buradayıq 😊"
        )
        return

    kb = InlineKeyboardBuilder()
    for key, lesson in LESSONS.items():
        kb.button(
            text=f"{lesson['emoji']} {lesson['title']}",
            callback_data=f"lesson_{key}"
        )
    kb.adjust(1)

    await msg.answer(
        "Salam! 👋 Sizi burada görmək çox xoşdur!\n\n"
        "Mən nütrisioloqam və Sizin üçün pulsuz qidalanma dərsləri hazırlamışam. "
        "İndi hansı dərsi izləmək istədiyinizi seçin:",
        reply_markup=kb.as_markup()
    )


# ════════════════════════════════════════
#  file_id almaq (yalnız admin üçün)
# ════════════════════════════════════════
@dp.message(F.video)
async def handle_video(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            f"✅ *Video faylının file\\_id-si:*\n\n`{msg.video.file_id}`\n\n"
            f"Kopyala və bot.py-a yapışdır",
            parse_mode="Markdown"
        )


# ════════════════════════════════════════
#  Skrinşot qəbulu — admina yönləndir
# ════════════════════════════════════════
@dp.message(F.photo)
async def handle_screenshot(msg: Message):
    user = msg.from_user
    if user.id == ADMIN_ID:
        return

    name     = user.full_name
    username = f"@{user.username}" if user.username else "username yoxdur"
    pkg_key  = pending_payment.get(user.id)
    pkg_info = f"{PACKAGES[pkg_key]['duration']} — {PACKAGES[pkg_key]['price']} AZN" if pkg_key else "naməlum paket"

    # пересылаем скриншот админу
    kb = InlineKeyboardBuilder()
    if pkg_key:
        kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"confirm_{user.id}_{pkg_key}")
        kb.button(text="❌ Ləğv et",           callback_data=f"cancel_{user.id}")
        kb.adjust(1)

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

    await msg.answer(
        "✅ Skrinşotunuz qəbul edildi! "
        "Yoxlandıqdan sonra sizə bildiriş göndərəcəyik 🙏"
    )


# ════════════════════════════════════════
#  Dərsin göndərilməsi + "Dərsə baxdım" düyməsi
# ════════════════════════════════════════
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

    # кнопка "Dərsə baxdım"
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

    task = asyncio.create_task(_followup_timer(uid))
    pending_followup[uid] = task


# ════════════════════════════════════════
#  "Dərsə baxdım" düyməsi — soru göstər
# ════════════════════════════════════════
@dp.callback_query(F.data == "watched")
async def lesson_watched(call: CallbackQuery):
    await call.message.edit_reply_markup()

    # отменяем таймер — вопрос задаём сразу
    uid = call.from_user.id
    if uid in pending_followup and not pending_followup[uid].done():
        pending_followup[uid].cancel()

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Bəli, bütün dərsləri istəyirəm!", callback_data="interest_yes")
    kb.button(text="❌ Xeyr, sağ olun",                  callback_data="interest_no")
    kb.adjust(1)

    await call.message.answer(
        "Əla! 🙌\n\n"
        "Dərs Sizin üçün faydalı oldumu? "
        "*Bütün dərslərə* giriş əldə etmək istərdinizmi?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


async def _followup_timer(user_id: int):
    await asyncio.sleep(10 * 60)  # 10 dəqiqə — əgər düyməyə basmayıbsa

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Bəli, bütün dərsləri istəyirəm!", callback_data="interest_yes")
    kb.button(text="❌ Xeyr, sağ olun",                  callback_data="interest_no")
    kb.adjust(1)

    await bot.send_message(
        user_id,
        "Salam! 👋\n\n"
        "Ümid edirik ki, dərs Sizin üçün faydalı oldu 🙌\n\n"
        "Deyin görək, material xoşunuza gəldimi və "
        "*bütün dərslərə* giriş əldə etmək istərdinizmi?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


# ════════════════════════════════════════
#  Cavab — XEYİR
# ════════════════════════════════════════
@dp.callback_query(F.data == "interest_no")
async def interest_no(call: CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Yaxşı, narahat etmirik 😊\n\n"
        "Sizə sağlamlıq və enerji arzulayırıq! "
        "Fikriniz dəyişsə və ya sualınız olsa — həmişə buradayıq. Uğurlar! 🌿"
    )
    await call.answer()


# ════════════════════════════════════════
#  Cavab — BƏLİ → paketlər
# ════════════════════════════════════════
@dp.callback_query(F.data == "interest_yes")
async def interest_yes(call: CallbackQuery):
    await call.message.edit_reply_markup()

    kb = InlineKeyboardBuilder()
    for key, pkg in PACKAGES.items():
        extra = " 🎁" if pkg["premium"] else ""
        star  = "⭐️ " if pkg["premium"] else ""
        kb.button(
            text=f"{star}{pkg['duration']} — {pkg['price']} AZN{extra}",
            callback_data=f"buy_{key}"
        )
    kb.adjust(1)

    await call.message.answer(
        "Əla! 🎉 Sizin üçün hazırladıqlarımız:\n\n"
        "📚 *Bütün dərslərlə Telegram kanalına giriş:*\n\n"
        "▪️ 1 aylıq giriş — 10 AZN\n"
        "▪️ 3 aylıq giriş — 25 AZN\n"
        "⭐️ 6 aylıq giriş — 45 AZN *(+ yay və payızda çıxacaq yeni dərslər)* 🎁\n"
        "⭐️ 1 illik giriş — 60 AZN *(+ yay və payızda çıxacaq yeni dərslər)* 🎁\n\n"
        "Uyğun variantı seçin:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


# ════════════════════════════════════════
#  Paket seçimi → rekvizitlər
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("buy_"))
async def buy_package(call: CallbackQuery):
    key = call.data.replace("buy_", "")
    pkg = PACKAGES.get(key)
    if not pkg:
        return

    await call.message.edit_reply_markup()

    extra_text = ""
    if pkg["premium"]:
        extra_text = "\n🎁 *Yay və payızda çıxacaq bütün yeni dərslər daxildir!*"

    await call.message.answer(
        f"Əla seçim! 🙌\n\n"
        f"Seçdiniz: *{pkg['duration']}* — *{pkg['price']} AZN*{extra_text}\n\n"
        f"{PAYMENT_DETAILS}",
        parse_mode="Markdown"
    )

    pending_payment[call.from_user.id] = key

    user     = call.from_user
    name     = user.full_name
    username = f"@{user.username}" if user.username else "username yoxdur"

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ödənişi təsdiqlə", callback_data=f"confirm_{user.id}_{key}")
    kb.button(text="❌ Ləğv et",           callback_data=f"cancel_{user.id}")
    kb.adjust(1)

    await bot.send_message(
        ADMIN_ID,
        f"💰 *Yeni sifariş!*\n\n"
        f"👤 {name} ({username})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 Paket: {pkg['duration']} — {pkg['price']} AZN\n\n"
        f"Skrinşot gözləyin və ya aşağıdakı düymələrdən istifadə edin:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


# ════════════════════════════════════════
#  Admin: ödənişi təsdiqlə
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(call: CallbackQuery):
    await call.message.answer(f"DEBUG: {call.from_user.id} vs {ADMIN_ID}")
    if call.from_user.id != ADMIN_ID:
        await call.message.answer("DEBUG: not admin!")
        return

    # confirm_{user_id}_{pkg_key} e.g. confirm_123456789_pkg_1m
    _, user_id_str, *pkg_parts = call.data.split("_")
    user_id = int(user_id_str)
    pkg_key = "_".join(pkg_parts)  # pkg_1m, pkg_3m, pkg_6m, pkg_12m
    pkg     = PACKAGES.get(pkg_key)
    if not pkg:
        await call.message.answer(f"⚠️ Paket tapılmadı: {pkg_key}")
        await call.answer()
        return

    await call.message.edit_reply_markup()

    channel      = CHANNEL_PREMIUM if pkg["premium"] else CHANNEL_BASIC
    channel_name = "Premium kanal" if pkg["premium"] else "Əsas kanal"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"📺 {channel_name}a daxil ol", url=channel)
    if pkg["premium"]:
        kb.button(text="📺 Əsas kanala da daxil ol", url=CHANNEL_BASIC)
    kb.adjust(1)

    try:
        await bot.send_message(
            user_id,
            "🎉 Ödənişiniz təsdiqləndi!\n\n"
            "Təşəkkür edirik! Aşağıdakı düyməyə basaraq kanala qoşulun:",
            reply_markup=kb.as_markup()
        )
        await call.message.answer(
            f"✅ Təsdiq göndərildi. İstifadəçi ID: `{user_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await call.message.answer(f"⚠️ Xəta: {e}")

    pending_payment.pop(user_id, None)
    await call.answer()


# ════════════════════════════════════════
#  Admin: ləğv et
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    user_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup()

    try:
        await bot.send_message(
            user_id,
            "Təəssüf ki, ödənişiniz təsdiqlənmədi. "
            "Probleminiz varsa bizimlə əlaqə saxlayın."
        )
    except Exception as e:
        await call.message.answer(f"⚠️ Xəta: {e}")

    await call.message.answer(f"❌ Sifariş ləğv edildi. ID: `{user_id}`", parse_mode="Markdown")
    pending_payment.pop(user_id, None)
    await call.answer()


# ════════════════════════════════════════
#  İşə salma
# ════════════════════════════════════════
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
