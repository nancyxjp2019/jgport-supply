# 新项目重建基座

## 1. 基座目标
- 复用当前 V5 业务内核与规则文档。
- 后台前端切换为 `Vue 3 + Element Plus + Vben Admin`。
- 数据库主引擎切换为 `PostgreSQL`（推荐 `18`，截至 2026-03-05 为最新主版本）。
- 项目开发 Python 环境统一为 `Conda` 环境 `jgport`。
- 不包含 UAT 相关代码；历史文档中的 UAT 章节仅作归档参考，不作为新项目实现基线。

## 2. 目录结构
- `docs/`：业务规则、状态机、接口、数据库、安全、部署与对齐报告
- `backend/`：后端业务代码、数据库迁移与初始化脚本
- `admin-web/`：后台前端工程（已基于 `Vben Admin v5.6.0` 初始化，默认使用 `Element Plus`）
- `miniprogram/`：小程序执行链基座（已移除 UAT 运行器）

## 3. 建议启动顺序
1. 先激活 `Conda` 环境 `jgport`，启动 `backend` 并完成 PostgreSQL 迁移。
2. 再启动 `admin-web`（Vben）并对接 OpenAPI。
3. 最后按角色链路联调 `miniprogram`。

## 4. admin-web 启动命令
```bash
cd admin-web
corepack enable
corepack pnpm install
corepack pnpm run dev:ele --host 0.0.0.0 --port 5666
```

访问地址：`http://127.0.0.1:5666`
