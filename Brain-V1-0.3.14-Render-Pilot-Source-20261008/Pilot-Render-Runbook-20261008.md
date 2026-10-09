# Brain V1 0.3.14 — Render Pilot 运行手册（待 Owner 决策）

## 当前状态

- 尚未连接 Git 源、创建 Render 服务或部署。
- `render.yaml` 只是一份单实例/1GB 持久盘配置模板；`PILOT_LIVE_ENABLED=0`，真实调用保持关闭。
- 未设置百炼 Secret、未生成邀请码、未调用 API。
- 冻结规则与 Prompt 未修改；离线 Python 测试 240/240 PASS，Runtime-Manifest 39/39 PASS。

## 打开 Pilot 前必须确认

1. 预算口径已按 Owner 确认：本次最多新增 ¥8，计入原 ¥20 总预算。历史账本已累计估算 ¥10.818338、PENDING 0；满额后累计约 ¥18.818338，余 ¥1.181662。平台模板已写入 ¥8 Pilot cap 与 ¥20 overall cap。
2. Owner 已确认采用短期窗口运行的最低可行付费方案：Starter Web Service + 1GB 持久盘。约 $7.25/月（约 ¥49/月），运行一天约 ¥1.6；按实际时长折算，最终费用以平台账单为准。Hobby 工作区本身为 $0/月。免费服务不能挂持久盘，不适用于本项目真实 Pilot。
3. 明确 Pilot 结束时间（北京时间，含时区）。结束后应导出核对数据并停止付费服务，避免窗口外继续计费；应用会拒绝截止后的回答/微体验，但这本身不会停止 Render 服务。
4. Owner 提供可安全授权的 Render Workspace 与 Git 部署源。该工作副本当前没有 Git 元数据；不会自动创建公开仓库或把代码上传第三方。

## Owner 授权后执行顺序

1. 由 Owner 在已授权 Render Workspace 连接批准的私有 Git 源，读取 `render.yaml` 建立服务；部署前再次核对 Pilot 总预算和结束时间。
2. 在 Render Secret 页面设置 `DASHSCOPE_API_KEY`。Key 不进入仓库、聊天、报告或普通环境变量截图。
3. 首次部署继续保持 `PILOT_LIVE_ENABLED=0`，只验证 HTTPS 子域名、健康检查、持久盘路径及页面展示；不得提交答案或触发模型调用。
4. 检查 closed preview、持久卷重启后数据保留、服务日志不泄露密钥，并由 Owner 明确确认正式窗口与预算后，才能单独开启 Live Pilot。
5. Live 开启前完成平台 Shell 内账本预检：累计基线与 Owner 原账本一致、无 PENDING、授权未使用；初始化仅写一条历史金额/调用数 aggregate baseline，不搬运原始调用或回答。
6. 生成邀请码仅使用服务 Shell 中受限的 `python pilot_admin.py invite --hours <小时数>`。最多发出 3 份邀请；邀请码通过 Owner 选定的安全私密渠道单独发给 3 名受邀学生。
7. 达到预算、出现错误/PENDING、超过截止时间或人数达到 3 时停止；不自动重试、不扩大范围。体验结束后由 Owner 关闭服务并导出报告/数据。

## 尚不可执行项

当前不得将 `PILOT_LIVE_ENABLED` 改为 `1`，不得填写真实 Key 或发邀请码。Pilot 结束时间仍未确认，也尚无可连接的私有 Git 部署源/Render 授权。确认这两项后，可先创建默认关闭的服务并做闭合预览，再由 Owner 配置 Secret、完成账本预检并依授权窗口开启 Live。
