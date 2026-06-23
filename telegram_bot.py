import requests

def send_alert(message):

    token = "8652639978:AAE8OIx6Rt8TAlDyj0GCx1d6Tl1Vp-HAvPI"
    chat_id = "2019899357"

    url = (
        f"https://api.telegram.org/bot"
        f"{token}/sendMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": message
        }
    )

    print(response.text)
