import os
import telebot
import re
from dotenv import load_dotenv
from threading import Thread
import time
from requests.exceptions import ConnectionError
from flask import Flask

load_dotenv()

API_KEY = os.getenv('API_KEY')
PORT = int(os.getenv('PORT', 5000))

if API_KEY is None:
    raise ValueError("No se encontró la variable de entorno 'API_KEY'.")

bot = telebot.TeleBot(API_KEY)

# Expresión regular
URL = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

###############################################################################################
#######################- FUNCIONES DEL BOT -#################################################
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

###############################################################################################
############################- FUNCIONES DE ESCUCHA -############################################
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    Thread(target=delete_welcome_message, args=(message,)).start()

###############################################################################################
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, '¡Hola! Soy Niki bot estaré escuchando todas tus peticiones.')
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        print(f"Mensaje de comando /start de {message.from_user.username} eliminado.")
    except Exception as e:
        print(f"No se pudo eliminar el mensaje de comando /start: {e}")

###############################################################################################
@bot.message_handler(func=lambda message: URL.search(message.text) is not None)
def handle_message_with_urls(message):
    if not is_user_admin(message.chat.id, message.from_user.id):
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            print(f"Mensaje con URL de {message.from_user.username} eliminado.")
            bot.send_message(chat_id=message.chat.id, text=f"@{message.from_user.username} baneado, no está permitido enviar enlaces, niki los castigara si continuan.")
        except Exception as e:
            print(f'{e} Error al borrar el mensaje')

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
