"""Full account data export - GET /api/settings/export.

Exports only the authenticated caller's own data. Deliberately excludes
the password hash, session token hashes, CSRF secrets, and anything
belonging to another user - see the exclusion list below and the
corresponding test in tests/test_data_export.py.

This is a structured JSON export, not a claim of legal compliance -
providing this endpoint does not by itself make the application
GDPR/KVKK compliant (see docs/SECURITY.md and the Financial/Privacy
disclaimers).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.experiments import store as experiments_store
from app.experiments.store import experiment_to_dict
from app.models_db.user import User
from app.notifications import service as notifications_service
from app.paper_trading import store as paper_trading_store
from app.preferences import service as preferences_service
from app.support import service as support_service
from app.watchlist import store as watchlist_store


def export_user_data(db: Session, user: User) -> dict:
    prefs = preferences_service.get_preferences(db, user.id)

    return {
        "export_format_version": 1,
        "profile": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            # Deliberately excluded: password_hash, session token hashes,
            # CSRF secrets, auth token hashes - none of these are secrets
            # the user needs back, and returning them would be a security
            # regression, not a privacy feature.
        },
        "preferences": {
            "timezone": prefs.timezone,
            "default_benchmark": prefs.default_benchmark,
            "theme": prefs.theme,
            "email_notifications_enabled": prefs.email_notifications_enabled,
            "research_notifications_enabled": prefs.research_notifications_enabled,
            "marketing_consent": prefs.marketing_consent,
            "terms_accepted_at": prefs.terms_accepted_at.isoformat() if prefs.terms_accepted_at else None,
            "privacy_accepted_at": prefs.privacy_accepted_at.isoformat() if prefs.privacy_accepted_at else None,
            "onboarding_completed": prefs.onboarding_completed,
        },
        "watchlists": [
            {
                "slug": w.slug,
                "tickers": w.tickers,
                "created_at": w.created_at.isoformat(),
                "updated_at": w.updated_at.isoformat(),
            }
            for w in watchlist_store.list_all_watchlists(db, user.id)
        ],
        "paper_portfolios": [
            {
                "slug": p.slug,
                # `state` already contains cash/positions/trades/
                # equity_snapshots/benchmark_basis in full.
                "state": p.state,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in paper_trading_store.list_all_portfolios(db, user.id)
        ],
        "experiments": [experiment_to_dict(e) for e in experiments_store.list_experiments(db, user.id)],
        "notifications": [
            {
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "target_route": n.target_route,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in notifications_service.list_notifications(db, user.id, limit=notifications_service.MAX_LIST_LIMIT)
        ],
        "support_requests": [
            {
                "category": r.category,
                "subject": r.subject,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in support_service.list_my_support_requests(db, user.id)
        ],
    }
