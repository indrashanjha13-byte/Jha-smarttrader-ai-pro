import requests

BOT_TOKEN = "8652639978:AAE8OIx6Rt8TAlDyj0GCx1d6Tl1Vp-HAvPI"
CHAT_ID = "2019899357"


def send_alert(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)