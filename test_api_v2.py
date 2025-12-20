"""
Script de prueba para la API v2 de Verity
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Probar endpoint de salud"""
    print("\n=== Probando /api/v2/health ===")
    try:
        response = requests.get(f"{BASE_URL}/api/v2/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_query():
    """Probar endpoint de query"""
    print("\n=== Probando /api/v2/query ===")
    
    payload = {
        "question": "¿Cuántos ingresos totales hay?",
        "available_tables": ["pagado_ef", "vista_empleados", "proyectos"]
    }
    
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v2/query",
            json=payload,
            timeout=30
        )
        
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Esperando que el servidor esté listo...")
    time.sleep(2)
    
    try:
        # Probar health check
        if test_health():
            print("\n✅ Health check exitoso")
        else:
            print("\n❌ Health check falló")
        
        # Probar query
        if test_query():
            print("\n✅ Query exitoso")
        else:
            print("\n❌ Query falló")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    input("\n\nPresiona Enter para salir...")
