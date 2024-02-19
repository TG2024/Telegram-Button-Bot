import os
import requests
import json

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # 从环境变量中获取Token
URL = f"https://api.telegram.org/bot{TOKEN}/"

last_messages = {}
last_photos = {}

def get_updates(last_update_id=None):
    url = URL + "getUpdates"
    params = {"offset": last_update_id + 1} if last_update_id else {}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('result', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching updates: {e}")
        return []

def handle_callback_query(update):
    query = update["callback_query"]
    chat_id = query["message"]["chat"]["id"]
    message_id = query["message"]["message_id"]

    if query["data"] == "/close":
        if chat_id in last_messages:
            del last_messages[chat_id]
            send_message(chat_id, "进程已关闭。")
            delete_message(chat_id, message_id)
        else:
            send_message(chat_id, "没有进行中的进程。")

def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(URL + "sendMessage", data=payload)
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def send_photo(chat_id, photo_id, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_id, "caption": caption, "parse_mode": "Markdown"}
    try:
        requests.post(URL + "sendPhoto", data=payload)
    except requests.exceptions.RequestException as e:
        print(f"Error sending photo: {e}")

def handle_start(update):
    chat_id = update["message"]["chat"]["id"]
    first_name = update["message"]["from"]["first_name"]
    welcome_message = (
        f"👋 *你好, {first_name}。欢迎使用个性化按钮机器人！*\n\n"
        "您需要先发送您的文本内容。随后,您需要再根据提示发送一个按钮信息:\n\n"
        "*格式: * `按钮显示文字 - 按钮链接`\n\n"
        "*您现在可以发送消息了!*"
    )
    send_message(chat_id, welcome_message)

def handle_text_message(chat_id, message_text):
    if '-' in message_text and chat_id in last_messages:
        button_text, button_url = message_text.split('-', 1)
        button_text, button_url = button_text.strip(), button_url.strip()
        keyboard = {"inline_keyboard": [[{"text": button_text, "url": button_url}]]}
        send_message(chat_id, last_messages.pop(chat_id), reply_markup=keyboard)
    else:
        last_messages[chat_id] = message_text
        close_keyboard = {"inline_keyboard": [[{"text": "重新发送", "callback_data": "/close"}]]}
        send_message(chat_id, "消息已接收，请发送按钮信息。", reply_markup=close_keyboard)

def handle_photo_message(chat_id, message_caption, photo_id):
    last_photos[chat_id] = photo_id
    last_messages[chat_id] = message_caption
    close_keyboard = {"inline_keyboard": [[{"text": "重新发送", "callback_data": "/close"}]]}
    send_photo(chat_id, photo_id, message_caption)
    send_message(chat_id, "文字描述型图片已接收，请发送按钮信息。", reply_markup=close_keyboard)

def delete_message(chat_id, message_id):
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        requests.post(URL + "deleteMessage", data=payload)
    except requests.exceptions.RequestException as e:
        print(f"Error deleting message: {e}")

def handle_message(update):
    if "callback_query" in update:
        handle_callback_query(update)
    elif "message" in update:
        chat_id = update["message"]["chat"]["id"]
        if "text" in update["message"]:
            message_text = update["message"]["text"]
            if message_text == "/start":
                handle_start(update)
            elif message_text == "/close":
                if chat_id in last_messages:
                    del last_messages[chat_id]
                    send_message(chat_id, "进程已关闭")
                else:
                    send_message(chat_id, "没有进行中的进程")
            else:
                handle_text_message(chat_id, message_text)
        elif "photo" in update["message"]:
            photo_id = update["message"]["photo"][-1]["file_id"]
            message_caption = update["message"].get("caption", "")
            handle_photo_message(chat_id, message_caption, photo_id)
        else:
            send_message(chat_id, "请发送文本消息或带说明的图片消息。")

def main():
    last_update_id = 0
    while True:
        updates = get_updates(last_update_id)
        for update in updates:
            update_id = update["update_id"]
            if last_update_id < update_id:
                last_update_id = update_id
                handle_message(update)

if __name__ == "__main__":
    main()
