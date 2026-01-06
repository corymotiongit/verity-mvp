import httpx
import sys
import json

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def test_query(question):
    print(f"\nQUERY: {question}")
    print("-" * 50)
    try:
        r = httpx.post(
            'http://127.0.0.1:8001/api/v2/query', 
            json={'question': question, 'available_tables': ['orders', 'listening_history']}, 
            timeout=30.0
        )
        data = r.json()
        
        # Imprimir respuesta final del ResponseComposer
        print(f"RESPONSE:\n{data.get('response', 'N/A')}")
        print("-" * 50)
                
    except Exception as e:
        print(f"ERROR: {e}")

test_query("top 5 artistas mas escuchados")
test_query("top 10 canciones mas escuchadas")
