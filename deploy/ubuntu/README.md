# Ubuntu 部署说明

这套模板默认先按“公网 IP 可访问”部署，等你后续决定域名后，再切到域名和 HTTPS。

## 方案建议

- 如果你现在只想尽快上线：先用 `deploy/ubuntu/nginx-ip.conf`
- 如果你已经有域名：改用 `deploy/ubuntu/nginx-domain.conf`，再接 `certbot`

两种方案都使用同一套应用代码与 `systemd` 服务，不需要改 Python 代码。

## 1. 放置代码

建议项目目录：

```bash
/home/admin/zhiyuqiao
```

把当前仓库同步到服务器后，进入项目目录：

```bash
cd /home/admin/zhiyuqiao
```

## 2. 安装运行环境

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nginx

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
```

## 3. 配置 `.env`

可以参考 `deploy/ubuntu/server.env.example`：

```bash
cp deploy/ubuntu/server.env.example .env
```

至少需要填写：

- `DEEPSEEK_API_KEY`

推荐部署参数：

- `APP_SERVER_NAME=127.0.0.1`
- `APP_SERVER_PORT=7860`

这样应用只监听本机，由 Nginx 对外提供访问入口。

如果你使用 PostgreSQL，记得同时在 `.env` 中补上：

- `DATABASE_URL=postgresql+psycopg://用户名:密码@127.0.0.1:5432/数据库名`

保护配置文件，并确认它没有进入 Git：

```bash
chmod 600 .env
git status --short
```

若当前只用公网 IP + HTTP 做短期验收，`ZHIYUQIAO_SECURE_COOKIES=0`；域名 HTTPS 生效后必须改为 `1`。HTTP 阶段不要录入真实学习者、访谈或教学数据。

## 4. 配置 `systemd`

复制模板并替换占位符：

```bash
cp deploy/ubuntu/zhiyuqiao.service /tmp/zhiyuqiao.service
sed -i 's|__APP_USER__|admin|g' /tmp/zhiyuqiao.service
sed -i 's|__APP_DIR__|/home/admin/zhiyuqiao|g' /tmp/zhiyuqiao.service
sudo cp /tmp/zhiyuqiao.service /etc/systemd/system/zhiyuqiao.service
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zhiyuqiao
sudo systemctl status zhiyuqiao -l
```

确认应用和数据库、知识目录都已就绪：

```bash
curl --fail http://127.0.0.1:7860/health/ready
```

### 可选：启用语义向量检索

2GB 内存服务器不要在线重建全部索引。先在开发机运行 `scripts/migrate_to_vectors.py --reset`；单独更新海派文化资料时可运行 `scripts/migrate_to_vectors.py --domain haipai`。然后把生成的 Chroma 目录和同一嵌入模型安全同步到服务器。服务器只安装 CPU 查询运行时：

```bash
source .venv/bin/activate
pip install -r requirements-vector.txt
```

在 `.env` 中分别设置服务器上的索引与模型绝对路径：

```dotenv
ZHIYUQIAO_VECTOR_DB_DIR=/srv/zhiyuqiao/data/vectors
ZHIYUQIAO_EMBEDDING_MODEL=/srv/zhiyuqiao/models/paraphrase-multilingual-MiniLM-L12-v2
ZHIYUQIAO_EMBEDDING_BACKEND=onnx
ZHIYUQIAO_EMBEDDING_ONNX_FILE=onnx/model_int8_avx2.onnx
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
ZHIYUQIAO_VECTOR_WARMUP=1
```

2GB CPU 服务器应在开发机提前导出 ONNX INT8 文件，再把成品放入模型目录的 `onnx/` 子目录。不要在生产服务器启动时执行 PyTorch 动态量化，否则转换峰值可能触发 Swap 抖动。

同步完成后先执行离线验收，再重启网站：

```bash
python scripts/verify_vector_index.py
sudo systemctl restart zhiyuqiao
```

向量组件不可用时，应用仍会自动降级到 TF-IDF，不会阻断网站启动。

查看日志：

```bash
sudo journalctl -u zhiyuqiao -f
```

## 5. 先用公网 IP 上线

启用 IP 版 Nginx 配置：

```bash
sudo cp deploy/ubuntu/nginx-ip.conf /etc/nginx/sites-available/zhiyuqiao
sudo ln -sf /etc/nginx/sites-available/zhiyuqiao /etc/nginx/sites-enabled/zhiyuqiao
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

浏览器访问：

```text
http://你的公网IP/
```

如果打不开，通常只需要检查云平台安全组是否放行：

- `80/tcp`

SSH 的 `22/tcp` 只建议向维护者固定公网 IP 开放，不要向所有地址长期开放。

## 6. 以后切换到域名

把域名解析到服务器公网 IP 后：

```bash
cp deploy/ubuntu/nginx-domain.conf /tmp/zhiyuqiao-nginx.conf
sed -i 's|__SERVER_NAME__|your-domain.com|g' /tmp/zhiyuqiao-nginx.conf
sudo cp /tmp/zhiyuqiao-nginx.conf /etc/nginx/sites-available/zhiyuqiao
sudo nginx -t
sudo systemctl reload nginx
```

然后签发 HTTPS 证书：

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

证书生效后，把 `.env` 中 `ZHIYUQIAO_SECURE_COOKIES` 改为 `1` 并重启服务。安全组再放行 `443/tcp`，确认 HTTPS 正常后可让 80 端口只负责跳转。

完成后访问：

```text
https://your-domain.com/
```

## 7. 更新代码后的重启方式

```bash
cd /home/admin/zhiyuqiao

# 更新前备份。SQLite 默认路径如下；PostgreSQL 请改用 pg_dump。
mkdir -p backups
if [ -f database/zhiyuqiao_dev.sqlite3 ]; then cp database/zhiyuqiao_dev.sqlite3 "backups/zhiyuqiao-$(date +%Y%m%d-%H%M%S).sqlite3"; fi

git fetch origin
git pull --ff-only origin main
source .venv/bin/activate
pip install -r requirements-web.txt
sudo systemctl restart zhiyuqiao
sudo journalctl -u zhiyuqiao -n 50 --no-pager
curl --fail http://127.0.0.1:7860/health/ready
```

如果健康检查失败，先查看日志，不要反复覆盖数据库。确认需要回滚代码时，切回更新前记录的提交，重新安装 `requirements-web.txt` 并重启；数据恢复则只使用刚才生成的备份副本。

## 8. 上线验收清单

- `/health/ready` 返回 `status: ready`
- 学生和教师分别登录后只进入自己的工作台
- 学生流式回答、停止生成、保存任务、完成反思与进度更新正常
- 教师保存教案、编辑、标记已审核、下载 Markdown、打印 PDF 正常
- 海派文化回答显示与主题一致的官方来源卡片
- HTTPS 下登录、退出、账号设置和注销流程正常
- `.env`、数据库、原始调研材料不在公开仓库中
