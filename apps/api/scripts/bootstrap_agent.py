"""Bootstrap (or rotate) the agent service-account user.

Creates a User row with `role=agent` and a freshly generated random
password. Prints the password to stdout exactly once — capture it and
store it on the agent's host (e.g. `~/.config/3d-portal/agent.password`)
because the password is hashed at rest and cannot be recovered later.

Idempotent on email: re-running with the same email is a no-op (logs a
notice). Use `--rotate` to force a new password for an existing user.

Usage:
    python -m scripts.bootstrap_agent --email agent@portal.local
    python -m scripts.bootstrap_agent --email agent@portal.local --rotate
    python -m scripts.bootstrap_agent --email agent@portal.local --password '<custom>'

The agent then logs in like any user via POST /api/auth/login and uses
the returned JWT for subsequent admin API calls. JWT lifetime defaults
to 30 minutes; cron a daily re-auth on the agent host to keep the token
fresh.
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys

from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import User, UserRole
from app.core.db.session import get_engine

_ALPHABET = string.ascii_letters + string.digits


def _generate_password(length: int = 32) -> str:
    """Cryptographically random password of `length` chars from [a-zA-Z0-9]."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def bootstrap_agent(
    *,
    email: str,
    password: str | None = None,
    rotate: bool = False,
    display_name: str = "Agent",
) -> tuple[User, str, str]:
    """Create or rotate the agent service-account user.

    Returns (user, action, password) where action is one of:
      - "created" — new user inserted
      - "rotated" — existing user's password updated
      - "exists"  — existing user, no change (rotate=False)

    `password` is the cleartext password (only meaningful on create/rotate;
    empty string on "exists"). Caller should print and discard.
    """
    pw = password or _generate_password()
    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing is not None:
            if not rotate:
                return existing, "exists", ""
            existing.password_hash = hash_password(pw)
            existing.role = UserRole.agent  # ensure role correct on rotate
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing, "rotated", pw

        user = User(
            email=email,
            display_name=display_name,
            role=UserRole.agent,
            password_hash=hash_password(pw),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, "created", pw


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--email",
        required=True,
        help="Email for the agent service-account (e.g. agent@portal.local)",
    )
    p.add_argument(
        "--password",
        default=None,
        help="Custom password (omit for cryptographically random 32-char)",
    )
    p.add_argument(
        "--rotate",
        action="store_true",
        help="Replace password for existing user (otherwise no-op on duplicate email)",
    )
    p.add_argument(
        "--display-name",
        default="Agent",
        help="Display name (default: 'Agent')",
    )
    args = p.parse_args(argv)

    user, action, password = bootstrap_agent(
        email=args.email,
        password=args.password,
        rotate=args.rotate,
        display_name=args.display_name,
    )

    if action == "exists":
        print(
            f"agent user already exists: {user.email} (id={user.id}). "
            f"Use --rotate to issue a new password.",
            file=sys.stderr,
        )
        return 0

    print(
        f"# Agent {action}\n"
        f"# email:      {user.email}\n"
        f"# user_id:    {user.id}\n"
        f"# role:       {user.role.value}\n"
        f"# password:   {password}\n"
        f"#\n"
        f"# Save the password somewhere safe — it cannot be recovered later.\n"
        f"# Suggested: ~/.config/3d-portal/agent.password (chmod 600)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
