<template>
  <AppLayout>
    <template #crumb>
      <router-link class="crumb-link" to="/">产品</router-link>
      <span class="sep">/</span>
      <span class="crumb-current">{{ product?.name || '...' }}</span>
    </template>

    <div class="toolbar">
      <div>
        <h1 class="page-title">{{ product?.name }} · 版本预览</h1>
        <p class="page-sub">当前产品共有 {{ versions.length }} 个版本；点击版本查看文件与工程内容。</p>
      </div>
      <el-button v-if="canUpload()" type="primary" @click="showCreate = true">新建版本</el-button>
    </div>

    <el-row :gutter="14" class="stats-row">
      <el-col :xs="12" :sm="8">
        <div class="stat-card">
          <span>版本数量</span>
          <strong>{{ versions.length }}</strong>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8">
        <div class="stat-card blue">
          <span>文件总数</span>
          <strong>{{ fileTotal }}</strong>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card">
          <span>最新版本</span>
          <strong class="version-name">{{ versions[0]?.name || '暂无版本' }}</strong>
        </div>
      </el-col>
    </el-row>

    <div class="section-title">
      <div>
        <h2>版本目录</h2>
        <span>选择版本进入内容预览、上传和下载</span>
      </div>
    </div>

    <el-table :data="versions" stripe class="flat-table" @row-click="goFiles" empty-text="暂无版本">
      <el-table-column prop="name" label="版本号" min-width="120" />
      <el-table-column label="备注" min-width="280">
        <template #default="{ row }">
          <div class="note-cell">{{ row.note || '—' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="uploader_name" label="上传人" width="120" />
      <el-table-column prop="file_count" label="文件数" width="90" />
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column v-if="canUpload()" label="管理" width="150" align="center">
        <template #default="{ row }">
          <div class="row-actions" @click.stop>
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="removeVersion(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建版本" width="420px">
      <el-form label-position="top">
        <el-form-item label="版本号">
          <el-input v-model="form.name" placeholder="例如 V1.0.0" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="5"
            placeholder="支持多行备注，按回车换行"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createVersion">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="编辑版本" width="420px">
      <el-form label-position="top">
        <el-form-item label="版本号">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="editForm.note"
            type="textarea"
            :rows="5"
            placeholder="支持多行备注，按回车换行"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="updateVersion">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import AppLayout from '../components/AppLayout.vue'
import { useAuth } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { canUpload } = useAuth()
const product = ref(null)
const versions = ref([])
const showCreate = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const form = reactive({ name: '', note: '' })
const editForm = reactive({ id: null, name: '', note: '' })
const fileTotal = computed(() => versions.value.reduce((sum, item) => sum + item.file_count, 0))

function formatTime(v) {
  return v ? new Date(v).toLocaleString() : ''
}

async function load() {
  const id = route.params.productId
  const [p, v] = await Promise.all([
    api.get(`/products/${id}`),
    api.get(`/products/${id}/versions`),
  ])
  product.value = p.data
  versions.value = v.data
}

function goFiles(row) {
  router.push(`/products/${route.params.productId}/versions/${row.id}`)
}

async function createVersion() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入版本号')
    return
  }
  saving.value = true
  try {
    await api.post(`/products/${route.params.productId}/versions`, form)
    ElMessage.success('版本已创建')
    showCreate.value = false
    form.name = ''
    form.note = ''
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

function openEdit(version) {
  editForm.id = version.id
  editForm.name = version.name
  editForm.note = version.note || ''
  showEdit.value = true
}

async function updateVersion() {
  if (!editForm.name.trim()) {
    ElMessage.warning('请输入版本号')
    return
  }
  saving.value = true
  try {
    await api.patch(`/versions/${editForm.id}`, {
      name: editForm.name,
      note: editForm.note,
    })
    ElMessage.success('版本信息已保存')
    showEdit.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeVersion(version) {
  try {
    await ElMessageBox.confirm(
      `删除版本“${version.name}”会删除其下全部 ${version.file_count} 个文件与文件夹，无法恢复。`,
      '确认删除版本',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await api.delete(`/versions/${version.id}`)
    ElMessage.success('版本已删除')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

watch(() => route.params.productId, load)
onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 12px;
}

.flat-table {
  cursor: pointer;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

.note-cell {
  white-space: pre-line;
  word-break: break-word;
  line-height: 1.5;
  color: var(--color-text);
  font-size: 13px;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}

.row-actions :deep(.el-button) {
  margin: 0;
  padding: 4px 6px;
  height: auto;
  line-height: 1.2;
}

.stats-row {
  margin-bottom: 22px;
}

.stat-card {
  position: relative;
  min-height: 94px;
  padding: 15px 18px;
  overflow: hidden;
  border: 1px solid #cde3e4;
  border-radius: 3px;
  background: #fff;
}

.stat-card::before {
  position: absolute;
  top: 0;
  left: 0;
  width: 32px;
  height: 2px;
  background: var(--color-primary);
  content: '';
}

.stat-card span,
.stat-card strong {
  display: block;
}

.stat-card span {
  color: var(--color-muted);
  font-size: 12px;
}

.stat-card strong {
  margin-top: 6px;
  color: var(--color-primary-dark);
  font-size: 27px;
  line-height: 1.1;
}

.stat-card.blue {
  border-color: #bae6fd;
  background: #f0f9ff;
}

.stat-card.blue strong {
  color: #0369a1;
}

.stat-card .version-name {
  overflow: hidden;
  font-size: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-title {
  margin-bottom: 10px;
}

.section-title h2 {
  margin: 0 0 2px;
  font-size: 16px;
}

.section-title span {
  color: var(--color-muted);
  font-size: 12px;
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
</style>
