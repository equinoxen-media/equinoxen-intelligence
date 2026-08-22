"""
pinterest_oauth_setup.py

One-time OAuth 2.0 setup script for Pinterest API access.
Run this locally (with ngrok) or temporarily on your server to complete
the authorization flow and obtain an access_token + refresh_token.

This is SEPARATE from content_pipeline.py — run it once, copy the tokens
into your .env, then this script is no longer needed for normal operation.

SETUP BEFORE RUNNING:
1. In your Pinterest Developer App settings, add a redirect URI.
   - If using ngrok: https://<your-ngrok-subdomain>.ngrok-free.app/pinterest/callback
   - If deploying to your server: https://equinoxen.com/pinterest/callback
2. Set these in your .env (or export as env vars before running):
   PINTEREST_CLIENT_ID=xxx
   PINTEREST_CLIENT_SECRET=xxx
   PINTEREST_REDIRECT_URI=https://<matches-what-you-registered>/pinterest/callback

INSTALL:
   pip install flask requests python-dotenv --break-system-packages

RUN:
   python3 pinterest_oauth_setup.py
   (then, in a separate terminal if using ngrok: ngrok http 5000)

FLOW:
   1. Visit http://localhost:5000/pinterest/connect in your browser
   2. Log into Pinterest, click "Allow"
   3. You'll be redirected back and see your tokens printed on screen
   4. Copy PINTEREST_ACCESS_TOKEN and PINTEREST_REFRESH_TOKEN into your .env
"""

import os
import base64
import urllib.parse
import requests
from flask import Flask, request, redirect

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # fine if you're exporting env vars manually instead

app = Flask(__name__)

PINTEREST_CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
PINTEREST_CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")
PINTEREST_REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:5000/pinterest/callback")

# Scopes — adjust if your app needs more/less. These cover reading boards
# and creating pins, which is what post_to_pinterest() in content_pipeline.py needs.
SCOPES = "boards:read,pins:read,pins:write,boards:write"


@app.route("/")
def index():
    return '<a href="/pinterest/connect">Connect to Pinterest</a>'


@app.route("/pinterest/connect")
def connect():
    if not PINTEREST_CLIENT_ID:
        return "ERROR: PINTEREST_CLIENT_ID not set in environment.", 500

    params = {
        "client_id": PINTEREST_CLIENT_ID,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    }
    auth_url = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode(params)
    return redirect(auth_url)


@app.route("/pinterest/callback")
def callback():
    error = request.args.get("error")
    if error:
        return f"<h2>Authorization failed</h2><pre>{error}</pre>", 400

    code = request.args.get("code")
    if not code:
        return "No authorization code received.", 400

    credentials = f"{PINTEREST_CLIENT_ID}:{PINTEREST_CLIENT_SECRET}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    resp = requests.post(
        "https://api.pinterest.com/v5/oauth/token",
        headers={
            "Authorization": f"Basic {encoded_creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": PINTEREST_REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        return f"<h2>Token exchange failed ({resp.status_code})</h2><pre>{resp.text}</pre>", 500

    tokens = resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    # Quick sanity check: confirm the token actually works by fetching boards
    verify = requests.get(
        "https://api.pinterest.com/v5/boards",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    boards_preview = verify.json() if verify.status_code == 200 else {"error": verify.text}

    return f"""
    <h2>Success — copy these into your .env</h2>
    <pre>
PINTEREST_ACCESS_TOKEN={access_token}
PINTEREST_REFRESH_TOKEN={refresh_token}
    </pre>
    <p>Access token expires in {expires_in} seconds (~{round(expires_in / 86400, 1) if expires_in else '?'} days).</p>
    <h3>Boards this token can see (sanity check):</h3>
    <pre>{boards_preview}</pre>
    """


@app.route("/pinterest/refresh")
def refresh():
    """
    Demo route: uses the refresh_token obtained during /pinterest/callback
    to get a new access_token. Pass it in as a query param for this demo:
    /pinterest/refresh?refresh_token=xxx
    (In production, content_pipeline.py reads this from .env instead.)
    """
    refresh_token = request.args.get("refresh_token") or os.getenv("PINTEREST_REFRESH_TOKEN")
    if not refresh_token:
        return "No refresh_token provided or found in environment.", 400

    credentials = f"{PINTEREST_CLIENT_ID}:{PINTEREST_CLIENT_SECRET}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    resp = requests.post(
        "https://api.pinterest.com/v5/oauth/token",
        headers={
            "Authorization": f"Basic {encoded_creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )

    if resp.status_code != 200:
        return f"<h2>Refresh failed ({resp.status_code})</h2><pre>{resp.text}</pre>", 500

    tokens = resp.json()
    new_access_token = tokens.get("access_token")
    new_refresh_token = tokens.get("refresh_token")  # only present if Pinterest rotates it
    expires_in = tokens.get("expires_in")

    # Sanity check — confirm the refreshed token actually works
    verify = requests.get(
        "https://api.pinterest.com/v5/boards",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    boards_preview = verify.json() if verify.status_code == 200 else {"error": verify.text}

    return f"""
    <h2>Token refreshed successfully</h2>
    <pre>
NEW PINTEREST_ACCESS_TOKEN={new_access_token}
{"NEW PINTEREST_REFRESH_TOKEN=" + new_refresh_token if new_refresh_token else "(refresh_token not rotated — original still valid)"}
    </pre>
    <p>New access token expires in {expires_in} seconds.</p>
    <h3>Boards confirmed accessible with refreshed token:</h3>
    <pre>{boards_preview}</pre>
    """


if __name__ == "__main__":
    if not PINTEREST_CLIENT_ID or not PINTEREST_CLIENT_SECRET:
        print("WARNING: PINTEREST_CLIENT_ID / PINTEREST_CLIENT_SECRET not found in environment.")
        print("Set them in .env or export them before running.")
    print(f"Redirect URI configured as: {PINTEREST_REDIRECT_URI}")
    print("Visit http://localhost:5000/pinterest/connect to start the flow.")
    app.run(host="0.0.0.0", port=5000, debug=True)
