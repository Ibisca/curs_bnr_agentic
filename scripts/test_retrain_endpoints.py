import requests, json
base = 'http://127.0.0.1:7772'

print('GET /api/health')
try:
    r = requests.get(base + '/api/health', timeout=5)
    print(r.status_code, r.json())
except Exception as e:
    print('health error:', e)

print('\nGET /api/runs?limit=5')
try:
    r = requests.get(base + '/api/runs?limit=5', timeout=5)
    print(r.status_code, r.json())
except Exception as e:
    print('runs error:', e)

print('\nGET /api/forecast/latest')
try:
    r = requests.get(base + '/api/forecast/latest', timeout=5)
    print(r.status_code, r.json())
except Exception as e:
    print('forecast error:', e)

print('\nPOST /api/retrain (timeout=300)')
try:
    r = requests.post(base + '/api/retrain', timeout=300)
    try:
        print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print('Status code', r.status_code, 'response text:', r.text)
except Exception as e:
    print('retrain error:', e)
