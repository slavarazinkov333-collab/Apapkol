import telebot
import json
import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

PROMOS = {
    "slavabro": {"type": "bonus", "value": 10, "desc": "+10 G бонус"},
    "standoff": {"type": "bonus", "value": 50, "desc": "+50 G бонус"},
    "flayy": {"type": "gift", "value": 500, "desc": "+500 G"},
    "admin": {"type": "gift", "value": 5000, "desc": "+5000 G"}
}

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = str(message.from_user.id)
    db = load_db()
    if user_id not in db:
        db[user_id] = {"gold": 0, "promo_used": [], "bonus": 0}
        save_db(db)
    bot.send_message(message.chat.id, "👋 Привет! StandFliutApap!\n\n/balance — баланс\n/topup — пополнить\n/promo — промокод")

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    user_id = str(message.from_user.id)
    db = load_db()
    if user_id not in db:
        db[user_id] = {"gold": 0, "promo_used": [], "bonus": 0}
        save_db(db)
    bot.send_message(message.chat.id, f"💰 Баланс: {db[user_id]['gold']} G")

@bot.message_handler(commands=['topup'])
def cmd_topup(message):
    bot.send_invoice(
        chat_id=message.chat.id,
        title="Пополнение",
        description="100 G за 50 звёзд",
        invoice_payload="topup_100",
        provider_token="",
        currency="XTR",
        prices=[telebot.types.LabeledPrice(label="100 G", amount=50)]
    )

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp(message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get('action') == 'topup':
            amount = int(data.get('amount', 0))
            if amount < 40:
                bot.send_message(message.chat.id, "❌ Минимум 40 ₽")
                return
            stars = amount // 2
            bot.send_invoice(
                chat_id=message.chat.id,
                title="Пополнение",
                description=f"{amount} G за {stars} звёзд",
                invoice_payload=f"topup_{amount}",
                provider_token="",
                currency="XTR",
                prices=[telebot.types.LabeledPrice(label=f"{amount} G", amount=stars)]
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.message_handler(commands=['promo'])
def cmd_promo(message):
    msg = bot.send_message(message.chat.id, "🎁 Введи промокод:")
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    user_id = str(message.from_user.id)
    code = message.text.strip().lower()
    db = load_db()
    if user_id not in db:
        db[user_id] = {"gold": 0, "promo_used": [], "bonus": 0}
    if code not in PROMOS:
        bot.send_message(message.chat.id, "❌ Неверный промокод")
        return
    if code in db[user_id]["promo_used"]:
        bot.send_message(message.chat.id, "❌ Уже использован")
        return
    promo = PROMOS[code]
    db[user_id]["promo_used"].append(code)
    if promo["type"] == "gift":
        db[user_id]["gold"] += promo["value"]
        bot.send_message(message.chat.id, f"🎁 {promo['desc']}!\n💰 Баланс: {db[user_id]['gold']} G")
    else:
        db[user_id]["bonus"] = promo["value"]
        bot.send_message(message.chat.id, f"🎁 {promo['desc']}!\nБонус при пополнении")
    save_db(db)

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = str(message.from_user.id)
    db = load_db()
    if user_id not in db:
        db[user_id] = {"gold": 0, "promo_used": [], "bonus": 0}
    payload = message.successful_payment.invoice_payload
    try:
        amount_rub = int(payload.split("_")[1])
    except:
        amount_rub = 100
    bonus = db[user_id].get("bonus", 0)
    total = amount_rub + bonus
    db[user_id]["gold"] += total
    db[user_id]["bonus"] = 0
    save_db(db)
    bot.send_message(message.chat.id, f"✅ Оплачено! +{total} G")

print("Бот запущен...")
bot.polling(none_stop=True)
