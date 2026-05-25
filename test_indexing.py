# save as test_indexing.py in ~/equinoxen-intelligence/
import os
from dotenv import load_dotenv
load_dotenv()

def test_google_indexing():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
            scopes=["https://www.googleapis.com/auth/indexing"]
        )
        
        service = build('indexing', 'v3', credentials=credentials)
        
        # Test with your homepage
        response = service.urlNotifications().publish(
            body={
                "url": "https://equinoxen.com",
                "type": "URL_UPDATED"
            }
        ).execute()
        
        print(f"✅ Success: {response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

test_google_indexing()
