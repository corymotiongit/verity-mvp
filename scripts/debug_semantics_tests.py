"""Debug script para entender comportamiento actual de resolve_semantics."""
import asyncio
from verity.tools.resolve_semantics import ResolveSemanticsTool
from verity.exceptions import AmbiguousMetricException, UnresolvedMetricException

async def test():
    tool = ResolveSemanticsTool()
    
    # Test 1: tot_reven
    print("=== Test 1: tot_reven ===")
    try:
        out = await tool.execute({"question": "tot_reven", "available_tables": ["orders"]})
        metrics = out.get("metrics", [])
        print(f"Result: {metrics}")
        print(f"Confidence: {out.get('confidence')}")
    except AmbiguousMetricException as e:
        print(f"AmbiguousMetricException: {e.details}")
    except UnresolvedMetricException as e:
        print(f"UnresolvedMetricException: {e.details}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    
    # Test 2: ventas
    print()
    print("=== Test 2: ventas ===")
    try:
        out = await tool.execute({"question": "ventas", "available_tables": ["orders"]})
        metrics = out.get("metrics", [])
        print(f"Result: {metrics}")
    except AmbiguousMetricException as e:
        candidates = e.details.get("candidates", [])
        print(f"AmbiguousMetricException: candidates={len(candidates)}")
        for c in candidates[:3]:
            print(f"  - {c.get('metric')}: score={c.get('score')}")
    except UnresolvedMetricException as e:
        print(f"UnresolvedMetricException: {e.details}")
    
    # Test 3: profit margin
    print()
    print("=== Test 3: profit margin ===")
    try:
        out = await tool.execute({"question": "profit margin", "available_tables": ["orders"]})
        metrics = out.get("metrics", [])
        print(f"Result: {metrics}")
    except UnresolvedMetricException as e:
        print(f"UnresolvedMetricException: code={e.code}")
    except AmbiguousMetricException as e:
        print(f"AmbiguousMetricException: {e.details}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
