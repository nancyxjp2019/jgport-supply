# 管理后台前端（Vue 3 + Element Plus + Vben Admin）

## 1. 目标
- 承接原 `backend/app/web/admin_console` 的后台管理能力。
- 使用 Vben Admin 工程体系重建菜单、权限、页面与 API 调用。

## 2. 初始化建议
1. 使用官方 Vben Admin 最新稳定模板初始化工程。
2. UI 框架统一选择 Element Plus。
3. 全量启用 TypeScript、ESLint、Prettier、路由权限守卫。

## 3. 必接后端配置
- API 基础地址：`/api/v1`
- 认证方式：Bearer Token（JWT）
- 关键模块：
  - 用户与公司主体
  - 模板中心
  - 合同、订单、采购入库、库存
  - 报表中心与审计日志

## 4. 安全要求
- 前端权限仅用于界面控制，最终权限以后端校验为准。
- 终止类动作必须二次确认并要求填写原因。
