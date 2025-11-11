"""Utility helpers to manage simple session-based authentication state."""

from __future__ import annotations

from flask import session


_SESSION_AUTH_FLAG = "auth_logged_in"
_SESSION_USERNAME = "auth_username"
_SESSION_USER_ID = "auth_user_id"


def login_user(user) -> None:
    """Persist the login state in the session."""

    session.permanent = True
    session[_SESSION_AUTH_FLAG] = True
    session[_SESSION_USERNAME] = getattr(user, "username", None)
    session[_SESSION_USER_ID] = getattr(user, "id", None)


def logout_user() -> None:
    """Clear session values related to authentication."""

    session.pop(_SESSION_AUTH_FLAG, None)
    session.pop(_SESSION_USERNAME, None)
    session.pop(_SESSION_USER_ID, None)


def is_authenticated() -> bool:
    """Return whether the current session is authenticated."""

    return bool(session.get(_SESSION_AUTH_FLAG))


def current_username() -> str | None:
    """Return the username stored in the session, if any."""

    return session.get(_SESSION_USERNAME)


def current_user_id() -> str | None:
    """Return the user id stored in the session, if any."""

    return session.get(_SESSION_USER_ID)
