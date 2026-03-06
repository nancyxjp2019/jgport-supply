# V6 小程序工程

## 当前状态
- `miniprogram/` 已完成最小工程初始化，可直接在微信开发者工具中打开。
- 当前已落地页面：`MINI-REPORT-01 经营快报`。
- 当前运行模式：仅支持 `演示模式`，用于页面评审与交互确认。
- V5 小程序代码已归档至 `archive/v5/miniprogram/`，仅作为结构参考。

## 当前目录说明
- `app.js / app.json / app.wxss`：小程序应用入口与全局样式。
- `pages/report/`：`MINI-REPORT-01` 轻量报表页。
- `config/env.js`：运行模式与演示角色配置。
- `mocks/report.js`：演示模式报表数据。
- `utils/`：请求、格式化、轻量报表纯函数。
- `tests/`：Node 纯函数测试。

## 当前能力边界
- 首版仅开放：运营、财务、管理员（小程序）。
- 客户、供应商、仓库不展示经营金额汇总，只显示禁止访问提示。
- 当前不包含：微信登录、真实联调、业务看板独立页、订单/待办/执行页面。

## 打开方式
1. 使用微信开发者工具打开仓库下的 `miniprogram/`。
2. 项目 `appid` 当前为 `touristappid`，用于本地评审。
3. 默认进入 `pages/report/index`，直接预览 `经营快报` 页面。

## 本地回归命令
```bash
node --check app.js config/env.js utils/api.js utils/format.js utils/light-report.js utils/request.js pages/report/index.js
node --test tests/*.test.js
```

## 后续计划
1. `M8-03` 接入微信登录与身份透传链路。
2. 在真实登录链路稳定后，再开放小程序更多业务页面。
