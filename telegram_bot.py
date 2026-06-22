import requests

def send_alert(message):

    token = "YOUR_NEW_TOKEN"
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
