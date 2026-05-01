import urllib.request
import urllib.parse
import json
import ssl

def check():
    print("Checking API internal connectivity...")
    try:
        # 1. Login
        login_url = "http://localhost:8000/api/v1/auth/login"
        print(f"Attempting login at {login_url}...")
        
        data = urllib.parse.urlencode({
            "username": "admin@spear-guard.com",
            "password": "demo123"
        }).encode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        req = urllib.request.Request(login_url, data=data, headers=headers, method="POST")
        
        token = None
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read()
                token_data = json.loads(res_body)
                token = token_data.get("access_token")
                print(f"✓ Login successful. Token obtained.")
        except urllib.error.HTTPError as e:
            print(f"✗ Login Failed: {e.code} {e.read().decode()}")
            return
        except Exception as e:
            print(f"✗ Login Error: {e}")
            return

        if not token:
            print("✗ No access_token in response.")
            return

        # 2. Get Stats
        stats_url = "http://localhost:8000/api/v1/dashboard/stats"
        print(f"Fetching stats from {stats_url}...")
        
        req2 = urllib.request.Request(stats_url)
        req2.add_header("Authorization", f"Bearer {token}")
        
        try:
            with urllib.request.urlopen(req2) as resp2:
                stats = json.loads(resp2.read())
                print("✓ Stats Endpoint Response:")
                print(json.dumps(stats, indent=2))
                
                # Validation
                if stats.get("totalEmails", 0) > 0:
                     print("✓ API returns NON-ZERO data. Verification PASSED.")
                else:
                     print("! API returns ZEROS. Investigation needed.")

        except urllib.error.HTTPError as e:
            print(f"✗ Stats Failed: {e.code} {e.read().decode()}")

    except Exception as e:
        print(f"✗ Connection/Script Error: {e}")

if __name__ == "__main__":
    check()
