"""
AUDITORIA PASIVA - Verity MVP
Walmart Sales CSV Test

NO MODIFICA CODIGO - SOLO EJECUTA Y REPORTA
"""

import httpx
import json
from datetime import datetime

API_URL = "http://127.0.0.1:8001/api/v2/query"
TIMEOUT = 30.0

# Preguntas exactas del auditor
QUESTIONS = [
    "Cuantos registros hay?",
    "Cuantas tiendas unicas hay?",
    "Top 5 tiendas por ventas",
    "Top 10 departamentos por ventas",
    "Top 5 tiendas en semanas con holiday",
    "Top 5 tiendas por ventas",  # Repetir para verificar cache
]

def run_audit():
    print("=" * 60)
    print("  AUDITORIA PASIVA - VERITY MVP")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    # Usamos walmart como tabla disponible
    available_tables = ["walmart"]
    conversation_id = None  # Same conversation for context
    
    results = []
    
    for i, question in enumerate(QUESTIONS, 1):
        print(f"[{i}/6] Pregunta: {question}")
        print("-" * 40)
        
        try:
            payload = {
                "question": question,
                "available_tables": available_tables,
            }
            if conversation_id:
                payload["conversation_id"] = conversation_id
            
            r = httpx.post(API_URL, json=payload, timeout=TIMEOUT)
            data = r.json()
            
            # Capturar conversation_id para continuidad
            if not conversation_id:
                conversation_id = data.get("conversation_id")
            
            result = {
                "question": question,
                "status_code": r.status_code,
                "intent": data.get("intent"),
                "confidence": data.get("confidence"),
                "response": data.get("response", "")[:200],
                "checkpoints": len(data.get("checkpoints", [])),
                "cache_hit": False,  # TODO: detectar si hubo cache hit
                "human_intervention": "disambiguation" in str(data.get("response", "")).lower(),
            }
            
            print(f"  Status: {r.status_code}")
            print(f"  Intent: {data.get('intent')}")
            print(f"  Confidence: {data.get('confidence')}")
            print(f"  Response: {data.get('response', '')[:150]}...")
            print(f"  Checkpoints: {len(data.get('checkpoints', []))}")
            
        except httpx.HTTPStatusError as e:
            result = {
                "question": question,
                "status_code": e.response.status_code,
                "error": str(e),
                "response": e.response.text[:200] if e.response else "",
            }
            print(f"  HTTP Error: {e.response.status_code}")
            print(f"  Detail: {e.response.text[:150] if e.response else 'N/A'}")
            
        except Exception as e:
            result = {
                "question": question,
                "status_code": None,
                "error": f"{type(e).__name__}: {e}",
            }
            print(f"  Exception: {type(e).__name__}: {e}")
        
        results.append(result)
        print()
    
    # Reporte final
    print("=" * 60)
    print("  REPORTE FINAL")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.get("status_code") == 200 and r.get("confidence", 0) > 0.5)
    failed = len(results) - passed
    
    print(f"\n  Total: {len(results)} preguntas")
    print(f"  OK (status 200, confidence > 0.5): {passed}")
    print(f"  Failed o low confidence: {failed}")
    
    print("\n  Detalle por pregunta:")
    for i, r in enumerate(results, 1):
        status = "OK" if r.get("status_code") == 200 and r.get("confidence", 0) > 0.5 else "FAIL"
        cache = "[CACHE]" if r.get("cache_hit") else ""
        human = "[HUMAN]" if r.get("human_intervention") else ""
        print(f"    {i}. {status} {cache}{human} - {r['question'][:40]}")
        if r.get("error"):
            print(f"       Error: {r['error'][:80]}")
    
    print("=" * 60)
    
    # Guardar resultados a JSON
    with open("audit_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n  Resultados guardados en: audit_results.json")
    
    return results

if __name__ == "__main__":
    run_audit()
