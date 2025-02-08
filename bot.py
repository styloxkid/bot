import telebot
import sqlite3
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Bot token
TOKEN = "7913420822:AAFWiWNIE0MVVf0-TvRN9r0EeBjd_ySqgFU"  # Replace with your actual token
bot = telebot.TeleBot(TOKEN)

# Group IDs
GROUP_A_ID = -4630311831  # Replace with Group A ID
GROUP_B_ID = -4624082798  # Replace with Group B ID

# --- SQLite Database Setup ---
db = sqlite3.connect("database.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screenshot_url TEXT NOT NULL,
    sender_id INTEGER NOT NULL,
    status TEXT DEFAULT 'Pending',
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()


# --- Database Functions ---
def add_payment(screenshot_url, sender_id):
    cursor.execute("""
    INSERT INTO payments (screenshot_url, sender_id)
    VALUES (?, ?)
    """, (screenshot_url, sender_id))
    db.commit()
    return cursor.lastrowid


def update_status(payment_id, new_status):
    cursor.execute("""
    UPDATE payments
    SET status = ?, timestamp = ?
    WHERE id = ?
    """, (new_status, datetime.now(), payment_id))
    db.commit()


def get_payment_status(payment_id):
    cursor.execute("""
    SELECT id, status, timestamp
    FROM payments
    WHERE id = ?
    """, (payment_id,))
    return cursor.fetchone()


# --- Bot Handlers ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if message.chat.id == GROUP_A_ID:
        file_info = bot.get_file(message.photo[-1].file_id)
        screenshot_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        unique_id = add_payment(screenshot_url, message.from_user.id)
        formatted_id = f"#{unique_id:05}"

        # Forward the image to Group B with Inline Buttons
        markup_b = InlineKeyboardMarkup()
        markup_b.add(
            InlineKeyboardButton(f"Confirm {formatted_id}", callback_data=f"confirm_{unique_id}"),
            InlineKeyboardButton(f"Reject {formatted_id}", callback_data=f"reject_{unique_id}")
        )
        bot.send_photo(
            GROUP_B_ID,
            photo=message.photo[-1].file_id,
            caption=f"New Payment Received!\nUnique ID: {formatted_id}",
            reply_markup=markup_b
        )

        # Send confirmation message with "Check Status" button in Group A
        markup_a = InlineKeyboardMarkup()
        markup_a.add(InlineKeyboardButton("Check Status", callback_data=f"status_{unique_id}"))
        bot.reply_to(message, f"Your payment has been forwarded with ID: {formatted_id}.", reply_markup=markup_a)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("reject_"))
def handle_inline_buttons_group_b(call):
    try:
        unique_id = int(call.data.split("_")[1])
        if "confirm" in call.data:
            update_status(unique_id, "Confirmed")
            bot.send_message(GROUP_A_ID, f"Payment #{unique_id:05} has been CONFIRMED!")
        elif "reject" in call.data:
            update_status(unique_id, "Rejected")
            bot.send_message(GROUP_A_ID, f"Payment #{unique_id:05} has been REJECTED!")
        bot.answer_callback_query(call.id, "Action completed successfully.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
def handle_check_status_button(call):
    try:
        unique_id = int(call.data.split("_")[1])
        payment = get_payment_status(unique_id)
        if payment:
            bot.answer_callback_query(
                call.id,
                f"Payment #{payment[0]:05}: {payment[1]} (Last Updated: {payment[2]})",
                show_alert=True
            )
        else:
            bot.answer_callback_query(call.id, "Invalid ID. Please check and try again.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)


# --- Start the Bot ---
bot.polling()
