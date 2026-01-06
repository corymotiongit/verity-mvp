import httpx
import sys
import json

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def test_query(question):
    print(f"\nQUERY: {question}")
    try:
        r = httpx.post(
            'http://127.0.0.1:8001/api/v2/query', 
            json={'question': question, 'available_tables': ['orders', 'listening_history']}, 
            timeout=30.0
        )
        data = r.json()
        
        if 'checkpoints' in data and len(data['checkpoints']) > 0:
            cp0 = data['checkpoints'][0]
            output = cp0.get('output', {})
            print(f"PLAN: GroupBy={output.get('group_by')} Limit={output.get('limit')} Op={output.get('operation')}")
        
        if 'checkpoints' in data and len(data['checkpoints']) > 1:
            cp1 = data['checkpoints'][1]
            output = cp1.get('output', {})
            rows = output.get('rows', [])
            print(f"RESULTS ({len(rows)}):")
            for i, row in enumerate(rows[:5]):
                print(f"  {i+1}. {row}")
                
    except Exception as e:
        print(f"ERROR: {e}")

test_query("top 5 artistas mas escuchados")
test_query("top 10 canciones mas escuchadas")
