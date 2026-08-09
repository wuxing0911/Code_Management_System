<template>
  <AppLayout>
    <template #crumb>
      <router-link class="crumb-link" to="/">产品</router-link>
      <span class="sep">/</span>
      <router-link class="crumb-link" :to="`/products/${route.params.productId}`">
        {{ product?.name || '...' }}
      </router-link>
      <span class="sep">/</span>
      <span class="crumb-current">{{ version?.name || '...' }}</span>
      <template v-for="(seg, idx) in pathSegments" :key="idx">
        <span class="sep">/</span>
        <a class="crumb-link" href="#" @click.prevent="enterPath(pathSegments.slice(0, idx + 1).join('/'))">{{ seg }}</a>
      </template>
    </template>

    <div class="toolbar">
      <div>
        <h1 class="page-title">{{ version?.name }} · 内容预览</h1>
        <p class="page-sub">按文件类型区分内容：程序代码为 bin/hex/LoP100；界面工程为 PKG 或 private 文件夹。</p>
      </div>
      <div class="actions">
        <el-button v-if="canDownload()" :disabled="!selected.length" type="primary" @click="downloadSelected">
          下载已选（{{ selected.length }}）
        </el-button>
        <el-button
          v-if="canDeleteFiles()"
          :disabled="!selected.length"
          type="danger"
          plain
          @click="deleteSelected"
        >
          删除已选（{{ selected.length }}）
        </el-button>
        <el-button v-if="canDownload()" @click="downloadWhole">下载整版本</el-button>
        <template v-if="canUpload()">
          <el-button type="primary" plain :loading="uploading" @click="pickCodeFiles">上传程序代码</el-button>
          <el-dropdown trigger="click" @command="onUiUploadCommand">
            <el-button type="primary" plain :loading="uploading">
              上传界面工程
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="pkg">上传 PKG 单文件</el-dropdown-item>
                <el-dropdown-item command="private">上传 private 文件夹</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </div>

    <div class="file-summary">
      <div class="path-summary"><span>当前目录</span><strong>{{ currentPathLabel }}</strong></div>
      <div><span>文件夹</span><strong><AnimatedNumber :value="directoryCount" /></strong></div>
      <div><span>文件</span><strong><AnimatedNumber :value="fileCount" /></strong></div>
      <div class="selected-summary"><span>已勾选</span><strong><AnimatedNumber :value="selected.length" :duration="350" /></strong></div>
    </div>

    <input
      ref="fileInput"
      type="file"
      multiple
      accept=".bin,.hex,.LoP100,.lop100"
      hidden
      @change="onCodeFilesChosen"
    />
    <input ref="pkgInput" type="file" multiple accept=".pkg,.PKG" hidden @change="onPkgFilesChosen" />
    <input ref="folderInput" type="file" webkitdirectory multiple hidden @change="onUiFolderChosen" />

    <div class="category-tip flat-card" v-if="!currentPath">
      <div>
        <strong>程序代码</strong>
        <span>文件类型：bin、hex、LoP100；与界面工程放在同一版本目录，通过内容类型区分</span>
      </div>
      <div>
        <strong>界面工程</strong>
        <span>单文件为 PKG；文件夹名称须为 private；同样存在当前版本目录下</span>
      </div>
    </div>

    <div class="path-bar flat-card" v-if="currentPath">
      <el-button text type="primary" class="up-button" @click="enterPath(parentPath)">‹ 返回上一级</el-button>
      <span class="path-text">当前目录：/{{ currentPath }}</span>
    </div>

    <el-table
      :data="nodes"
      stripe
      class="flat-table"
      empty-text="此目录暂无内容"
      @selection-change="onSelect"
    >
      <el-table-column v-if="canDownload() || canDeleteFiles()" type="selection" width="48" />
      <el-table-column label="名称" min-width="260">
        <template #default="{ row }">
          <button v-if="row.is_dir" class="name-btn folder" @click="enterPath(row.path)">
            [目录] {{ row.name }}
          </button>
          <span v-else class="name-file">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="内容类型" width="120">
        <template #default="{ row }">
          <span class="category-tag" :class="row.category || categoryClass(row)">
            {{ row.category_label || categoryLabel(row.path, row.is_dir) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="形态" width="90">
        <template #default="{ row }">{{ row.is_dir ? '文件夹' : '文件' }}</template>
      </el-table-column>
      <el-table-column label="大小" width="120">
        <template #default="{ row }">{{ row.is_dir ? '-' : formatSize(row.size) }}</template>
      </el-table-column>
      <el-table-column
        v-if="canDownload() || canDeleteFiles()"
        label="操作"
        :width="canDownload() && canDeleteFiles() ? 168 : 88"
        align="center"
      >
        <template #default="{ row }">
          <div class="row-actions" :class="{ 'with-delete': canDeleteFiles() }" @click.stop>
            <el-button v-if="canDownload()" text type="primary" @click="downloadOne(row)">下载</el-button>
            <el-button v-if="canDeleteFiles()" text type="danger" @click="deleteOne(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import AppLayout from '../components/AppLayout.vue'
import { useAuth } from '../stores/auth'

const route = useRoute()
const { canUpload, canDownload, canDeleteFiles } = useAuth()
const product = ref(null)
const version = ref(null)
const nodes = ref([])
const selected = ref([])
const currentPath = ref('')
const fileInput = ref(null)
const pkgInput = ref(null)
const folderInput = ref(null)
const uploading = ref(false)

const CODE_DIR = '程序代码'
const UI_DIR = '界面工程'
const CODE_EXTS = ['.bin', '.hex', '.lop100']

const pathSegments = computed(() => (currentPath.value ? currentPath.value.split('/') : []))
const parentPath = computed(() => pathSegments.value.slice(0, -1).join('/'))
const directoryCount = computed(() => nodes.value.filter((item) => item.is_dir).length)
const fileCount = computed(() => nodes.value.filter((item) => !item.is_dir).length)
const currentPathLabel = computed(() => (currentPath.value ? `/${currentPath.value}` : '版本根目录'))

function extOf(name) {
  const lower = String(name || '').toLowerCase()
  const idx = lower.lastIndexOf('.')
  return idx >= 0 ? lower.slice(idx) : ''
}

function isCodeFile(name) {
  return CODE_EXTS.includes(extOf(name))
}

function isPkgFile(name) {
  return extOf(name) === '.pkg'
}

function categoryClass(row) {
  const label = row.category_label || categoryLabel(row.path, row.is_dir)
  if (label === '程序代码') return 'code'
  if (label === '界面工程') return 'ui'
  return 'other'
}

function categoryLabel(path, isDir = false) {
  const parts = String(path || '').split('/').filter(Boolean)
  if (!parts.length) return '其他'
  const first = parts[0]
  if (first === CODE_DIR || first === 'code') return '程序代码'
  if (first === UI_DIR || first === 'ui') return '界面工程'
  if (parts.some((part) => part.toLowerCase() === 'private')) return '界面工程'
  const name = parts[parts.length - 1]
  if (!isDir && isCodeFile(name)) return '程序代码'
  if (!isDir && isPkgFile(name)) return '界面工程'
  if (isDir && name.toLowerCase() === 'private') return '界面工程'
  return '其他'
}

function resolveUploadBase() {
  return currentPath.value || ''
}

function joinPath(base, relative) {
  const rel = String(relative || '').replace(/\\/g, '/').replace(/^\/+/, '')
  if (!base) return rel
  return `${base}/${rel}`
}

function formatSize(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function onSelect(rows) {
  selected.value = rows
}

function enterPath(path) {
  currentPath.value = path || ''
  selected.value = []
  loadFiles()
}

async function loadMeta() {
  const [p, v] = await Promise.all([
    api.get(`/products/${route.params.productId}`),
    api.get(`/versions/${route.params.versionId}`),
  ])
  product.value = p.data
  version.value = v.data
}

async function loadFiles() {
  const { data } = await api.get(`/versions/${route.params.versionId}/files`, {
    params: { path: currentPath.value || undefined },
  })
  nodes.value = data
}

async function downloadBlob(url, body, fallbackName) {
  const res = await api.post(url, body, { responseType: 'blob' })
  const cd = res.headers['content-disposition'] || ''
  let name = fallbackName
  const m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd)
  if (m) name = decodeURIComponent(m[1] || m[2])
  const blobUrl = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = name
  a.click()
  URL.revokeObjectURL(blobUrl)
}

async function downloadSelected() {
  if (!selected.value.length) return
  const paths = selected.value.map((x) => x.path)
  const onlyOneFile = selected.value.length === 1 && !selected.value[0].is_dir
  try {
    await downloadBlob(
      `/versions/${route.params.versionId}/download-selected`,
      { paths },
      onlyOneFile ? selected.value[0].name : `${version.value?.name || 'selected'}.zip`,
    )
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function downloadWhole() {
  try {
    const res = await api.get(`/versions/${route.params.versionId}/download`, { responseType: 'blob' })
    const blobUrl = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `${product.value?.slug || 'product'}_${version.value?.name || 'version'}.zip`
    a.click()
    URL.revokeObjectURL(blobUrl)
  } catch {
    ElMessage.error('下载失败')
  }
}

async function downloadOne(row) {
  try {
    if (!row.is_dir && row.file_id) {
      const res = await api.get(`/files/${row.file_id}/download`, { responseType: 'blob' })
      const blobUrl = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = row.name
      a.click()
      URL.revokeObjectURL(blobUrl)
      return
    }
    await downloadBlob(
      `/versions/${route.params.versionId}/download-selected`,
      { paths: [row.path] },
      row.is_dir ? `${row.name}.zip` : row.name,
    )
  } catch {
    ElMessage.error('下载失败')
  }
}

async function deletePaths(paths, tip) {
  try {
    await ElMessageBox.confirm(tip, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.post(`/versions/${route.params.versionId}/delete-selected`, { paths })
    ElMessage.success('已删除')
    selected.value = []
    await loadFiles()
    await loadMeta()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

async function deleteOne(row) {
  const tip = row.is_dir
    ? `删除文件夹“${row.name}”将同时删除其中全部内容，无法恢复。`
    : `删除文件“${row.name}”后无法恢复，是否继续？`
  await deletePaths([row.path], tip)
}

async function deleteSelected() {
  if (!selected.value.length) return
  const tip = `将删除已勾选的 ${selected.value.length} 项（含文件夹内全部内容），无法恢复。`
  await deletePaths(
    selected.value.map((item) => item.path),
    tip,
  )
}

function pickCodeFiles() {
  fileInput.value?.click()
}

function onUiUploadCommand(command) {
  if (command === 'pkg') {
    pkgInput.value?.click()
  } else if (command === 'private') {
    folderInput.value?.click()
  }
}

async function onCodeFilesChosen(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  const invalid = files.filter((f) => !isCodeFile(f.name))
  if (invalid.length) {
    ElMessage.warning('程序代码仅支持 bin、hex、LoP100 文件')
    return
  }
  const base = resolveUploadBase()
  const fd = new FormData()
  files.forEach((f) => {
    fd.append('files', f)
    fd.append('paths', joinPath(base, f.name))
  })
  await doUpload('/upload/files', fd, '程序代码上传成功')
}

async function onPkgFilesChosen(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  const invalid = files.filter((f) => !isPkgFile(f.name))
  if (invalid.length) {
    ElMessage.warning('界面工程单文件仅支持 PKG')
    return
  }
  const base = resolveUploadBase()
  const fd = new FormData()
  files.forEach((f) => {
    fd.append('files', f)
    fd.append('paths', joinPath(base, f.name))
  })
  await doUpload('/upload/files', fd, '界面工程 PKG 上传成功')
}

async function onUiFolderChosen(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  const topName = String(files[0].webkitRelativePath || files[0].name).split(/[/\\]/)[0]
  if (topName.toLowerCase() !== 'private') {
    ElMessage.warning('界面工程文件夹名称必须为 private')
    return
  }
  const base = resolveUploadBase()
  const fd = new FormData()
  files.forEach((f) => {
    fd.append('files', f)
    const webkit = f.webkitRelativePath || f.name
    fd.append('paths', joinPath(base, webkit))
  })
  await doUpload('/upload/folder', fd, '界面工程 private 文件夹上传成功')
}

async function doUpload(suffix, fd, successText = '上传成功') {
  uploading.value = true
  try {
    await api.post(`/versions/${route.params.versionId}${suffix}`, fd)
    ElMessage.success(successText)
    await loadFiles()
    await loadMeta()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

watch(
  () => [route.params.productId, route.params.versionId],
  async () => {
    currentPath.value = ''
    await loadMeta()
    await loadFiles()
  },
)

onMounted(async () => {
  await loadMeta()
  await loadFiles()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-tip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 12px;
}

.category-tip strong,
.category-tip span {
  display: block;
}

.category-tip strong {
  margin-bottom: 4px;
  color: var(--color-primary-dark);
}

.category-tip span {
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.5;
}

.category-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  white-space: nowrap;
}

.category-tag.code {
  background: #e0f2fe;
  color: #0369a1;
}

.category-tag.ui {
  background: #ccfbf1;
  color: #0f766e;
}

.category-tag.other {
  background: #f1f5f9;
  color: #64748b;
}

.actions :deep(.el-button--primary:not(.is-plain)) {
  border-color: #0b6d72;
  background: #0b6d72;
  color: #ffffff;
  font-weight: 600;
}

.actions :deep(.el-button--primary:not(.is-plain):hover) {
  border-color: #075c61;
  background: #075c61;
  color: #ffffff;
}

.actions :deep(.el-button--primary.is-disabled:not(.is-plain)),
.actions :deep(.el-button--primary.is-disabled:not(.is-plain):hover) {
  border-color: #9bb9bc;
  background: #9bb9bc;
  color: #f7ffff;
}

.file-summary {
  display: grid;
  grid-template-columns: minmax(210px, 1.5fr) repeat(3, minmax(110px, 0.5fr));
  margin-bottom: 12px;
  border: 1px solid #cde3e4;
  border-radius: 3px;
  background: #fff;
  box-shadow: 0 8px 20px rgba(22, 75, 82, 0.04);
}

.file-summary > div {
  min-width: 0;
  padding: 12px 16px;
  border-right: 1px solid var(--color-border);
}

.file-summary > div:last-child {
  border-right: 0;
}

.file-summary > div > span,
.file-summary > div > strong {
  display: block;
}

.file-summary > div > span {
  color: #486b72;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.file-summary > div > strong {
  overflow: hidden;
  margin-top: 5px;
  color: #075c61;
  font-size: 28px;
  font-weight: 750;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-summary > .path-summary > strong {
  font-size: 16px;
  font-weight: 650;
  line-height: 1.65;
}

.selected-summary {
  background: #d5f4ee;
}

.selected-summary > strong {
  color: #075c61;
}

.path-bar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  font-size: 13px;
  color: var(--color-muted);
}

.up-button {
  flex-shrink: 0;
  padding-left: 0;
  color: #167c80;
  font-weight: 600;
}

.path-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flat-table {
  border: 1px solid #cde3e4;
  border-radius: 3px;
  overflow: hidden;
}

.row-actions {
  display: grid;
  grid-template-columns: 48px;
  align-items: center;
  justify-content: center;
  justify-items: center;
  gap: 4px;
  margin: 0 auto;
  white-space: nowrap;
}

.row-actions.with-delete {
  grid-template-columns: 48px 48px;
}

.row-actions :deep(.el-button) {
  margin: 0;
  padding: 4px 0;
  width: 48px;
  height: auto;
  line-height: 1.2;
  justify-content: center;
}

.name-btn {
  border: none;
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  padding: 0;
  font: inherit;
}

.name-btn:hover {
  text-decoration: underline;
}

.name-file {
  color: var(--color-text);
}

.crumb-link {
  color: var(--color-accent);
  font-size: 14px;
}

.sep {
  margin: 0 6px;
  color: var(--color-muted);
}

.crumb-current {
  color: var(--color-muted);
  font-size: 14px;
}

@media (max-width: 700px) {
  .file-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .file-summary > div:nth-child(2) {
    border-right: 0;
  }

  .file-summary > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
