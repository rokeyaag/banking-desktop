import requests

try:
    r = requests.get('https://teaching-corn-medication-months.trycloudflare.com/login', timeout=10)
    print("STATUS_CODE:", r.status_code)
except Exception as e:
    print("REQUEST_ERROR:", e)
