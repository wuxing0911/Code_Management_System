# 项目代码版本管理系统

面向部门嵌入式开发的**最终可发布物**管理工具。开发完成可烧录/可交付文件后上传到服务器，测试人员按产品与版本下载使用。

## 项目说明

### 业务目标

- 统一管理部门各产品的软件版本发布物
- 以「产品 → 版本 → 文件」组织内容
- 支持程序代码与界面工程两类文件的上传、预览、下载与删除
- 支持本机开发运行，并可部署到阿里云 ECS 等服务器

### 主要功能

| 模块 | 说明 |
|------|------|
| 账号权限 | 管理员 / 开发 / 测试三角色；JWT 登录 |
| 产品管理 | 新建、编辑、删除产品；产品数 / 版本数预览 |
| 版本管理 | 新建、编辑、删除版本；多行备注展示 |
| 内容预览 | 文件树浏览，可进入子目录 |
| 上传 | 程序代码、界面工程（PKG / private 文件夹） |
| 下载 | 单文件、文件夹打包、勾选批量、整版本打包 |
| 删除 | 文件 / 文件夹删除；勾选批量删除（开发/管理员） |
| 导航 | 侧栏快捷切换产品；面包屑与返回上一页 |

### 文件类型约定

程序代码与界面工程放在**同一版本目录**下，通过「内容类型」区分：

| 类型 | 规则 |
|------|------|
| 程序代码 | 扩展名 `.bin` / `.hex` / `.LoP100` |
| 界面工程 | 单文件 `.PKG`；或文件夹名称为 `private` |

### 角色权限

| 角色 | 权限 |
|------|------|
| 管理员 | 用户管理、产品/版本管理、上传下载删除 |
| 开发 | 产品/版本管理、上传下载删除 |
| 测试 | 浏览与下载（不可上传、删除） |

### 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Element Plus + Vue Router |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 数据库 | SQLite（MVP，数据文件位于 `data/app.db`） |
| 文件存储 | 本地磁盘 `data/releases/` |
| 部署 | Docker Compose + Nginx |

### 目录结构

```text
项目代码版本管理系统/
├── backend/                 # FastAPI 后端
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vue3 前端
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── deploy/
│   └── docker-compose.yml   # 一键部署编排
├── data/
│   ├── app.db               # 运行后生成的数据库
│   └── releases/            # 版本文件存储（产品/版本/文件）
├── start-dev.sh             # 本机一键开发启动脚本
└── README.md
```

磁盘上的版本文件路径示例：

```text
data/releases/
  {product_slug}/
    {version_name}/
      xxx.bin
      xxx.hex
      xxx.LoP100
      xxx.PKG
      private/
        ...
```

---

## 本机开发运行

### 环境要求

- Python **3.11**（推荐；勿用过新的 3.14 以免依赖构建失败）
- Node.js 18+ / npm
- 可选：Docker（用于本地模拟线上部署）

### 方式一：脚本启动

```bash
chmod +x start-dev.sh
./start-dev.sh
```

### 方式二：分别启动

**后端**

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**前端**（另开终端）

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器打开：http://127.0.0.1:5173  

前端开发服务器会把 `/api` 代理到后端 `8000` 端口。

### 本机端口

| 服务 | 端口 |
|------|------|
| 前端 Vite | 5173 |
| 后端 FastAPI | 8000 |

### 默认账号

首次启动会自动创建以下账号（登录后请尽快修改密码）：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| dev | dev123 | 开发 |
| tester | tester123 | 测试 |

### Docker 本机预览（接近线上）

```bash
cd deploy
docker compose up -d --build
```

访问：http://127.0.0.1:8080  

数据与发布文件保存在项目根目录 `data/`。

---

## 服务器部署（阿里云 ECS）

推荐使用仓库内已有的 Docker Compose 方案，前后端与 Nginx 一体部署。

### 1. 准备 ECS

1. 购买 / 使用一台 Linux ECS（Ubuntu 22.04 或 CentOS 7/8 均可）
2. 建议挂载独立数据盘，用于存放 `data/`（版本文件会随使用增长）
3. 安全组放行端口：
   - **8080**（默认 compose 映射），或
   - **80**（若将映射改为 `80:80`）
4. 可选：后续绑定域名并配置 HTTPS

### 2. 安装 Docker

**Ubuntu 示例：**

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# 重新登录后使 docker 组生效
```

**CentOS 示例：**

```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
```

验证：

```bash
docker --version
docker compose version
```

### 3. 上传项目代码

将整个项目目录放到服务器，例如 `/opt/vms`：

```bash
# 本机示例（按实际路径修改）
rsync -avz --exclude node_modules --exclude backend/.venv --exclude frontend/dist \
  "./项目代码版本管理系统/" user@your-server-ip:/opt/vms/
```

或使用 Git：

```bash
ssh user@your-server-ip
sudo mkdir -p /opt/vms
sudo chown $USER:$USER /opt/vms
git clone <你的仓库地址> /opt/vms
```

### 4. 修改生产配置

编辑 `deploy/docker-compose.yml`：

```yaml
environment:
  VMS_DATABASE_URL: sqlite:////data/app.db
  VMS_STORAGE_ROOT: /data/releases
  VMS_SECRET_KEY: 请改成足够长的随机字符串
```

如需使用 80 端口访问，将：

```yaml
ports:
  - "8080:80"
```

改为：

```yaml
ports:
  - "80:80"
```

并确保安全组已放行对应端口。

### 5. 启动服务

```bash
cd /opt/vms/deploy
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f
```

浏览器访问：

- 默认：`http://服务器公网IP:8080`
- 若改为 80 端口：`http://服务器公网IP`

### 6. 上线后必做

1. 使用 `admin / admin123` 登录
2. **立即修改管理员密码**，并按需创建开发 / 测试账号
3. 确认上传、下载、删除流程正常

### 7. 数据与升级

| 路径 | 内容 |
|------|------|
| `data/app.db` | 用户、产品、版本等元数据 |
| `data/releases/` | 实际上传的程序代码与界面工程文件 |

**升级代码时不要删除 `data/` 目录。**

升级步骤示例：

```bash
cd /opt/vms
# 更新代码（git pull 或重新 rsync）
cd deploy
docker compose up -d --build
```

停止服务（数据仍保留在 `data/`）：

```bash
cd /opt/vms/deploy
docker compose down
```

### 8. 常用运维命令

```bash
cd /opt/vms/deploy
docker compose ps              # 查看运行状态
docker compose logs -f         # 跟踪日志
docker compose restart         # 重启全部服务
docker compose restart backend # 仅重启后端
```

### 9. 备份建议

定期备份整个 `data/` 目录即可同时备份数据库与发布文件：

```bash
tar -czf vms-data-$(date +%Y%m%d).tar.gz -C /opt/vms data
```

---

## 环境变量说明

后端支持以下环境变量（前缀 `VMS_`）：

| 变量 | 说明 | 默认 / 示例 |
|------|------|-------------|
| `VMS_SECRET_KEY` | JWT 签名密钥 | 开发默认弱密钥，生产必须修改 |
| `VMS_DATABASE_URL` | 数据库连接 | `sqlite:////data/app.db` |
| `VMS_STORAGE_ROOT` | 版本文件根目录 | `/data/releases` |
| `VMS_DEFAULT_ADMIN_USERNAME` | 初始管理员用户名 | `admin` |
| `VMS_DEFAULT_ADMIN_PASSWORD` | 初始管理员密码 | `admin123` |

---

## 后续可扩展方向

- 域名 + HTTPS（Nginx / 阿里云证书）
- 大文件迁移至阿里云 OSS
- SQLite 升级为 MySQL / PostgreSQL
- 发布审批、操作审计、消息通知等流程能力

---

## 许可证与使用范围

本系统供部门内部嵌入式版本发布与测试下载使用。请勿将默认账号与弱密钥用于公网生产环境。
