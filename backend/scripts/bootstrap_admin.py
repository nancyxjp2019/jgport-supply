import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import generate_activation_code
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.activation_code import ActivationCode
from app.models.user import User, UserRole, UserStatus


def bootstrap_admin(username: str, display_name: str | None) -> None:
    settings = get_settings()
    init_db()

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is None:
            user = User(
                username=username,
                display_name=display_name,
                role=UserRole.ADMIN,
                status=UserStatus.PENDING_ACTIVATION,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user = existing

        code = generate_activation_code()
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.activation_code_expire_minutes)
        activation = ActivationCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
        )
        db.add(activation)
        db.commit()

    activation_url = f"{settings.activation_link_base_url}?code={code}&uid={user.id}"
    print(f"admin_user_id={user.id}")
    print(f"activation_code={code}")
    print(f"activation_url={activation_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="admin")
    parser.add_argument("--display-name", default="System Admin")
    args = parser.parse_args()
    bootstrap_admin(username=args.username, display_name=args.display_name)
