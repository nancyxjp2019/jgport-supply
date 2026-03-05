# JGPort V6 重建工作区

## 1. 当前状态
- 本仓库已切换到 **V6 重建模式**。
- 历史 V5 代码与文档已归档至 `archive/v5/`，用于追溯与参考，不再作为 V6 默认开发目录。
- V6 默认开发目录：`backend/`、`admin-web/`、`miniprogram/`、`docs/`。

## 2. 目录说明
- `backend/`：V6 后端工程（FastAPI + PostgreSQL 18）
- `admin-web/`：V6 管理后台工程（Vue 3 + Element Plus + Vben Admin）
- `miniprogram/`：V6 小程序执行链工程
- `docs/`：V6 需求、方案、设计、迁移与联调文档
- `archive/v5/`：V5 归档区（只读参考，避免干扰 V6 开发）

## 3. 启动建议
1. 先完成 V6 后端工程初始化与 PostgreSQL 连接验证。
2. 再初始化 V6 管理后台并对接 `/api/v1`。
3. 最后迁移小程序关键链路并做联调回归。

## 4. 说明
- 本次调整只完成“目录隔离 + 基线文档落地”，尚未开始 V6 功能开发。
