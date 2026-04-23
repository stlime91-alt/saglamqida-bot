# -*- coding: utf-8 -*-
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ─────────────────────────────────────────
#  AYARLAR — işə salmadan əvvəl doldurun
# ─────────────────────────────────────────
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID   = 84994299

CHANNEL_BASIC   = "https://t.me/+0Nh0N4MbKrswMGRi"   # 1 ay, 3 ay
CHANNEL_PREMIUM = "https://t.me/+0ZfO-9FlrMcxYTIy"   # 6 ay, 1 il

PAYMENT_DETAILS = (
    "💳 Ödəniş rekvizitləri:\n"
    "Kart: 4169 7388 5948 0232\n"
    "Alıcı: Ad Soyad\n\n"
    "Ödənişdən sonra skrinşotu bura göndərin — "
    "bir neçə saat ərzində kanala girişi açacağam 🙏"
)

# ─────────────────────────────────────────
#  VİDEO FAYLLAR
# ─────────────────────────────────────────
LESSONS = {
    "protein": {
        "title":   "Zülal norması",
        "file_id": "BAACAgIAAxkBAAMDaeiyIblWBo0P4mddiDzfhPTkqxUAAuicAAIYVEFLgM-zu29fhl47BA",
        "caption": "🥚 *Zülal norması*\n\nDərsi izləyin, sualınız olsa, buradayam 😊",
        "emoji":   "🥚",
    },
    "oils": {
        "title":   "Yağlar reytinqi",
        "file_id": "BAACAgIAAxkBAAMFaeiyrZJ8atjDFDMGjdJQUEtnQSIAAuqcAAIYVEFLz-PeK426BC87BA",
        "caption": "🫒 *Yağlar reytinqi*\n\nDərsi izləyin, sualınız olsa, buradayam 😊",
        "emoji":   "🫒",
    },
    "recipe": {
        "title":   "Resept",
        "file_id": "BAACAgIAAxkBAAMHaeiy-GZ6Hc-l9aHR-Jukmtnr_P0AAuycAAIYVEFL5gtlRbyhyJs7BA",
        "caption": "🥗 *Resept*\n\nDərsi izləyin, sualınız olsa, buradayam 😊",
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

# ожидающие подтверждения оплаты {user_id: pkg_key}
pending_payment: dict[int, str] = {}


# ════════════════════════════════════════
#  /start — salamlama + dərs seçimi
# ════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    data = await state.get_data()

    # если урок уже был выбран — кнопки недоступны
    if data.get("lesson_chosen"):
        await msg.answer(
            "Salam! 👋 Artıq dərsinizi seçmisiniz.\n\n"
            "Sualınız varsa, buradayam 😊"
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
        "Mən nütrisioloqam və sizin üçün ödənişsiz qidalanma dərsləri hazırlamışam. "
        "İndi hansı dərsi izləmək istədiyinizi seçin:",
        reply_markup=kb.as_markup()
    )


# ════════════════════════════════════════
#  file_id almaq — video faylı bota yönləndir
# ════════════════════════════════════════
@dp.message(F.video)
async def get_file_id(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            f"✅ *Video faylının file\\_id-si:*\n\n`{msg.video.file_id}`\n\n"
            f"Kopyala və bot.py-a yapışdır",
            parse_mode="Markdown"
        )


# ════════════════════════════════════════
#  Dərsin göndərilməsi (yalnız bir dəfə)
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("lesson_"))
async def send_lesson(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # если урок уже выбран — игнорируем
    if data.get("lesson_chosen"):
        await call.answer("Artıq dərsinizi seçmisiniz!", show_alert=True)
        return

    key = call.data.replace("lesson_", "")
    lesson = LESSONS.get(key)
    if not lesson:
        return

    # помечаем что урок выбран — остальные заблокированы
    await state.update_data(lesson_chosen=True, lesson_key=key)

    await call.message.edit_reply_markup()  # убираем кнопки
    await call.message.answer_video(
        video=lesson["file_id"],
        caption=lesson["caption"],
        parse_mode="Markdown"
    )
    await call.answer()

    uid = call.from_user.id
    if uid in pending_followup and not pending_followup[uid].done():
        pending_followup[uid].cancel()

    task = asyncio.create_task(_followup_timer(uid))
    pending_followup[uid] = task


async def _followup_timer(user_id: int):
    await asyncio.sleep(10 * 60)  # 10 dəqiqə

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Bəli, bütün dərsləri istəyirəm!", callback_data="interest_yes")
    kb.button(text="❌ Xeyr, sağ ol",                    callback_data="interest_no")
    kb.adjust(1)

    await bot.send_message(
        user_id,
        "Salam! 👋\n\n"
        "Ümid edirəm ki, dərs faydalı oldu 🙌\n\n"
        "Material xoşunuza gəldimi və "
        "*bütün dərslərə* giriş əldə etmək istərdinizmi?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


# ════════════════════════════════════════
#  Cavab — XEYR
# ════════════════════════════════════════
@dp.callback_query(F.data == "interest_no")
async def interest_no(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Yaxşı, narahat etmirəm 😊\n\n"
        "Sənə sağlamlıq və enerji arzulayıram! "
        "Fikrin dəyişsə və ya sualın olsa — həmişə buradayam. Uğurlar! 🌿"
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
        "Əla! 🎉 Sənin üçün hazırladıqlarım:\n\n"
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
        f"Seçdin: *{pkg['duration']}* — *{pkg['price']} AZN*{extra_text}\n\n"
        f"{PAYMENT_DETAILS}",
        parse_mode="Markdown"
    )

    # сохраняем заявку в ожидании подтверждения
    pending_payment[call.from_user.id] = key

    user = call.from_user
    name = user.full_name
    username = f"@{user.username}" if user.username else "username yoxdur"

    # уведомление тебе с кнопкой подтверждения
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
        f"Ödənişi aldıqdan sonra təsdiqlə:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
    await call.answer()


# ════════════════════════════════════════
#  Admin: təsdiq düyməsi
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    parts = call.data.split("_")
    user_id = int(parts[1])
    pkg_key = parts[2]
    pkg = PACKAGES.get(pkg_key)

    await call.message.edit_reply_markup()

    channel = CHANNEL_PREMIUM if pkg["premium"] else CHANNEL_BASIC
    channel_name = "Premium kanal" if pkg["premium"] else "Əsas kanal"

    # отправляем клиенту ссылку на канал
    kb = InlineKeyboardBuilder()
    kb.button(text=f"📺 {channel_name}ə keçin", url=channel)
    if pkg["premium"]:
        kb.button(text="📺 Əsas kanala da keçin", url=CHANNEL_BASIC)
    kb.adjust(1)

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
    await call.answer()

    # убираем из ожидания
    pending_payment.pop(user_id, None)


# ════════════════════════════════════════
#  Admin: ləğv düyməsi
# ════════════════════════════════════════
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    user_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup()

    await bot.send_message(
        user_id,
        "Təəssüf ki, ödənişiniz təsdiqlənmədi. "
        "Probleminiz varsa bizimlə əlaqə saxlayın."
    )
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
