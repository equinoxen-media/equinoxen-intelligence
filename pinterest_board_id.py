import requests
import os

token = os.getenv("PINTEREST_ACCESS_TOKEN")
response = requests.get(
    "https://api.pinterest.com/v5/boards",
    headers={"Authorization": f"Bearer {token}"},
    params={"fields": "id,name"}
)
print(response.status_code)
print(response.json())

