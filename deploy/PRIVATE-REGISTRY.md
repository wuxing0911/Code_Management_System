# Docker Hub 私有镜像发布与飞牛 NAS 升级

本方案使用 GitHub Actions 构建，NAS 只拉取成品镜像。只自动发布，不会未经确认自动升级 NAS。原有 `docker-compose.yml` 源码构建方式保持不变。

## 1. 创建一个私有仓库

在 Docker Hub 登录自己的账号，创建名为 **vms** 的仓库，创建时选择 **Private**。不要先推送再改私有，以免镜像短暂公开。也可使用其他名称，但需要同时修改 GitHub 的 `DOCKERHUB_REPOSITORY` 变量和 NAS 配置。

镜像仓库私有不会改变 GitHub 源码仓库的可见性；如源码也需要保密，应另行检查 GitHub 仓库设置。

前后端共用一个私有仓库，使用不同标签，例如：

```text
你的DockerHub用户名/vms:backend-v1.0.0
你的DockerHub用户名/vms:frontend-v1.0.0
```

当前 NAS 是 x86，工作流构建 `linux/amd64`。更换 ARM NAS 时必须同步调整工作流和 Compose 平台。

## 2. 配置两个用途不同的访问令牌

在 Docker Hub 创建 Personal Access Token（PAT）：

- GitHub 发布使用：Read & Write，不需要 Delete。
- NAS 下载使用：Read-only；如果账户支持仓库范围限制，限制到该私有仓库。

令牌只粘贴到对应产品的设置页或本机交互式密码输入中，不发到聊天、不写进仓库或命令行参数。

在 GitHub 代码仓库 **Settings → Secrets and variables → Actions → Repository secrets** 添加：

| Secret | 内容 |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub 用户名，不是邮箱，也不一定与 GitHub 用户名相同 |
| `DOCKERHUB_TOKEN` | 发布用 Read & Write PAT |

仓库名不是 `vms` 时，再在 Variables 添加 `DOCKERHUB_REPOSITORY`。工作流会在构建前、推送前核验仓库确实存在且 `is_private=true`；查不到或不是私有就停止，不会创建仓库或修改其可见性。

## 3. 发布第一个版本

先将本次新增工作流、部署文件、测试和所需应用修改提交并推送到 GitHub。工作区里尚未提交的修改不会进入云端镜像。

在本机 Git 仓库，为已审核的提交创建一个尚未使用的版本标签：

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub **Actions → Publish private Docker images** 会先测试并核验隐私，再构建两个镜像。两个镜像都构建成功后才开始推送。不创建 `latest` 标签，不在普通分支提交时发布。

手动重新运行时选择现有的版本 tag，不能选择 main。不要移动已发布的 tag 或重复用于不同代码。推送两个镜像不是仓库端的原子事务，网络中断仍可能只推送一个；**必须等整个工作流全部成功，两个版本标签都存在，再升级 NAS**。

## 4. 配置 NAS（只做一次）

把 `deploy` 中的新文件同步到 NAS 的 `/vol1/1000/Docker/vms/deploy`，不要覆盖或删除已有 `data`，也不要启动第二个 Compose 项目。新配置显式沿用原来的项目名 `deploy`。

在 NAS SSH 终端：

```bash
cd /vol1/1000/Docker/vms/deploy
cp -n .env.registry.example .env.registry
chmod 600 .env.registry
```

通过文件编辑器填写 `.env.registry`：

- `DOCKERHUB_USERNAME`：自己的 Docker Hub 用户名。
- `DOCKERHUB_REPOSITORY`：`vms` 或实际仓库名。
- `VMS_VERSION`：已发布版本，例如 `v1.0.0`。
- `VMS_HTTP_PORT`：保持当前 `18080`，或填写现有映射端口。
- `VMS_SECRET_KEY`：首次迁移可复制现有 Compose 中的密钥，避免现有登录失效。之后应单独换成长随机密钥；更换后所有用户需要重新登录。

不要在这个文件放 Docker Hub PAT。该文件已被 Git 忽略。

使用与升级脚本相同的 root Docker 身份登录实际拉取地址：

```bash
sudo docker login registry-1.docker.io --username 你的DockerHub用户名
```

在 Password 提示处粘贴 **NAS 专用 Read-only PAT**，不要输入飞牛密码。Docker 会保存登录凭据；没有 credential helper 时通常保存在 root 的 Docker 配置中（编码不是加密），请保护 NAS 管理员权限，停用令牌时及时撤销。不要发出该配置文件截图。

Docker 网络代理仍在飞牛 Docker 设置里管理。拉取期间可能需要 Mac Clash 保持运行，但不再需要把代理传给 pip/npm，也不需要 NAS 下载源代码依赖。

## 5. 从当前源码部署切换，或升级后续版本

确认该版本的全部发布工作流成功、当前两个容器运行中，并阅读新版本的数据库变更说明，然后执行：

```bash
cd /vol1/1000/Docker/vms/deploy
sudo bash upgrade.sh v1.0.0
```

后续只需将参数换为已发布的新版本，例如 `v1.1.0`。脚本会：

1. 检查版本、部署配置、升级锁和当前数据挂载，避免操作其他目录。
2. 在旧服务运行时拉取两个镜像；失败不会停止旧服务。
3. 保留旧镜像的本地回退标签和部署环境配置。
4. 停止本项目前后端，将整个 `data`（数据库和上传文件）打包备份并检查归档可读性。
5. 更新两个容器，等待后端 API、前端网页及代理 API 健康检查。
6. 成功后记录当前版本到 `.env.registry`，并打印备份目录。

停止写入后的整个备份、更新阶段都有维护停机。数据越大，备份耗时和所需空间越多。备份保存在项目的 `backups/upgrade-版本-随机后缀/`，权限仅当前执行用户可读。它与原数据在同一 NAS 上，不替代异机备份。脚本不会清理旧备份或旧镜像，请定期检查空间并按保留策略人工清理。

验证入口仍是 `http://NAS局域网IP:18080`。如果失败，查看：

```bash
sudo docker compose --env-file .env.registry -f docker-compose.registry.yml logs --tail=100 backend frontend
```

切换后请统一使用新的 `--env-file .env.registry -f docker-compose.registry.yml` 参数管理项目。不要再用旧源码 Compose 执行 `up`，否则会切回本地构建镜像。

## 6. 首次安装到空 NAS

没有旧容器时，不使用升级脚本。先创建项目根目录的 `data`、配置 `.env.registry` 并登录仓库，然后执行：

```bash
sudo docker compose --env-file .env.registry -f docker-compose.registry.yml pull
sudo docker compose --env-file .env.registry -f docker-compose.registry.yml up -d --no-build --wait --wait-timeout 180
```

## 7. 失败处理与回退

- 下载失败：旧服务继续运行，修复网络或令牌后重试。
- 备份失败：脚本尝试重新启动原容器，先处理磁盘空间/权限，不要继续升级。
- 新版启动或健康检查失败：脚本停止本项目容器并保留备份，不自动覆盖数据库，以免在未知迁移情况下丢数据。

每个完整备份含 `data.tar.gz`、旧 `.env.registry` 及 `rollback.compose.yml`，回退镜像另有本地标签，不要在确认新版本之前删除它们。

回退时先停止项目并保护当前 data。确认备份完整后，可将当前 data **重命名保留**到另一个未使用的目录，再把该次 `data.tar.gz` 解压到项目根目录；不要把旧数据库直接覆盖到正在运行的服务上。恢复该备份的 `.env.registry`，然后在 deploy 目录使用对应备份的回退配置：

```bash
# 将下面路径替换为本次升级打印出的真实备份目录。
sudo docker compose --env-file ../backups/实际备份目录/.env.registry \
  -f docker-compose.registry.yml \
  -f ../backups/实际备份目录/rollback.compose.yml \
  up -d --no-build --pull never --wait --wait-timeout 180
```

数据恢复到升级前备份会撤销备份之后的写入。涉及数据库变更时务必先核对迁移说明，并保留失败版本的数据副本。当前应用使用 `create_all` 创建缺失表，并不等于已有字段的自动迁移；**本方案不提供数据库自动迁移，也不自动追踪新版本升级**。

## 本地验证

```bash
python3 -m unittest discover -s deploy/tests -v
bash -n deploy/upgrade.sh
```

测试使用临时目录、模拟 Docker 和模拟 Hub API，不会连接 NAS、发布镜像或接触真实数据库。实际镜像构建与健康检查仍需在 GitHub Actions 和 NAS 上验证。
