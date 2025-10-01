##backend/app/routes/__init__.py

from .jobs import router as jobs_router
from .candidates import router as candidates_router
from .TAteam import router as ta_team_router
from .notifications import router as notifications_router
from .upload import router as upload_router
from .ctc import router as ctc_router
from .documents import router as documents_router
from .dashboard import router as dashboard_router
from .discussionstatus import router as discussionstatus_router
from .stats_filter import router as stats_filter_router
from .referred_by import router as referred_by_router
from .data_retention import router as data_retention_router