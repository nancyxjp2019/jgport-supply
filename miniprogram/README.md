# V6 小程序工程

## 当前状态
- `miniprogram/` 已完成最小工程初始化，可直接在微信开发者工具中打开。
- 当前已落地页面：`MINI-LOGIN-01 登录入口`、`MINI-TODO-01 我的待办`、`MINI-MSG-01 消息中心`、`MINI-ORDER-01 订单发起与查询`、`MINI-REPORT-01 经营快报`、`MINI-EXEC-01 仓库执行回执`、`MINI-SUPPLIER-PO-01 供应商采购进度、附件回传与发货确认`。
- 当前已补齐：`消息中心 -> 业务页` 的来源回看与深链一致性首批能力。
- 当前运行模式：支持 `演示模式`、`本地联调`、`微信登录`。
- V5 小程序代码已归档至 `archive/v5/miniprogram/`，仅作为结构参考。

## 当前目录说明
- `app.js / app.json / app.wxss`：小程序应用入口与全局样式。
- `pages/login/`：`MINI-LOGIN-01` 登录入口页。
- `pages/todo/`：`MINI-TODO-01` 我的待办页。
- `pages/msg/`：`MINI-MSG-01` 消息中心页。
- `pages/order/`：`MINI-ORDER-01` 订单发起与查询页。
- `pages/report/`：`MINI-REPORT-01` 轻量报表页。
- `pages/exec/`：`MINI-EXEC-01` 仓库执行回执页。
- `pages/supplier-purchase/`：`MINI-SUPPLIER-PO-01` 供应商采购进度页。
- `config/env.js`：运行模式与演示角色配置。
- `mocks/report.js`：演示模式报表数据。
- `utils/`：请求、格式化、轻量报表纯函数、本地会话工具。
- `tests/`：Node 纯函数测试。

## 当前能力边界
- 首版已开放：客户（订单发起与查询）、运营/财务/管理员（轻量报表）、仓库（执行回执）、供应商（采购进度查看、附件回传与单笔发货确认）。
- 供应商不展示经营金额汇总，仅开放采购订单进度、发货准备信息回看、首批业务附件回传与单笔发货确认。
- 当前已包含：登录入口、待办页、消息中心、客户订单页、报表页登录守卫、仓库执行回执页、供应商采购进度页、供应商附件路径登记与摘要回看、供应商单笔发货确认、消息来源回看提示、统一深链跳转、开发者工具本地后端联调、微信登录骨架。
- 当前不包含：真机 HTTPS 联调、业务看板独立页、供应商付款确认、异常关闭与批量处理、二进制文件直传、服务端消息推送。

## 打开方式
1. 使用微信开发者工具打开仓库下的 `miniprogram/`。
2. 项目 `appid` 以本地开发者工具已绑定配置为准；仓库默认配置仅作为占位基线。
3. 默认进入 `pages/login/index`，先选择运行模式与角色；登录后统一进入 `我的待办`，再按角色进入订单、快报或执行入口。
4. `演示模式` 用于纯页面评审；`本地联调` 会访问本机后端，默认地址为 `http://127.0.0.1:8000/api/v1`；`微信登录` 会先调用 `wx.login`，再由后端执行 `code2session`。
5. 客户角色可进入订单页并发起/查询订单；运营、财务、管理员可查看经营快报；仓库角色可进入执行回执页；供应商可进入采购进度页查看真实采购订单进度、登记首批业务附件路径，并在待供应商确认状态下提交单笔发货确认。
6. 若需要本地联调或微信登录，请先启动后端，并保持微信开发者工具项目开启“开发环境不校验请求域名/TLS”一类本地调试能力。
7. 首次微信登录若提示“未绑定业务角色”，可在开发环境读取 `debug_openid`，再执行 `cd backend && python scripts/bootstrap_mini_program_account.py ...` 完成绑定。

## 本地回归命令
```bash
node --check app.js config/env.js mocks/order.js utils/api.js utils/format.js utils/light-report.js utils/message.js utils/navigation.js utils/order.js utils/request.js utils/session.js utils/supplier-purchase.js utils/todo.js utils/warehouse-exec.js pages/login/index.js pages/todo/index.js pages/msg/index.js pages/order/index.js pages/report/index.js pages/exec/index.js pages/supplier-purchase/index.js
node --test tests/*.test.js
```

## 后续计划
1. 在补充 `AppSecret` 与实际微信账号绑定后完成真实微信登录联调。
2. 在真实登录链路稳定后，继续补消息推送与供应商真实业务待办。
3. 在供应商确认发货首批能力稳定后，继续评估付款校验结果回看、异常关闭与后续执行链提示。
