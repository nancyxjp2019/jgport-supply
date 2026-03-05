import argparse
from pathlib import Path
from urllib.parse import quote


def build_totp_uri(secret: str, account: str, issuer: str) -> str:
    issuer_text = issuer.strip()
    account_text = account.strip()
    label = f"{issuer_text}:{account_text}"
    return (
        f"otpauth://totp/{quote(label, safe=':')}"
        f"?secret={secret.strip()}&issuer={quote(issuer_text)}&algorithm=SHA1&digits=6&period=30"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="将 SUPER_ADMIN 的 TOTP 信息生成 Microsoft Authenticator 可扫码二维码")
    parser.add_argument("--totp-uri", help="完整 otpauth://totp/... 链接")
    parser.add_argument("--secret", help="TOTP 密钥（与 --totp-uri 二选一）")
    parser.add_argument("--account", default="root", help="账号名，仅在使用 --secret 时生效")
    parser.add_argument("--issuer", default="JGSDSC Supply Chain", help="签发方，仅在使用 --secret 时生效")
    parser.add_argument("--output", default="../deploy/super_admin_totp_qr.png", help="二维码输出路径")
    args = parser.parse_args()

    if not args.totp_uri and not args.secret:
        raise SystemExit("请传入 --totp-uri 或 --secret")

    if args.totp_uri and args.secret:
        raise SystemExit("--totp-uri 与 --secret 只能传一个")

    try:
        import qrcode
    except ImportError as exc:
        raise SystemExit("缺少依赖 qrcode，请先执行：pip install qrcode[pil]") from exc

    totp_uri = args.totp_uri.strip() if args.totp_uri else build_totp_uri(args.secret, args.account, args.issuer)
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = qrcode.make(totp_uri)
    image.save(output_path)

    print(f"totp_uri={totp_uri}")
    print(f"qr_path={output_path.resolve()}")


if __name__ == "__main__":
    main()
