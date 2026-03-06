# V6 小程序工程

## 当前状态
- `miniprogram/` 已完成最小工程初始化，可直接在微信开发者工具中打开。
- 当前已落地页面：`MINI-LOGIN-01 本地登录`、`MINI-REPORT-01 经营快报`。
- 当前运行模式：支持 `演示模式` 与 `本地联调`。
- V5 小程序代码已归档至 `archive/v5/miniprogram/`，仅作为结构参考。

## 当前目录说明
- `app.js / app.json / app.wxss`：小程序应用入口与全局样式。
- `pages/login/`：`MINI-LOGIN-01` 本地登录页。
- `pages/report/`：`MINI-REPORT-01` 轻量报表页。
- `config/env.js`：运行模式与演示角色配置。
- `mocks/report.js`：演示模式报表数据。
- `utils/`：请求、格式化、轻量报表纯函数、本地会话工具。
- `tests/`：Node 纯函数测试。

## 当前能力边界
- 首版仅开放：运营、财务、管理员（小程序）。
- 客户、供应商、仓库不展示经营金额汇总，只显示禁止访问提示。
- 当前已包含：本地登录、角色切换、报表页登录守卫、开发者工具本地后端联调。
- 当前不包含：微信登录、真机 HTTPS 联调、业务看板独立页、订单/待办/执行页面。

## 打开方式
1. 使用微信开发者工具打开仓库下的 `miniprogram/`。
2. 项目 `appid` 以本地开发者工具已绑定配置为准；仓库默认配置仅作为占位基线。
3. 默认进入 `pages/login/index`，先选择运行模式与角色，再进入 `经营快报` 页面。
4. `演示模式` 用于纯页面评审；`本地联调` 会访问本机后端，默认地址为 `http://127.0.0.1:8000/api/v1`。
5. 运营、财务、管理员可查看经营快报；客户、供应商、仓库用于验证中文阻断提示。
6. 若需要本地联调，请先启动后端，并保持微信开发者工具项目开启“开发环境不校验请求域名/TLS”一类本地调试能力。

## 本地回归命令
```bash
node --check app.js config/env.js utils/api.js utils/format.js utils/light-report.js utils/request.js utils/session.js pages/login/index.js pages/report/index.js
node --test tests/*.test.js
```

## 后续计划
1. 在提供微信侧联调条件后接入真实微信登录与身份透传。
2. 在真实登录链路稳定后，再开放小程序更多业务页面。
