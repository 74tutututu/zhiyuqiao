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
pip install -r requirements.txt
```

## 3. 配置 `.env`

可以参考 `deploy/ubuntu/server.env.example`：

```bash
cp deploy/ubuntu/server.env.example .env
```

至少需要填写：

- `DEEPSEEK_API_KEY`

推荐部署参数：

- `GRADIO_SERVER_NAME=127.0.0.1`
- `GRADIO_SERVER_PORT=7860`

这样应用只监听本机，由 Nginx 对外提供访问入口。

如果你使用 PostgreSQL，记得同时在 `.env` 中补上：

- `DATABASE_URL=postgresql+psycopg://用户名:密码@127.0.0.1:5432/数据库名`

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

完成后访问：

```text
https://your-domain.com/
```

## 7. 更新代码后的重启方式

```bash
cd /home/admin/zhiyuqiao
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart zhiyuqiao
sudo journalctl -u zhiyuqiao -n 50 --no-pager
```
