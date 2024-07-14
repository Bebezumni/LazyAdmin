import telebot, os
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


TOKEN = os.environ["TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
BOT_CHAT_ID = os.environ["BOT_CHAT_ID"]
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)
allowed_ids = os.environ["ALLOWED_IDS"]
bot = telebot.TeleBot(TOKEN)
messages_to_send = {}
instructions = os.environ["INSTRUCTION"]

@bot.message_handler(commands=['send_messages'])
def send_messages_to_channel(message):
    for user_id, message_data in messages_to_send.items():
        media_group = []
        if message_data['photos']:
            for index, photo_id in enumerate(message_data['photos']):
                if index == 0 and message_data['text']:
                    media_group.append(
                        types.InputMediaPhoto(photo_id, caption=message_data['text'], parse_mode='Markdown'))
                else:
                    media_group.append(types.InputMediaPhoto(photo_id))

        if message_data['videos']:
            for index, video_id in enumerate(message_data['videos']):
                if not media_group and message_data['text']:
                    media_group.append(
                        types.InputMediaVideo(video_id, caption=message_data['text'], parse_mode='Markdown'))
                else:
                    media_group.append(types.InputMediaVideo(video_id))

        # Отправляем медиагруппу в канал
        if media_group:
            bot.send_media_group(CHANNEL_ID, media_group)
        print(f"Media group before sending: {media_group}")
        clear_messages_to_send(user_id)


def send_messages_to_bot(message):
    for user_id, message_data in messages_to_send.items():
        media_group = []
        if message_data['photos']:
            for index, photo_id in enumerate(message_data['photos']):
                if index == 0 and message_data['text']:
                    media_group.append(
                        types.InputMediaPhoto(photo_id, caption=message_data['text'], parse_mode='Markdown'))
                else:
                    media_group.append(types.InputMediaPhoto(photo_id))

        if message_data['videos']:
            for index, video_id in enumerate(message_data['videos']):
                if not media_group and message_data['text']:
                    media_group.append(
                        types.InputMediaVideo(video_id, caption=message_data['text'], parse_mode='Markdown'))
                else:
                    media_group.append(types.InputMediaVideo(video_id))
        if message_data['text_alone']:
            for index, text_id in enumerate(message_data['text_alone']):
                media_group.append(types.InputTextMessageContent(message_text=message_data['text_alone'], parse_mode='Markdown'))

        # Отправляем медиагруппу обратно по айди сообщения бота
        print(f"Media group: {media_group}")
        if media_group:
            bot.send_media_group(message.chat.id, media_group)
        print(f"Media group before sending: {media_group}")


def clear_messages_to_send(user_id):
    # Очищаем сообщение после отправки
    messages_to_send[user_id] = {
        'text': None,
        'photos': [],
        'videos': [],
        "message": [],
        "text_alone": None

    }


def give_choice(message):
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("Запостить", callback_data="send_post")
    button2 = InlineKeyboardButton("Изменить текст!", callback_data="regen_text")
    button3 = InlineKeyboardButton("Удалить всё", callback_data="delete_all")
    markup.add(button1, button2, button3)
    send_messages_to_bot(message)
    bot.send_message(message.chat.id, f"Понравился пост? \n", reply_markup=markup)


def get_new_text(message):
    if message.text:
        text= message.text
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ]
        )
        ai_response = response.choices[0].message.content
        messages_to_send[message.from_user.id][
            'text_alone'] = full_message = f"{ai_response} \n\n [Bezumni AI](https://t.me/bezumni_ai_bot)[🤖](https://t.me/bezumni_ai_bot)"
    else:
        text = message.caption

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ]
        )
        ai_response = response.choices[0].message.content
        messages_to_send[message.from_user.id][
            'text'] = full_message = f"{ai_response} \n\n [Bezumni AI](https://t.me/bezumni_ai_bot)[🤖](https://t.me/bezumni_ai_bot)"


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "send_post":
        print(f"callback on send catched")
        if call.message.chat.id in messages_to_send and 'message' in messages_to_send[call.message.chat.id] and len(
                messages_to_send[call.message.chat.id]['message']) > 0:
            send_messages_to_channel(call.message)
            bot.send_message(call.message.chat.id, "Пост уже на канале!")
        else:
            bot.send_message(call.message.chat.id, "Нечего отправлять")
    elif call.data == "regen_text":
        for user_id, message_data in messages_to_send.items():
            if call.message.chat.id in messages_to_send and 'message' in messages_to_send[call.message.chat.id] and len(
                    messages_to_send[call.message.chat.id]['message']) > 0:
                original_message = messages_to_send[call.message.chat.id]['message'][0]
                get_new_text(original_message)
            else:
                bot.send_message(call.message.chat.id, "Я пустой, жду новый пост!")
        give_choice(call.message)
    elif call.data == "delete_all":
        clear_messages_to_send(call.message.chat.id)
        bot.send_message(call.message.chat.id, "Я очищен, жду новый пост!")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    if message.from_user.id in allowed_ids:
        if message.from_user.id not in messages_to_send:
            messages_to_send[message.from_user.id] = {
                'text': None,
                'photos': [],
                'videos': [],
                "message": [],
                "text_alone": None
            }
        if message.text:
            get_new_text(message)
            messages_to_send[message.from_user.id]['message'].append(message)
        if message.caption:
            get_new_text(message)
            messages_to_send[message.from_user.id]['message'].append(message)
        if message.photo:
            messages_to_send[message.from_user.id]['photos'].append(message.photo[0].file_id)
        if message.video:
            messages_to_send[message.from_user.id]['videos'].append(message.video.file_id)
        give_choice(message)

bot.polling()