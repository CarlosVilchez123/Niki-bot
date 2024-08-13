import os
import telebot
import re
from dotenv import load_dotenv
from threading import Thread
import time
from requests.exceptions import ConnectionError
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_KEY = os.getenv('API_KEY')
PORT = int(os.getenv('PORT', 5000))

if API_KEY is None:
    raise ValueError("No se encontró la variable de entorno 'API_KEY'.")

bot = telebot.TeleBot(API_KEY)

# Expresión regular
URL = re.compile(
    r'\b((http[s]?://)?[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*\.[a-zA-Z]{2,})\b'
)

def is_user_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.id == user_id:
                return True
        return False
    except Exception as e:
        print(f'{e}: No se encontró el id del administrador')

def delete_welcome_message(message):
    for member in message.new_chat_members:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            print(f"Mensaje de bienvenida de {member.username} eliminado.")
        except Exception as e:
            print(f"No se pudo eliminar el mensaje de bienvenida: {e}")

def get_user_id_by_username(chat_id, username):
    try:
        if not username.startswith('@'):
            username = '@' + username
        user = bot.get_chat_member(chat_id, username)
        if user and user.user:
            return user.user.id
    except Exception as e:
        print(f"Error al obtener el ID del usuario {username}: {e}")
    return None

def ban_user(chat_id, username):
    try:
        user_id = get_user_id_by_username(chat_id, username)
        if user_id:
            bot.kick_chat_member(chat_id, user_id)
            print(f"Usuario {username} baneado del chat {chat_id}.")
        else:
            print(f"No se pudo encontrar al usuario {username} en el chat {chat_id}.")
    except Exception as e:
        print(f"No se pudo banear al usuario {username}: {e}")

def mute_user(chat_id, username, until_date=None):
    try:
        user_id = get_user_id_by_username(chat_id, username)
        if user_id:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False, until_date=until_date)
            print(f"Usuario {username} silenciado en el chat {chat_id}.")
        else:
            print(f"No se pudo encontrar al usuario {username} en el chat {chat_id}.")
    except Exception as e:
        print(f"No se pudo silenciar al usuario {username}: {e}")

def unmute_user(chat_id, username):
    try:
        user_id = get_user_id_by_username(chat_id, username)
        if user_id:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=True)
            print(f"Usuario {username} reactivado en el chat {chat_id}.")
        else:
            print(f"No se pudo encontrar al usuario {username} en el chat {chat_id}.")
    except Exception as e:
        print(f"No se pudo reactivar al usuario {username}: {e}")

def parse_duration(duration):
    unit = duration[-1]
    time_value = int(duration[:-1])
    if unit == 'm':
        return time_value * 60
    elif unit == 'h':
        return time_value * 3600
    elif unit == 'd':
        return time_value * 86400
    elif unit == 'w':
        return time_value * 604800
    else:
        raise ValueError("Unidad de tiempo no válida")

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    Thread(target=delete_welcome_message, args=(message,)).start()

@bot.message_handler(commands=['start'])
def start(message):
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        print(f"Mensaje de comando /start de {message.from_user.username} eliminado.")
    except Exception as e:
        print(f"No se pudo eliminar el mensaje de comando /start: {e}")

@bot.message_handler(func=lambda message: URL.search(message.text) is not None)
def handle_message_with_urls(message):
    if not is_user_admin(message.chat.id, message.from_user.id):
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            print(f"Mensaje con URL de {message.from_user.username} eliminado.")
            bot.send_message(chat_id=message.chat.id, text=f"@{message.from_user.username} no se permite enviar enlaces, cuidadito eh!!")
            ban_user(message.chat.id, message.from_user.username)
        except Exception as e:
            print(f'{e} Error al borrar el mensaje o banear al usuario')

def ban_help(message):
    ban_message = (
        "Para banear usa el siguiente comando /ban @username.\n\n"
    )
    bot.send_message(chat_id=message.chat.id, text=ban_message)

@bot.message_handler(commands=['ban'])
def ban_user_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        try:
            username = message.text.split()[1]
            ban_user(message.chat.id, username)
            bot.send_message(chat_id=message.chat.id, text=f"Usuario {username} baneado.")
        except (IndexError, ValueError):
            bot.send_message(chat_id=message.chat.id, text="Uso: /ban @username")
        except Exception as e:
            bot.send_message(chat_id=message.chat.id, text=f"No se pudo banear al usuario: {e}")
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para usar este comando.")

@bot.message_handler(commands=['dban'])
def dban_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        if message.reply_to_message:
            username = message.reply_to_message.from_user.username
            try:
                ban_user(message.chat.id, username)
                bot.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
                bot.send_message(chat_id=message.chat.id, text=f"Usuario {username} baneado y mensaje eliminado.")
            except Exception as e:
                bot.send_message(chat_id=message.chat.id, text=f"No se pudo banear al usuario: {e}")
        else:
            bot.send_message(chat_id=message.chat.id, text="Usa este comando en respuesta a un mensaje para banear al usuario.")
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para usar este comando.")

@bot.message_handler(commands=['sban'])
def sban_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        try:
            username = message.text.split()[1]
            ban_user(message.chat.id, username)
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except (IndexError, ValueError):
            bot.send_message(chat_id=message.chat.id, text="Uso: /sban @username")
        except Exception as e:
            bot.send_message(chat_id=message.chat.id, text=f"No se pudo banear al usuario: {e}")
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para usar este comando.")

@bot.message_handler(commands=['mute'])
def mute_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        try:
            username = message.text.split()[1]
            mute_user(message.chat.id, username)
            bot.send_message(chat_id=message.chat.id, text=f"Usuario {username} silenciado.")
        except (IndexError, ValueError):
            bot.send_message(chat_id=message.chat.id, text="Uso: /mute @username")
        except Exception as e:
            bot.send_message(chat_id=message.chat.id, text=f"No se pudo silenciar al usuario: {e}")
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para usar este comando.")

@bot.message_handler(commands=['tmute'])
def tmute_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        try:
            args = message.text.split()
            username = args[1]
            duration = args[2]
            until_date = time.time() + parse_duration(duration)
            mute_user(message.chat.id, username, until_date)
            bot.send_message(chat_id=message.chat.id, text=f"Usuario {username} silenciado por {duration}.")
        except (IndexError, ValueError):
            bot.send_message(chat_id=message.chat.id, text="Uso: /tmute @username <duration>")
        except Exception as e:
            bot.send_message(chat_id=message.chat.id, text=f"No se pudo silenciar al usuario: {e}")
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para usar este comando.")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Banear Usuario", callback_data="ban_help"))
        markup.add(InlineKeyboardButton("Baneo por Respuesta", callback_data="dban_help"))
        markup.add(InlineKeyboardButton("Baneo Silencioso", callback_data="sban_help"))
        markup.add(InlineKeyboardButton("Silenciar Usuario", callback_data="mute_help"))
        markup.add(InlineKeyboardButton("Silencio Temporal", callback_data="tmute_help"))
        bot.send_message(chat_id=message.chat.id, text="Panel de administrador:", reply_markup=markup)
    else:
        bot.send_message(chat_id=message.chat.id, text="No tienes permisos para acceder a este panel.")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "ban_help":
        ban_help(call.message)
    elif call.data == "dban_help":
        bot.send_message(chat_id=call.message.chat.id, text="Usa /dban en respuesta a un mensaje para banear al usuario y eliminar su mensaje.")
    elif call.data == "sban_help":
        bot.send_message(chat_id=call.message.chat.id, text="Usa /sban @username para banear al usuario en silencio y eliminar tu mensaje de comando.")
    elif call.data == "mute_help":
        bot.send_message(chat_id=call.message.chat.id, text="Usa /mute @username para silenciar a un usuario.")
    elif call.data == "tmute_help":
        bot.send_message(chat_id=call.message.chat.id, text="Usa /tmute @username <duration> para silenciar temporalmente a un usuario. Ejemplos de duración: 4m, 3h, 6d, 5w.")

def start_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True)
        except ConnectionError:
            print("Connection error occurred, retrying in 15 seconds...")
            time.sleep(15)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(15)  # Sleep to prevent rapid retry loop

# Start bot polling in a separate thread
bot_thread = Thread(target=start_bot_polling)
bot_thread.start()

# Flask server setup
app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
