from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "message": "请求参数校验失败",
                "detail": [
                    {
                        "loc": list(error.get("loc", ())),
                        "msg": _translate_validation_message(error),
                        "type": error.get("type", "validation_error"),
                    }
                    for error in exc.errors()
                ],
            },
        )


def _translate_validation_message(error: dict) -> str:
    error_type = error.get("type")
    ctx = error.get("ctx") or {}
    raw_message = error.get("msg", "请求参数不合法")

    if error_type == "missing":
        return "字段必填"
    if error_type == "greater_than":
        return f"值必须大于 {ctx.get('gt')}"
    if error_type == "greater_than_equal":
        return f"值必须大于等于 {ctx.get('ge')}"
    if error_type == "less_than":
        return f"值必须小于 {ctx.get('lt')}"
    if error_type == "less_than_equal":
        return f"值必须小于等于 {ctx.get('le')}"
    if error_type == "string_too_short":
        return f"长度不能少于 {ctx.get('min_length')} 个字符"
    if error_type == "string_too_long":
        return f"长度不能超过 {ctx.get('max_length')} 个字符"
    if error_type == "string_pattern_mismatch":
        return "格式不正确"
    if error_type == "list_too_short":
        return f"列表元素数量不能少于 {ctx.get('min_length')} 个"
    if error_type == "list_too_long":
        return f"列表元素数量不能超过 {ctx.get('max_length')} 个"
    if raw_message.startswith("Value error, "):
        return raw_message.replace("Value error, ", "", 1)
    if raw_message.startswith("Assertion failed, "):
        return raw_message.replace("Assertion failed, ", "", 1)
    if _contains_chinese(raw_message):
        return raw_message
    return "请求参数不合法"


def _contains_chinese(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)
