# JGPort V6 重建工作区

## 1. 当前状态
- 本仓库已切换到 **V6 重建模式**。
- 历史 V5 代码与文档已归档至 `archive/v5/`，用于追溯与参考，不再作为 V6 默认开发目录。
- V6 默认开发目录：`backend/`、`admin-web/`、`miniprogram/`、`docs/`。
- 当前已完成：`M1~M7` 后端与报表首批能力，`M8-01` 管理后台基座与报表页首批能力，`M8-02` 小程序轻量报表页，`M8-03` 管理后台登录与身份透传首批能力，`M8-04` 小程序本地登录与角色切换能力，`M8-05` 小程序开发者工具本地后端联调模式，`M8-06` 微信登录与 `code2session` 骨架，`M8-07` 仓库执行回执页，`M8-08` 客户订单发起与查询页，`M8-09` 小程序待办入口首批，`M8-10` 小程序消息中心首批，`M8-11` 消息来源页回看与深链一致性首批能力，`M8-12` 供应商采购进度首批能力，`M8-13` 供应商附件回传首批能力，`M8-14` 供应商发货确认首批能力，`M8-15` 供应商付款校验结果回看首批能力。

## 2. 目录说明
- `backend/`：V6 后端工程（FastAPI + PostgreSQL 18）
- `admin-web/`：V6 管理后台工程（Vue 3 + Element Plus，工程组织对齐 Vben Admin）
- `miniprogram/`：V6 小程序执行链工程
- `docs/`：V6 需求、方案、设计、迁移与联调文档
- `archive/v5/`：V5 归档区（只读参考，避免干扰 V6 开发）

## 3. 启动建议
1. 先启动 V6 后端并完成 PostgreSQL 迁移验证。
2. 再启动 V6 管理后台并对接 `/api/v1`。
3. 小程序当前已完成登录入口、待办入口、消息中心、客户订单页、轻量报表页、仓库执行回执页、供应商采购进度页、供应商附件回传、单笔发货确认与付款校验结果回看首批能力、消息来源页回看与深链一致性首批能力、开发者工具本地联调模式与微信登录骨架，可在微信开发者工具中切换演示模式、本地联调或微信登录模式。

## 4. 说明
- 已完成 V6 后端基座初始化（FastAPI + Alembic + PostgreSQL）。
- 当前已验证 `alembic upgrade head`、`pytest`、`/api/v1/healthz` 可用。

## 5. V6 后端快速启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
