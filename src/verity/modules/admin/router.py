"""
Verity Admin Module

System administration endpoints:
- Cache management
- System health
- Maintenance tasks
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from verity.deps import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[require_admin])


class CacheStats(BaseModel):
    """Cache statistics."""
    data_engine_cache_size: int
    data_engine_hits: int = 0
    data_engine_misses: int = 0


@router.post("/cache/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """
    Clear all system caches.
    
    Target caches:
    - Data Engine (query results)
    - Document Metadata (if cached)
    """
    from verity.modules.data.engine import get_data_engine
    
    engine = await get_data_engine()
    engine.clear_cache()
    
    # Add logs
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[ADMIN] Cache cleared by user")


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get cache visibility."""
    from verity.modules.data.engine import get_data_engine
    
    engine = await get_data_engine()
    stats = engine.get_cache_stats()
    
    return CacheStats(
        data_engine_cache_size=stats.get("size", 0),
        data_engine_hits=stats.get("hits", 0),
        data_engine_misses=stats.get("misses", 0)
    )
