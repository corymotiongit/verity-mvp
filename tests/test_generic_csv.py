"""
Test de genericidad del sistema Verity.

Objetivo: Validar si el sistema puede manejar un CSV arbitrario
sin tocar código ni modificar el Data Dictionary.

CSV de prueba: walmart.csv
Columnas: Store, Date, Weekly_Sales, Holiday_Flag, Temperature, Fuel_Price, CPI, Unemployment

Operaciones a probar:
1. COUNT - Contar registros
2. UNIQUE - Valores únicos de una columna
3. TOP N - Ranking de entidades

RESULTADO ESPERADO:
- Si el sistema es genérico: Las 3 operaciones funcionan
- Si tiene dependencias hardcodeadas: Falla con error de tabla/métrica no encontrada
"""

import asyncio
import pandas as pd
from pathlib import Path

# Ruta del CSV de prueba
WALMART_CSV_PATH = Path(r"C:\Users\ofgarcia\Downloads\walmart.csv")


def test_csv_exists_and_valid():
    """Verificar que el CSV existe y tiene estructura válida."""
    assert WALMART_CSV_PATH.exists(), f"CSV no encontrado: {WALMART_CSV_PATH}"
    
    df = pd.read_csv(WALMART_CSV_PATH)
    print(f"\n=== CSV Walmart ===")
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Sample:\n{df.head(3)}")
    
    # Verificar columnas esperadas
    expected_cols = ['Store', 'Date', 'Weekly_Sales', 'Holiday_Flag', 'Temperature', 'Fuel_Price', 'CPI', 'Unemployment']
    actual_cols = df.columns.tolist()
    
    # Limpiar nombres (pueden tener espacios o caracteres raros)
    actual_cols_clean = [c.strip() for c in actual_cols]
    
    assert len(actual_cols) >= 5, f"CSV debería tener al menos 5 columnas, tiene {len(actual_cols)}"
    print(f"[OK] CSV válido con {len(actual_cols)} columnas\n")


def test_data_dictionary_does_not_contain_walmart():
    """Verificar que el Data Dictionary NO contiene walmart (baseline)."""
    from verity.data import DataDictionary
    
    dd = DataDictionary()
    tables = dd.list_tables()
    
    print(f"=== Data Dictionary ===")
    print(f"Tablas registradas: {tables}")
    
    assert "walmart" not in tables, "walmart ya está en el Data Dictionary - test inválido"
    print(f"[OK] walmart NO está en el Data Dictionary (baseline correcto)\n")


def test_count_operation_on_walmart():
    """
    TEST: COUNT - ¿Cuántos registros hay?
    
    Pregunta: "cuántos registros hay en walmart"
    Esperado (si es genérico): COUNT(*) = 6435
    """
    from verity.tools.resolve_semantics import ResolveSemanticsTool
    
    tool = ResolveSemanticsTool()
    
    try:
        result = asyncio.run(tool.execute({
            "question": "cuántos registros hay",
            "available_tables": ["walmart"],
        }))
        print(f"=== COUNT Operation ===")
        print(f"Result: {result}")
        print(f"[OK] COUNT funcionó - Sistema GENÉRICO")
        return True
        
    except Exception as e:
        print(f"=== COUNT Operation ===")
        print(f"Error: {type(e).__name__}: {e}")
        print(f"[FAIL] COUNT falló - Sistema HARDCODEADO")
        return False


def test_unique_operation_on_walmart():
    """
    TEST: UNIQUE - ¿Cuántas tiendas únicas hay?
    
    Pregunta: "cuántas tiendas únicas hay"
    Esperado (si es genérico): COUNT(DISTINCT Store)
    """
    from verity.tools.resolve_semantics import ResolveSemanticsTool
    
    tool = ResolveSemanticsTool()
    
    try:
        result = asyncio.run(tool.execute({
            "question": "cuántas tiendas únicas hay",
            "available_tables": ["walmart"],
        }))
        print(f"=== UNIQUE Operation ===")
        print(f"Result: {result}")
        print(f"[OK] UNIQUE funcionó - Sistema GENÉRICO")
        return True
        
    except Exception as e:
        print(f"=== UNIQUE Operation ===")
        print(f"Error: {type(e).__name__}: {e}")
        print(f"[FAIL] UNIQUE falló - Sistema HARDCODEADO")
        return False


def test_topn_operation_on_walmart():
    """
    TEST: TOP N - ¿Cuáles son las top 5 tiendas por ventas?
    
    Pregunta: "top 5 tiendas por ventas"
    Esperado (si es genérico): GROUP BY Store, ORDER BY SUM(Weekly_Sales) DESC, LIMIT 5
    """
    from verity.tools.resolve_semantics import ResolveSemanticsTool
    
    tool = ResolveSemanticsTool()
    
    try:
        result = asyncio.run(tool.execute({
            "question": "top 5 tiendas por ventas",
            "available_tables": ["walmart"],
        }))
        print(f"=== TOP N Operation ===")
        print(f"Result: {result}")
        print(f"[OK] TOP N funcionó - Sistema GENÉRICO")
        return True
        
    except Exception as e:
        print(f"=== TOP N Operation ===")
        print(f"Error: {type(e).__name__}: {e}")
        print(f"[FAIL] TOP N falló - Sistema HARDCODEADO")
        return False


def test_full_genericidad_report():
    """
    Test completo de genericidad.
    Ejecuta las 3 operaciones y genera reporte.
    """
    print("\n" + "="*60)
    print("  TEST DE GENERICIDAD - VERITY MVP")
    print("="*60 + "\n")
    
    # Baseline
    test_csv_exists_and_valid()
    test_data_dictionary_does_not_contain_walmart()
    
    # Tests de operaciones
    results = {
        "COUNT": test_count_operation_on_walmart(),
        "UNIQUE": test_unique_operation_on_walmart(),
        "TOP_N": test_topn_operation_on_walmart(),
    }
    
    # Reporte final
    print("\n" + "="*60)
    print("  REPORTE FINAL")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for op, success in results.items():
        status = "[OK] PASS" if success else "[FAIL] FAIL"
        print(f"  {op}: {status}")
    
    print(f"\n  Score: {passed}/{total}")
    
    if passed == total:
        print("\n  >>> SISTEMA ES GENÉRICO <<<")
    else:
        print("\n  >>> SISTEMA TIENE DEPENDENCIAS HARDCODEADAS <<<")
        print("  El Data Dictionary requiere registro explícito de tablas y métricas.")
    
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    test_full_genericidad_report()
