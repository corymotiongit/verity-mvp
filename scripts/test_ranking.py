import httpx
import sys

def test_query(question):
    print(f"\nQuery: {question}")
    print("-" * 50)
    r = httpx.post(
        'http://127.0.0.1:8001/api/v2/query', 
        json={'question': question, 'available_tables': ['orders', 'listening_history']}, 
        timeout=30.0
    )
    data = r.json()
    print(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"Error: {data}")
        return
    
    # Semantic resolution output
    if 'checkpoints' in data and len(data['checkpoints']) > 0:
        cp0 = data['checkpoints'][0]
        output = cp0.get('output', {})
        print(f"Group By: {output.get('group_by', 'N/A')}")
        print(f"Limit: {output.get('limit', 'N/A')}")
    
    # Query output
    if 'checkpoints' in data and len(data['checkpoints']) > 1:
        cp1 = data['checkpoints'][1]
        output = cp1.get('output', {})
        rows = output.get('rows', [])
        cols = output.get('columns', [])
        print(f"Columns: {cols}")
        print(f"Results ({len(rows)} rows):")
        for i, row in enumerate(rows[:5]):
            print(f"  {i+1}. {row}")
    
    print(f"\nResponse: {data.get('response', 'N/A')[:150]}...")

# Tests
test_query("top 5 artistas mas escuchados")
test_query("top 10 canciones mas escuchadas")
test_query("cuantas canciones escuche")
