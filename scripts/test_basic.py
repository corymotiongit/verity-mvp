import httpx

r = httpx.post(
    'http://127.0.0.1:8001/api/v2/query', 
    json={'question': 'cuantas canciones escuche', 'available_tables': ['orders', 'listening_history']}, 
    timeout=30.0
)
print(f'Status: {r.status_code}')
data = r.json()
print(f'Response: {data.get("response", "N/A")[:200]}')
