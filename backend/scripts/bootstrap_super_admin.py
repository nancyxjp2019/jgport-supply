import argparse

from sqlalchemy import select

from app.core.security import (
    build_totp_provisioning_uri,
    generate_recovery_codes,
    generate_totp_secret,
    hash_password,
    hash_recovery_code,
)
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.super_admin import SuperAdminCredential, SuperAdminMfa, SuperAdminRecoveryCode


def bootstrap_super_admin(username: str, display_name: str | None, password: str, issuer: str) -> None:
    init_db()
    with SessionLocal() as db:
        username_text = username.strip()
        row = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.username == username_text))
        if row is None:
            row = SuperAdminCredential(
                username=username_text,
                display_name=display_name,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(row)
            db.flush()
        else:
            row.display_name = display_name
            row.password_hash = hash_password(password)
            row.is_active = True
            row.failed_login_count = 0
            row.locked_until = None

        account_label = f"{issuer}:{username_text}"
        secret = generate_totp_secret()
        mfa = db.scalar(select(SuperAdminMfa).where(SuperAdminMfa.admin_id == row.id))
        if mfa is None:
            mfa = SuperAdminMfa(
                admin_id=row.id,
                totp_secret=secret,
                issuer=issuer,
                account_label=account_label,
                is_enabled=True,
            )
            db.add(mfa)
        else:
            mfa.totp_secret = secret
            mfa.issuer = issuer
            mfa.account_label = account_label
            mfa.is_enabled = True

        old_codes = db.scalars(select(SuperAdminRecoveryCode).where(SuperAdminRecoveryCode.admin_id == row.id)).all()
        for item in old_codes:
            db.delete(item)

        recovery_codes = generate_recovery_codes(8)
        for code in recovery_codes:
            db.add(
                SuperAdminRecoveryCode(
                    admin_id=row.id,
                    code_hash=hash_recovery_code(code),
                    is_used=False,
                )
            )
        db.commit()

    uri = build_totp_provisioning_uri(secret=secret, account_name=username_text, issuer=issuer)
    print(f"super_admin_username={username_text}")
    print(f"totp_secret={secret}")
    print(f"totp_uri={uri}")
    print("recovery_codes=" + ",".join(recovery_codes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="root")
    parser.add_argument("--display-name", default="超级管理员")
    parser.add_argument("--password", required=True)
    parser.add_argument("--issuer", default="JGSDSC Supply Chain")
    args = parser.parse_args()
    bootstrap_super_admin(
        username=args.username,
        display_name=args.display_name,
        password=args.password,
        issuer=args.issuer,
    )
