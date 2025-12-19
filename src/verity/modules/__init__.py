"""Verity Modules - All application modules."""

from verity.modules.documents import router as documents_router
from verity.modules.approvals import router as approvals_router
from verity.modules.agent import router as agent_router
from verity.modules.charts import router as charts_router
from verity.modules.reports import router as reports_router
from verity.modules.forecast import router as forecast_router
from verity.modules.logs import router as logs_router
from verity.modules.audit import router as audit_router

__all__ = [
    "documents_router",
    "approvals_router",
    "agent_router",
    "charts_router",
    "reports_router",
    "forecast_router",
    "logs_router",
    "audit_router",
]
