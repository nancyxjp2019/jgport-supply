# V6 小程序工程

## 当前状态
- `miniprogram/` 已完成最小工程初始化，可直接在微信开发者工具中打开。
- 当前已落地页面：`MINI-LOGIN-01 登录入口`、`MINI-REPORT-01 经营快报`、`MINI-EXEC-01 仓库执行回执`。
- 当前运行模式：支持 `演示模式`、`本地联调`、`微信登录`。
- V5 小程序代码已归档至 `archive/v5/miniprogram/`，仅作为结构参考。

## 当前目录说明
- `app.js / app.json / app.wxss`：小程序应用入口与全局样式。
- `pages/login/`：`MINI-LOGIN-01` 登录入口页。
- `pages/report/`：`MINI-REPORT-01` 轻量报表页。
- `pages/exec/`：`MINI-EXEC-01` 仓库执行回执页。
- `config/env.js`：运行模式与演示角色配置。
- `mocks/report.js`：演示模式报表数据。
- `utils/`：请求、格式化、轻量报表纯函数、本地会话工具。
- `tests/`：Node 纯函数测试。

## 当前能力边界
- 首版已开放：运营、财务、管理员（轻量报表）与仓库（执行回执）。
- 客户、供应商不展示经营金额汇总，只显示禁止访问提示。
- 当前已包含：登录入口、角色切换、报表页登录守卫、仓库执行回执页、开发者工具本地后端联调、微信登录骨架。
- 当前不包含：真机 HTTPS 联调、业务看板独立页、客户订单页、消息中心。

## 打开方式
1. 使用微信开发者工具打开仓库下的 `miniprogram/`。
2. 项目 `appid` 以本地开发者工具已绑定配置为准；仓库默认配置仅作为占位基线。
3. 默认进入 `pages/login/index`，先选择运行模式与角色；仓库角色默认进入 `仓库执行回执`，其他已实现角色默认进入 `经营快报`。
4. `演示模式` 用于纯页面评审；`本地联调` 会访问本机后端，默认地址为 `http://127.0.0.1:8000/api/v1`；`微信登录` 会先调用 `wx.login`，再由后端执行 `code2session`。
5. 运营、财务、管理员可查看经营快报；仓库角色可进入执行回执页；客户、供应商仍用于验证当前已开放页面的中文阻断提示。
6. 若需要本地联调或微信登录，请先启动后端，并保持微信开发者工具项目开启“开发环境不校验请求域名/TLS”一类本地调试能力。
7. 首次微信登录若提示“未绑定业务角色”，可在开发环境读取 `debug_openid`，再执行 `cd backend && python scripts/bootstrap_mini_program_account.py ...` 完成绑定。

## 本地回归命令
```bash
node --check app.js config/env.js utils/api.js utils/format.js utils/light-report.js utils/navigation.js utils/request.js utils/session.js utils/warehouse-exec.js pages/login/index.js pages/report/index.js pages/exec/index.js
node --test tests/*.test.js
```

## 后续计划
1. 在补充 `AppSecret` 与实际微信账号绑定后完成真实微信登录联调。
2. 在真实登录链路稳定后，再开放客户订单页、消息中心与待办页。
