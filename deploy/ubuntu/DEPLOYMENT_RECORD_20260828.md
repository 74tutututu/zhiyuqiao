# 智语桥云端部署验收记录（2026-08-28）

## 部署基线

- 平台：阿里云 ECS，华东 2（上海）
- 系统：Ubuntu 24.04 LTS，2 vCPU / 2 GiB，40 GiB 系统盘
- 内存保护：2 GiB Swap，已写入 `/etc/fstab`
- 应用版本：`main` 分支提交 `b2fbed9`
- 部署目录：`/srv/zhiyuqiao`
- 运行身份：独立低权限账户 `zhiyuqiao`
- 应用进程：systemd 托管，仅监听 `127.0.0.1:7860`
- 公网入口：Nginx 监听 80 端口并反向代理应用
- 数据：SQLite 文件权限为 `600`，数据库目录权限为 `700`
- 密钥：应用密钥仅保存在服务器 `.env`，未写入 Git 仓库

## 验收结果

- `/health` 与 `/health/ready` 均返回 HTTP 200。
- 知识库可检索资料数为 16,118 条。
- 注册页同时提供“中文学习者”和“中文教师”两类身份。
- 学生账号注册后进入学生工作台；教师账号注册后进入教师工作台。
- 教师访问学生工作台时会被重定向回教师工作台，角色隔离有效。
- 学生端“杨浦滨江中文观察任务”生成成功，引用上海市政府公开来源。
- 教师端“杨浦滨江工业遗产 HSK 3 口语任务”生成并保存草稿成功。
- 页面样式、静态资源、中文文案与浏览器控制台均无异常。
- `test_minimal_launch.py`、`test_role_security.py`、`test_learning_workflow.py` 在服务器运行通过。
- systemd 重启后应用能自动恢复，Nginx 与应用端口监听符合预期。

验收使用的临时学生、教师账号及其会话、任务和草稿已经删除；删除前已在服务器本地生成数据库备份。备份不进入 Git 仓库。

## 当前边界

目前是 HTTP 公网阶段，适合演示与继续开发。正式收集真实用户资料前，应先绑定域名、申请 HTTPS 证书，并把安全 Cookie 配置切换为开启状态。

向量索引文件未纳入 Git，线上目前使用 TF-IDF 回退检索；功能与来源引用正常。后续如需提升语义召回，可在服务器单独生成或安全同步向量索引。

## 日常检查

```bash
sudo systemctl status zhiyuqiao --no-pager
sudo systemctl status nginx --no-pager
curl -fsS http://127.0.0.1:7860/health/ready
sudo journalctl -u zhiyuqiao -n 100 --no-pager
```

更新、备份与回滚流程见同目录的 `README.md`。
