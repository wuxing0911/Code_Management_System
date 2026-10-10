#!/usr/bin/env bash
# Linux/fnOS only. Run with the same Docker identity used for docker login.
set -Eeuo pipefail
umask 077

die() { printf '%s\n' "$*" >&2; exit 1; }
[[ $# == 1 ]] || die '用法：sudo bash deploy/upgrade.sh v1.0.0'
new_version=$1
[[ $new_version =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z][0-9A-Za-z.-]*)?$ ]] || die '版本格式应为 v1.0.0；不允许 latest 或任意镜像地址。'

deploy_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
project_dir=$(cd -- "$deploy_dir/.." && pwd -P)
env_file="$deploy_dir/.env.registry"
compose_file="$deploy_dir/docker-compose.registry.yml"
[[ -f $env_file ]] || die '请先复制 deploy/.env.registry.example 为 .env.registry 并填写配置。'
[[ -d $project_dir/data ]] || die '找不到现有 data 目录；首次部署请按私有镜像部署文档操作。'
for dependency in docker flock tar awk mktemp; do
  command -v "$dependency" >/dev/null || die "缺少命令：$dependency"
done

export VMS_VERSION="$new_version"
compose=(docker compose --project-name deploy --env-file "$env_file" -f "$compose_file")
"${compose[@]}" config --quiet
exec 9>"$deploy_dir/.registry-upgrade.lock"
flock -n 9 || die '另一个升级任务正在执行，请勿重复运行。'

# Only upgrade the existing, running project; refuse an ambiguous backup target.
old_backend=$("${compose[@]}" ps --all --quiet backend)
old_frontend=$("${compose[@]}" ps --all --quiet frontend)
[[ -n $old_backend && -n $old_frontend ]] || die '需要现有前后端容器；首次部署请按文档操作。'
for container in "$old_backend" "$old_frontend"; do
  [[ $(docker inspect --format '{{.State.Running}}' "$container") == true ]] || die '请先启动现有前后端容器，再执行升级。'
done
data_dir=$(cd -- "$project_dir/data" && pwd -P)
mounted_data=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$old_backend")
[[ $mounted_data == "$data_dir" ]] || die '现有 /data 挂载与项目 data 目录不一致，已停止；请人工确认备份路径。'
backend_image=$(docker inspect --format '{{.Image}}' "$old_backend")
frontend_image=$(docker inspect --format '{{.Image}}' "$old_frontend")

printf '正在拉取 %s 的两个镜像；下载失败不会停止旧服务。\n' "$new_version"
"${compose[@]}" pull
mkdir -p -- "$project_dir/backups"
backup_dir=$(mktemp -d "$project_dir/backups/upgrade-${new_version}-XXXXXX")
backup_tag=$(basename -- "$backup_dir")
docker image tag "$backend_image" "vms-local-rollback/backend:$backup_tag"
docker image tag "$frontend_image" "vms-local-rollback/frontend:$backup_tag"
cp -- "$env_file" "$backup_dir/.env.registry"
printf 'services:\n  backend:\n    image: vms-local-rollback/backend:%s\n  frontend:\n    image: vms-local-rollback/frontend:%s\n' \
  "$backup_tag" "$backup_tag" > "$backup_dir/rollback.compose.yml"

phase=backup
cleanup() {
  result=$?
  trap - EXIT
  if (( result != 0 )); then
    if [[ $phase == backup ]]; then
      printf '备份阶段失败，尝试重新启动原有容器。\n' >&2
      docker start "$old_backend" "$old_frontend" >&2 || true
    elif [[ $phase == deploy ]]; then
      printf '新版启动/健康检查失败，正在停止本项目容器，避免继续写入数据。\n' >&2
      "${compose[@]}" stop >&2 || true
      printf '未自动覆盖数据库。备份与旧镜像回退配置保存在：%s\n请按文档确认迁移情况后回退。\n' "$backup_dir" >&2
    else
      printf '新版已通过健康检查，但版本配置保存失败，请人工确认 .env.registry。\n' >&2
    fi
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '暂停前后端并备份整个 data 目录；此阶段有维护停机。\n'
"${compose[@]}" stop
tar -czf "$backup_dir/data.tar.gz" -C "$project_dir" data
tar -tzf "$backup_dir/data.tar.gz" >/dev/null

phase=deploy
"${compose[@]}" up -d --no-build --pull never --force-recreate --wait --wait-timeout 180

phase=metadata
new_env=$(mktemp "$deploy_dir/.env.registry.XXXXXX")
awk -v version="$new_version" '
  /^[[:space:]]*VMS_VERSION=/ { if (!written) print "VMS_VERSION=" version; written=1; next }
  { print }
  END { if (!written) print "VMS_VERSION=" version }
' "$env_file" > "$new_env"
mv -- "$new_env" "$env_file"
phase=done
printf '升级至 %s 完成，前后端健康检查通过。\n备份保留在：%s\n' "$new_version" "$backup_dir"
"${compose[@]}" ps || printf '服务已健康启动，但无法显示状态，请人工检查 Docker。\n' >&2
