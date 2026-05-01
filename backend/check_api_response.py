import requests
import json
import os

# Use the credentials we just found
EMAIL = "admin@spear-guard.gov.ru"
PASSWORD = "admin123"
BASE_URL = "http://localhost:8000/api/v1"

def check_latest_analysis():
    # 1. Login
    login_resp = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Analysis List
    list_resp = requests.get(f"{BASE_URL}/analysis/?limit=1", headers=headers)
    if list_resp.status_code != 200:
        print(f"List failed: {list_resp.text}")
        return

    data = list_resp.json()["data"]
    if not data:
        print("No analysis found.")
        return

    latest = data[0]
    print(f"Latest Analysis ID: {latest['id']}")
    print(f"Subject: {latest['subject']}")
    
    # Check if analysis_details is present in list view
    if "analysis_details" in latest:
        print("analysis_details found in list view:")
        print(json.dumps(latest["analysis_details"], indent=2, ensure_ascii=False))
    else:
        print("analysis_details NOT found in list view (maybe ok if detail view only)")

    # 3. Get Detail View
    detail_resp = requests.get(f"{BASE_URL}/analysis/{latest['id']}", headers=headers)
    if detail_resp.status_code != 200:
        print(f"Detail failed: {detail_resp.text}")
        return
        
    detail = detail_resp.json()
    if "analysis_details" in detail:
        print("\nanalysis_details found in DETAIL view:")
        print(json.dumps(detail["analysis_details"], indent=2, ensure_ascii=False))
    else:
        print("\nanalysis_details MISSING in DETAIL view!")
        print("Keys available:", list(detail.keys()))

if __name__ == "__main__":
    check_latest_analysis()
