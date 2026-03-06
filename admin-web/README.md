# V6 管理后台工程

## 当前状态
- `M8` 首批已开始落地管理后台工程骨架。
- 技术基线：`Vue 3 + Vite + TypeScript + Element Plus`。
- 工程组织：布局、路由、权限与页面分层对齐 `Vben Admin` 思路，不直接整仓引入上游 Monorepo 模板。
- V5 后台代码已归档至 `archive/v5/admin-web/`。

## 已落地范围
1. 管理后台前端工程初始化。
2. `M7` 首批页面：仪表盘、业务看板。
3. 演示数据模式与代理联调模式切换。
4. 管理后台登录页、路由守卫与代理身份读取。

## 本地启动
```bash
cd admin-web
pnpm install
pnpm dev
```

## 环境变量
- `VITE_REPORTS_MODE`：`demo` 或 `proxy`
- `BACKEND_API_BASE_URL`：后端接口地址，默认 `http://127.0.0.1:8000/api/v1`
- `BACKEND_AUTH_SECRET`：仅供 Vite 开发代理注入到后端请求头，禁止放入浏览器端公开变量

## 下一步建议
1. 补小程序真实微信登录与身份透传。
2. 按模块迁移合同、订单、资金、库存页面。
3. 再补按钮级权限和真实会话续期能力。
