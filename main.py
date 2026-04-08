import telebot
from telebot import types
import time
import os
import threading
from datetime import datetime, timedelta

# --- CONFIG ---
API_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1003746627836
ADMIN_KEY = "Esh20imayar26"

bot = telebot.TeleBot(API_TOKEN)

# --- DATA ---
current_timer = 60
user_scores = {}
user_wrong_streak = {}
poll_correct_answers = {}
stored_questions = []
admin_sessions = {}

# --- AUTH ---
def is_login_valid(chat_id):
    if chat_id not in admin_sessions:
        return False
    if datetime.now() > admin_sessions[chat_id] + timedelta(minutes=20):
        del admin_sessions[chat_id]
        return False
    return True

# --- MENU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📝 Make Question', '🚀 Start Quiz')
    markup.add('🏆 Get Leaderboard', '⚙️ Set Timer')
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 Admin Panel Active.", reply_markup=main_menu())

# --- ADMIN LOGIN ---
@bot.message_handler(commands=['admin'])
def admin_login(message):
    msg = bot.send_message(message.chat.id, "🔑 Enter Admin Key:")
    bot.register_next_step_handler(msg, verify_admin)

def verify_admin(message):
    if message.text == ADMIN_KEY:
        admin_sessions[message.chat.id] = datetime.now()
        bot.send_message(message.chat.id, "✅ Logged in (20 min)")
    else:
        bot.send_message(message.chat.id, "❌ Wrong key")

# --- TIMER ---
@bot.message_handler(func=lambda m: m.text == '⚙️ Set Timer')
def set_timer(message):
    if not is_login_valid(message.chat.id):
        return bot.send_message(message.chat.id, "🔐 Use /admin")

    msg = bot.send_message(message.chat.id, "Enter seconds (10-600):")
    bot.register_next_step_handler(msg, save_timer)

def save_timer(message):
    global current_timer
    try:
        t = int(message.text)
        if 10 <= t <= 600:
            current_timer = t
            bot.send_message(message.chat.id, f"✅ Timer set to {t}s")
        else:
            bot.send_message(message.chat.id, "❌ Must be 10-600")
    except:
        bot.send_message(message.chat.id, "❌ Invalid input")

# --- QUESTIONS ---
@bot.message_handler(func=lambda m: m.text == '📝 Make Question')
def make_q(message):
    if not is_login_valid(message.chat.id):
        return bot.send_message(message.chat.id, "🔐 Use /admin")

    msg = bot.send_message(message.chat.id, "Paste questions:")
    bot.register_next_step_handler(msg, save_q)

def save_q(message):
    global stored_questions
    blocks = [b.strip() for b in message.text.split('\n\n') if "Answer:" in b]

    if blocks:
        stored_questions = blocks
        bot.send_message(message.chat.id, f"✅ {len(blocks)} saved")
    else:
        bot.send_message(message.chat.id, "❌ Format error")

# --- QUIZ THREAD ---
def run_quiz(message):
    global stored_questions

    bot.send_message(message.chat.id, f"🚀 Sending {len(stored_questions)} questions")

    for i, block in enumerate(stored_questions, 1):
        try:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) < 6:
                continue

            q = f"Q{i}: {lines[0]}"
            options = [lines[1][3:], lines[2][3:], lines[3][3:], lines[4][3:]]

            ans = "A"
            for l in lines:
                if "Answer:" in l:
                    ans = l.split(":")[-1].strip().upper()

            idx = ord(ans) - ord('A')

            poll = bot.send_poll(
                chat_id=GROUP_ID,
                question=q,
                options=options,
                type='quiz',
                correct_option_id=idx,
                is_anonymous=False,
                open_period=current_timer
            )

            poll_correct_answers[poll.poll.id] = idx
            time.sleep(current_timer + 2)

        except Exception as e:
            print(e)

    stored_questions = []
    bot.send_message(message.chat.id, "🏁 Quiz Done")

# --- START QUIZ ---
@bot.message_handler(func=lambda m: m.text == '🚀 Start Quiz')
def start_quiz(message):
    if not is_login_valid(message.chat.id):
        return bot.send_message(message.chat.id, "🔐 Use /admin")

    if not stored_questions:
        return bot.send_message(message.chat.id, "⚠️ No questions")

    threading.Thread(target=run_quiz, args=(message,)).start()

# --- POLL ANSWER ---
@bot.poll_answer_handler()
def handle_poll(poll):
    if not poll.option_ids:
        return

    uid = poll.user.id
    name = poll.user.first_name
    selected = poll.option_ids[0]

    if poll.poll_id in poll_correct_answers:
        if selected == poll_correct_answers[poll.poll_id]:
            user_scores[uid] = user_scores.get(uid, {"name": name, "score": 0})
            user_scores[uid]["score"] += 1
            user_wrong_streak[uid] = 0
        else:
            user_wrong_streak[uid] = user_wrong_streak.get(uid, 0) + 1
            if user_wrong_streak[uid] >= 3:
                bot.send_message(GROUP_ID, f"💪 {name}, keep trying!")
                user_wrong_streak[uid] = 0

# --- LEADERBOARD ---
@bot.message_handler(func=lambda m: m.text == '🏆 Get Leaderboard')
def leaderboard(message):
    if not user_scores:
        return bot.send_message(message.chat.id, "No data")

    sorted_users = sorted(user_scores.values(), key=lambda x: x["score"], reverse=True)

    text = "🏆 TOP 10\n\n"
    for i, u in enumerate(sorted_users[:10], 1):
        text += f"{i}. {u['name']} - {u['score']} pts\n"

    bot.send_message(message.chat.id, text)

# --- RUN ---
print("Bot running...")

while True:
    try:
        bot.polling(none_stop=True, interval=2)
    except Exception as e:
        print(e)
        time.sleep(5)