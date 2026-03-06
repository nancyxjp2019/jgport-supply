# V6 新项目重建基座说明（Vue 3 + Element Plus + Vben Admin + PostgreSQL）

## 1. 目标
- 在 V5 业务口径基础上重建 V6。
- 后台前端统一使用 `Vue 3 + Element Plus`，工程组织、布局分层、路由与权限模式对齐 `Vben Admin`。
- 数据库统一基线为 `PostgreSQL 18`。
- V5 仅保留归档，不参与 V6 日常开发。

## 2. 当前目录策略
- V6 开发目录：仓库根下 `backend/`、`admin-web/`、`miniprogram/`、`docs/`
- V5 归档目录：`archive/v5/`

## 3. 阶段划分
1. 基座阶段：工程初始化、规范固化、环境打通（后端基座已完成）。
2. 迁移阶段：按业务域分批迁移并建立回归用例。
3. 收敛阶段：性能、审计、合规、部署与运维收口。

## 4. 开发准则
- 所有新增需求以 V6 目录为准。
- V5 只读参考，不作为合并目标。
- 业务规则变更必须同步更新 `docs/需求方案.md` 并标注状态。
- 官方 `Vben Admin` 当前以 Monorepo 模板方式提供；V6 仓库首批不直接整仓引入上游模板，而是在 `admin-web/` 内按其工程组织思想建立本地化骨架，避免一次性引入无关应用与包。

## 5. 当前进展（2026-03-05）
- 已完成 `backend/` 最小可运行基座：
  - FastAPI 应用入口与 `/api/v1/healthz`
  - SQLAlchemy 会话与 `business_logs` 模型
  - Alembic 首次迁移 `0001_init_v6_schema`
- 已完成验证：
  - `alembic upgrade head` 成功
  - `pytest` 成功
  - `uvicorn` 启动后健康检查返回 `{\"status\":\"ok\"}`
