"""SQLAlchemy ORM models for the production SaaS foundation.

Importing this package registers every model on `app.db.base.Base.metadata`,
which both Alembic autogeneration and `create_all_tables()` rely on.
"""
from app.models_db.user import User, UserPreferences
from app.models_db.session import UserSession
from app.models_db.tokens import AuthToken
from app.models_db.notification import Notification
from app.models_db.support import SupportRequest
from app.models_db.watchlist import WatchlistDB
from app.models_db.paper_trading import PaperPortfolioDB
from app.models_db.experiment import ExperimentDB

__all__ = [
    "User",
    "UserPreferences",
    "UserSession",
    "AuthToken",
    "Notification",
    "SupportRequest",
    "WatchlistDB",
    "PaperPortfolioDB",
    "ExperimentDB",
]
