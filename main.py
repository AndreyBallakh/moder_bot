import telebot
import sqlite3
import os
import config as cfg
from datetime import datetime, timedelta
from telegram import ChatPermissions
import g4f

from colorama import Fore, init
init(autoreset=True)

TOKEN = cfg.TOKEN  # Replace with your actual bot token
bot = telebot.TeleBot(TOKEN)

mat = ['bitch', 'fuck']

# Connect to the SQLite database
def connect_db():
    return sqlite3.connect(os.path.join(os.path.dirname(__file__), 'ad_list.db'))

def check_for_mat(sentense, message):
    words_list = sentense.split()
    for word in range(len(words_list)):
        words_list[word-1] = ''.join(list(dict.fromkeys(list(words_list[word-1].lower())))) #removing duplicates
        if words_list[word-1] in mat:
            try:
                # Delete the offensive message
                bot.delete_message(message.chat.id, message_id=message.message_id)

                # Notify the user about the mute
                bot.send_message(message.chat.id, f'@{message.from_user.username} muted because of mat')
                bot.send_message(chat_id=cfg.ADMIN_ID, text=f'user: @{message.from_user.username};\ntext: {message.text}')

                # Mute the user for 30 seconds
                until_date = int((datetime.utcnow() + timedelta(seconds=30)).timestamp())
                permissions = ChatPermissions(can_send_messages=False)
                # bot.restrict_chat_member(message.chat.id, message.from_user.id, permissions, until_date=until_date)
            except Exception as e:
                print(f"Error muting user: {e}")
        else:
            pass

def create_ad_list_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_list (
            id INTEGER PRIMARY KEY,
            username TEXT,
            text TEXT,
            from_date DATETIME,
            until_date DATETIME,
            telegram_form_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def check_if_ad(message):
    try:
        # try:
        #     response = g4f.ChatCompletion.create(
        #         model="gpt-3.5-turbo",
        #         messages=[{"role": "user", "content": f" ({message.text}) Проверь или данное сообшение является рекламой и выдай ответ только True или False  Чтобы твой ответ можно было обработать в коде"}],
        #     )  
        #     if response == True:
        #         check_text_and_data(message)
        # except Exception as e:
        #     print(Fore.Red + f"check_if_ad gpt error: {e}")
        #     if len(message.text) >= 80:
        #         # bot.send_message(chat_id=cfg.ADMIN_ID, text=f'user: @{message.from_user.username};\ntext: {message.text}\ndata: {message.date}')
        #         check_text_and_data(message)
        if len(message.text) >= 80:
                # bot.send_message(chat_id=cfg.ADMIN_ID, text=f'user: @{message.from_user.username};\ntext: {message.text}\ndata: {message.date}')
                check_text_and_data(message)
    except Exception as e:
        print(Fore.RED + f'check_if_ad error: {e}')

def check_if_correct_message(message):
    try:
        response = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f" ({message.text}) Проверь или данное сообшение является рекламой не качественого продукта или призывом к заработку, сбору денег или спам или использование языка отличного от русского, украинского, англиского, румынского. И выдай ответ только одним словом true или false. Чтобы твой ответ можно было обработать в коде"}],
                # or socks5://user:pass@host:port
                timeout=120,  # in secs
            )  
        print(response)
        # if response == True:
        #     check_text_and_data(message)
    except Exception as e:
        print(Fore.RED + f"check_if_correct_message error: {e}")
        check_if_ad(message)

def insert_data_in_db(message):
    try:
        # Connect to the database and create the table if not exists
        create_ad_list_table()

        # Insert data into the ad_list table
        with connect_db() as conn:
            cursor = conn.cursor()
            username = f'@{message.from_user.username}'
            text = f'{message.text}'
            from_date = datetime.utcfromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')
            until_date = (datetime.utcfromtimestamp(message.date) + timedelta(seconds=604800)).strftime('%Y-%m-%d %H:%M:%S')
            telegrem_data = message.date + 60 #604800
            # Execute the SQL command to insert data into the table
            cursor.execute('''
                INSERT INTO ad_list (username, text, from_date, until_date, telegram_form_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, text, from_date, until_date, telegrem_data))
            conn.commit()
    except Exception as e:
        print(Fore.RED + f'insert_data_in_db: {e}')

def check_text_and_data(message):
    try:
        database_path = 'ad_list.db'
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()

            # Execute the SQL SELECT statement to check if the text already exists
            cursor.execute('SELECT * FROM ad_list WHERE text = ?', (message.text,))
            existing_row = cursor.fetchone()

            if existing_row:
                # bot.send_message(chat_id=cfg.ADMIN_ID, text=f'time: {message.date-int(existing_row[5])}')
                if message.date-int(existing_row[5]) < 0:
                    bot.send_message(chat_id=cfg.ADMIN_ID, text=f'Duplicate:\n\n{str(existing_row)}')
                    delete_message(message, existing_row[1])
                else:
                    cursor.execute('DELETE FROM ad_list WHERE text = ?', (message.text,))
                    conn.commit()
                    # Insert data into the ad_list table
                    insert_data_in_db(message)

    except Exception as e:
        print(Fore.RED + f'check_text_and_data: {e}') 

def delete_message(message, user):
    bot.delete_message(chat_id=message.chat.id, message_id=message.id)
    bot.send_message(chat_id=message.chat.id, text=f'{user} к сожелению нельзя постить рекламу чаше раза в неделю')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! I am your bot moderator.")
    # Create the ad_list table
    create_ad_list_table()

@bot.message_handler(commands=['database'])
def show_database(message):
    try:
        database_path = 'ad_list.db'
        if str(message.chat.id) == cfg.ADMIN_ID:
            with sqlite3.connect(database_path) as conn:
                cursor = conn.cursor()

                # Execute the SQL SELECT statement to retrieve all rows from the ad_list table
                cursor.execute('SELECT * FROM ad_list')
                rows = cursor.fetchall()

                # Print the contents of the ad_list table
                for row in rows:
                    bot.send_message(chat_id=message.chat.id, text=str(row))
        else:
            bot.send_message(chat_id=message.chat.id, text="you are not admin")
    except Exception as e:
        print(Fore.RED + f'show_database: {e}')

@bot.message_handler()
def check_message(message):
    # check_if_correct_message(message)
    check_if_ad(message)

@bot.edited_message_handler()
def check_edited_message(message):
    check_if_ad(message)

if __name__ == "__main__":
    bot.polling(none_stop=True)
