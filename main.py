import hashlib
import time
import requests
import json
import os
import datetime
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from flask import Flask

import threading

app = Flask(__name__)

@app.route("/")

def home():

    return "Bot đang chạy!"

def run_web():

    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web).start()
keys = {}
allowed_users = []
vip_users = []
balances = {}
missions_completed = set()
daily_mission_count = {}
DAILY_LIMIT = 10
#gioi han nv của ngay
admin_id = 7816353760
#admin_id = *1234
#thay = id tele của banh 
MONEY_FILE = 'money.json'

def load_balances():
    global balances
    if os.path.exists(MONEY_FILE):
        with open(MONEY_FILE, 'r') as f:
            balances = json.load(f)

def save_balances():
    with open(MONEY_FILE, 'w') as f:
        json.dump(balances, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Nhiệm vụ", callback_data='nhiemvu')],
        [InlineKeyboardButton("Nhập mã", callback_data='nhap_ma')],
        [InlineKeyboardButton("Thông tin", callback_data='thong_tin')],
        [InlineKeyboardButton("Rút tiền", callback_data='rut_tien')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chào mừng bạn đến với bot! Nhấn vào nút bên dưới để bắt đầu:", reply_markup=reply_markup)

async def rut_tien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    balance = balances.get(str(user_id), 0)

    if balance < 20000:
        await query.message.reply_text("Số dư của bạn phải lớn hơn 20,000 VND để rút tiền.")
    else:
        await query.message.reply_text("Vui lòng nhập thông tin rút tiền theo cú pháp: /rut <số điện thoại> <mã ngân hàng> <số tiền>")

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    balance = balances.get(str(user_id), 0)

    if balance < 20000:
        await update.message.reply_text("Số dư của bạn phải lớn hơn 20,000 VND để rút tiền.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("Vui lòng nhập đúng cú pháp: /rut <số điện thoại> <mã ngân hàng> <số tiền>")
        return

    phone_number = context.args[0]
    bank_code = context.args[1]
    amount = int(context.args[2])

    if amount > balance:
        await update.message.reply_text("Số tiền rút vượt quá số dư hiện có.")
        return
    balances[str(user_id)] -= amount
    save_balances()
    withdrawal_request = f"Yêu cầu rút tiền:\nID: {user_id}\nSố điện thoại: {phone_number}\nNgân hàng: {bank_code}\nSố tiền: {amount} VND"
    await context.bot.send_message(chat_id=admin_id, text=withdrawal_request)
    await update.message.reply_text("Yêu cầu rút tiền của bạn đã được gửi đi.")

async def nhiemvu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    today = datetime.now().date()

    if str(user_id) not in daily_mission_count:
        daily_mission_count[str(user_id)] = {'count': 0, 'date': today}
    elif daily_mission_count[str(user_id)]['date'] != today:
        daily_mission_count[str(user_id)] = {'count': 0, 'date': today}

    if daily_mission_count[str(user_id)]['count'] >= DAILY_LIMIT:
        await query.message.reply_text("Bạn đã đạt giới hạn 10 nhiệm vụ hôm nay. Vui lòng quay lại vào ngày mai.")
        return

    if str(user_id) not in missions_completed:
        await query.answer()
        string = f'GL-{user_id}+{int(time.time())}'
        key = hashlib.md5(string.encode()).hexdigest()
        keys[str(user_id)] = key  

        try:
            response = requests.get(f'https://link4m.co/api-shorten/v2?api=nhapapi&url=url')
            #nhap api them token link4m ,url thêm url web key của bạn vào
            response_json = response.json()
            url_key = response_json.get('shortenedUrl', "Lấy Key Lỗi Vui Lòng Sử Dụng Lại Lệnh /getkey")
            keyboard = [[InlineKeyboardButton("Nhấn vào đây để thực hiện nhiệm vụ", url=url_key)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(f"Link của bạn: {url_key}\nNhấn vào nút bên dưới để thực hiện nhiệm vụ:", reply_markup=reply_markup)
            daily_mission_count[str(user_id)]['count'] += 1
        except Exception as e:
            await query.message.reply_text(f"Lỗi: {str(e)}")
    else:
        missions_completed.remove(str(user_id))
        await query.message.reply_text("Bạn có thể bắt đầu nhiệm vụ mới!")

async def enter_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Vui lòng nhập đúng key.")
        return

    user_id = update.message.from_user.id
    entered_key = context.args[0]
    expected_key = keys.get(str(user_id))

    if str(user_id) in missions_completed:
        await update.message.reply_text("Bạn đã nhập mã trước đó và không thể nhập lại.")
        return

    if entered_key == expected_key or str(user_id) in vip_users:
        allowed_users.append(user_id)
        balances[str(user_id)] = balances.get(str(user_id), 0) + 100
        save_balances()
        missions_completed.add(str(user_id))
        await update.message.reply_text("Bạn đã nhập mã thành công và được thưởng 100đ.")
    else:
        await update.message.reply_text("Key không hợp lệ! Vui lòng thử lại.")

async def thong_tin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username
    balance = balances.get(str(user_id), 0)
    await query.message.reply_text(f"Thông tin của bạn:\nID: {user_id}\nUsername: {username}\nSố dư: {balance} VND")

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'nhap_ma':
        await query.message.reply_text("Vui lòng nhập mã của bạn theo cú pháp: /nhap_ma <mã>")
    elif query.data == 'thong_tin':
        await thong_tin(update, context)
    elif query.data == 'rut_tien':
        await rut_tien(update, context)

def main():
    load_balances()  
    application = ApplicationBuilder().token('thay=token_cuaban').build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(nhiemvu, pattern='nhiemvu'))
    application.add_handler(CallbackQueryHandler(handle_button_click, pattern='nhap_ma|thong_tin|rut_tien'))
    application.add_handler(CommandHandler("nhap_ma", enter_key))
    application.add_handler(CommandHandler("rut", process_withdrawal))
    application.run_polling()
    save_balances()  

if __name__ == '__main__':
    main()
