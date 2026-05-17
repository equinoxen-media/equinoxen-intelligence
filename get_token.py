import requests
import os
# Paste your credentials and the copied code here
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = 'https://equinoxen.com'
AUTHORIZATION_CODE = 'input_code_from_url'

url = "https://www.linkedin.com/oauth/v2/accessToken"
headers = {'Content-Type': 'application/x-www-form-urlencoded'}

data = {
'grant_type': 'authorization_code',
'code': AUTHORIZATION_CODE,
'redirect_uri': REDIRECT_URI,
'client_id': CLIENT_ID,
'client_secret': CLIENT_SECRET
}

response = requests.post(url, headers=headers, data=data)
token_data = response.json()

print("Your Access Token is:", token_data.get('access_token'))
print("Expires in (seconds):", token_data.get('expires_in'))

