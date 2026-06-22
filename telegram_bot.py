import requests

def send_alert(message):

    token = "8778860843:AAHd06Hpdx5K5wy9ay0mvH-n1umvBesl8W8"

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
