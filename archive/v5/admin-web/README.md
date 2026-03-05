# 管理后台前端（Vue 3 + Element Plus + Vben Admin）

## 1. 当前状态
- 已基于 `Vben Admin v5.6.0` 初始化。
- 默认使用 `Element Plus` 方案（应用：`@vben/web-ele`）。
- 本工程目录为 Monorepo 结构，按 Vben 官方工作区组织。

## 2. 环境要求
- Node.js：建议 `22.22.0`（模板内 `.node-version`）
- 包管理器：`pnpm`（通过 `corepack` 使用）

## 3. 安装依赖
```bash
cd admin-web
corepack enable
corepack pnpm install
```

## 4. 启动开发服务（Element Plus）
```bash
cd admin-web
corepack pnpm run dev:ele --host 0.0.0.0 --port 5666
```

访问地址：`http://127.0.0.1:5666`

## 5. 常用命令
```bash
# 构建 Element Plus 版本
corepack pnpm run build:ele

# 启动 Ant Design Vue 版本（可选）
corepack pnpm run dev:antd

# 启动 Naive UI 版本（可选）
corepack pnpm run dev:naive
```

## 6. 对接后端要求
- API 前缀：`/api/v1`
- 鉴权：Bearer Token（JWT）
- 权限策略：前端仅做界面控制，最终以后端鉴权为准

## 7. 参考资料
- Vben 官方文档：`https://doc.vben.pro`
- Vben 官方仓库：`https://github.com/vbenjs/vue-vben-admin`
