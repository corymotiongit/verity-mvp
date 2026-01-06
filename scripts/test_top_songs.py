import httpx

r = httpx.post(
    'http://127.0.0.1:8001/api/v2/query', 
    json={'question': 'top 10 canciones mas escuchadas', 'available_tables': ['orders', 'listening_history']}, 
    timeout=30.0
)
data = r.json()
print(f"Status: {r.status_code}")
print(f"Response: {data.get('response', 'N/A')[:300]}")

if 'checkpoints' in data and len(data['checkpoints']) > 1:
    cp = data['checkpoints'][1]
    rows = cp.get('output', {}).get('rows', [])
    print("\nTop 10 Canciones:")
    for i, row in enumerate(rows[:10]):
        print(f"  {i+1}. {row[0]} - {row[1]} plays")
