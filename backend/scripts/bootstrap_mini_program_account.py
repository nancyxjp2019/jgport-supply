from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.mini_program_account import MiniProgramAccount
from app.models.role_company_binding import RoleCompanyBinding


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="绑定或更新小程序微信账号与业务角色")
    parser.add_argument("--openid", required=True, help="微信 openid")
    parser.add_argument("--role-code", required=True, help="业务角色编码")
    parser.add_argument("--company-id", required=True, help="归属公司 ID")
    parser.add_argument("--company-type", required=True, help="归属公司类型")
    parser.add_argument("--display-name", default="", help="显示名称")
    parser.add_argument("--unionid", default="", help="微信 unionid，可选")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        binding = db.scalar(
            select(RoleCompanyBinding).where(
                RoleCompanyBinding.role_code == args.role_code,
                RoleCompanyBinding.company_type == args.company_type,
                RoleCompanyBinding.status == "生效",
                RoleCompanyBinding.is_active.is_(True),
            )
        )
        if binding is None or not bool(binding.miniprogram_allowed):
            raise SystemExit("当前角色与公司归属未开放小程序访问，禁止绑定")

        account = db.scalar(select(MiniProgramAccount).where(MiniProgramAccount.openid == args.openid))
        if account is None:
            account = MiniProgramAccount(
                openid=args.openid,
                unionid=args.unionid or None,
                role_code=args.role_code,
                company_id=args.company_id,
                company_type=args.company_type,
                display_name=args.display_name or None,
            )
            db.add(account)
            action = "创建"
        else:
            account.unionid = args.unionid or None
            account.role_code = args.role_code
            account.company_id = args.company_id
            account.company_type = args.company_type
            account.display_name = args.display_name or None
            account.status = "生效"
            account.is_active = True
            action = "更新"

        db.commit()
        print(f"{action}小程序微信账号绑定成功：openid={args.openid} role={args.role_code} company={args.company_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
