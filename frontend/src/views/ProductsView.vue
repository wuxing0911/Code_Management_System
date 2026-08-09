<template>
  <AppLayout>
    <template #crumb>
      <span class="crumb-current">产品列表</span>
    </template>

    <div class="toolbar">
      <div>
        <h1 class="page-title">产品总览</h1>
        <p class="page-sub">集中查看所有产品与对应版本，点击产品进入版本预览。</p>
      </div>
      <div class="actions">
        <el-input v-model="keyword" clearable placeholder="搜索产品" style="width: 220px" @clear="load" @keyup.enter="load" />
        <el-button type="primary" @click="load">搜索</el-button>
        <el-button v-if="canManageProducts()" type="primary" plain @click="showCreate = true">新建产品</el-button>
      </div>
    </div>

    <el-row :gutter="14" class="stats-row">
      <el-col :xs="24" :sm="12" :md="8">
        <div class="stat-card primary-stat">
          <span>产品总数</span>
          <strong><AnimatedNumber :value="products.length" /></strong>
          <small>已纳入版本管理的产品</small>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <div class="stat-card accent-stat">
          <span>版本总数</span>
          <strong><AnimatedNumber :value="versionTotal" /></strong>
          <small>所有产品下的可用版本</small>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <div class="stat-card neutral-stat">
          <span>最近更新</span>
          <strong class="latest-name">{{ latestProduct?.name || '暂无' }}</strong>
          <small>{{ latestProduct ? formatTime(latestProduct.created_at) : '创建产品后显示' }}</small>
        </div>
      </el-col>
    </el-row>

    <div class="section-title">
      <div>
        <h2>产品目录</h2>
        <span>每个产品显示其下版本数量</span>
      </div>
    </div>

    <div v-if="products.length" class="product-grid">
      <article v-for="product in products" :key="product.id" class="product-card" @click="goVersions(product)">
        <div class="product-card-head">
          <span class="product-mark">{{ product.name.slice(0, 1) }}</span>
          <span class="version-badge">{{ product.version_count }} 个版本</span>
        </div>
        <strong>{{ product.name }}</strong>
        <p>{{ product.description || '暂未填写产品描述' }}</p>
        <footer>
          <span>创建于 {{ formatDate(product.created_at) }}</span>
          <span class="card-actions" v-if="canManageProducts()">
            <el-button text type="primary" @click.stop="openEdit(product)">编辑</el-button>
            <el-button text type="danger" @click.stop="removeProduct(product)">删除</el-button>
          </span>
          <span v-else class="go-link">查看版本 →</span>
        </footer>
      </article>
    </div>
    <el-empty v-else description="暂无产品，请先创建第一个产品" />

    <el-dialog v-model="showCreate" title="新建产品" width="420px">
      <el-form label-position="top">
        <el-form-item label="产品名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createProduct">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="编辑产品" width="420px">
      <el-form label-position="top">
        <el-form-item label="产品名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="updateProduct">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import AppLayout from '../components/AppLayout.vue'
import { useAuth } from '../stores/auth'

const router = useRouter()
const { canManageProducts } = useAuth()
const products = ref([])
const keyword = ref('')
const showCreate = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const form = reactive({ name: '', description: '' })
const editForm = reactive({ id: null, name: '', description: '' })
const versionTotal = computed(() => products.value.reduce((sum, item) => sum + item.version_count, 0))
const latestProduct = computed(() => products.value[0])

function formatTime(v) {
  return v ? new Date(v).toLocaleString() : ''
}

function formatDate(v) {
  return v ? new Date(v).toLocaleDateString() : ''
}

async function load() {
  const { data } = await api.get('/products', { params: { q: keyword.value || undefined } })
  products.value = data
}

function goVersions(row) {
  router.push(`/products/${row.id}`)
}

async function createProduct() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入产品名称')
    return
  }
  saving.value = true
  try {
    await api.post('/products', form)
    ElMessage.success('已创建')
    showCreate.value = false
    form.name = ''
    form.description = ''
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

function openEdit(product) {
  editForm.id = product.id
  editForm.name = product.name
  editForm.description = product.description || ''
  showEdit.value = true
}

async function updateProduct() {
  if (!editForm.name.trim()) {
    ElMessage.warning('请输入产品名称')
    return
  }
  saving.value = true
  try {
    await api.patch(`/products/${editForm.id}`, {
      name: editForm.name,
      description: editForm.description,
    })
    ElMessage.success('产品信息已保存')
    showEdit.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeProduct(product) {
  try {
    await ElMessageBox.confirm(
      `删除“${product.name}”将同时删除其下 ${product.version_count} 个版本及所有服务器文件，无法恢复。`,
      '确认删除产品',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await api.delete(`/products/${product.id}`)
    ElMessage.success('产品已删除')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  position: relative;
  min-height: 126px;
  padding: 18px 20px;
  overflow: hidden;
  border: 1px solid #cde3e4;
  border-radius: 3px;
  background: var(--color-surface);
  box-shadow: 0 8px 20px rgba(22, 75, 82, 0.04);
}

.stat-card::before {
  position: absolute;
  top: 0;
  left: 0;
  width: 42px;
  height: 2px;
  background: var(--color-primary);
  content: '';
}

.stat-card > span,
.stat-card > small,
.stat-card > strong {
  display: block;
}

.stat-card > span {
  color: #365f67;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.stat-card > strong {
  margin: 10px 0 9px;
  color: #075c61;
  font-size: 42px;
  font-weight: 750;
  line-height: 1;
}

.stat-card > small {
  color: #71868b;
  font-size: 12px;
  line-height: 1.45;
}

.accent-stat {
  border-color: #bae6fd;
  background: linear-gradient(135deg, #fff, #f0f9ff);
}

.accent-stat > strong {
  color: #0369a1;
}

.neutral-stat {
  background: linear-gradient(135deg, #fff, #f0fdfa);
}

.stat-card > strong.latest-name {
  overflow: hidden;
  font-size: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title h2 {
  margin: 0 0 3px;
  color: var(--color-text);
  font-size: 16px;
}

.section-title span {
  color: var(--color-muted);
  font-size: 12px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 14px;
}

.product-card {
  position: relative;
  display: flex;
  min-height: 174px;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
  border: 1px solid #cfe3e4;
  border-radius: 3px;
  background: linear-gradient(135deg, #fff, #f8fdfd);
  color: var(--color-text);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.product-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 16px;
  height: 16px;
  border-top: 2px solid #5eead4;
  border-right: 2px solid #5eead4;
  content: '';
}

.product-card:hover {
  border-color: #2dd4bf;
  background: #fbfffe;
  box-shadow: 0 12px 25px rgba(13, 148, 136, 0.12);
  transform: translateY(-2px);
}

.product-card-head,
.product-card footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.card-actions :deep(.el-button) {
  margin-left: 0;
  padding: 2px 4px;
}

.product-mark {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid #8ee9dc;
  border-radius: 3px;
  background: #eafcf9;
  color: var(--color-primary-dark);
  font-weight: 700;
}

.version-badge {
  color: var(--color-accent);
  font-size: 12px;
}

.product-card > strong {
  margin-top: 16px;
  font-size: 16px;
}

.product-card p {
  display: -webkit-box;
  overflow: hidden;
  margin: 6px 0 auto;
  color: var(--color-muted);
  font-size: 13px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.product-card footer {
  margin-top: 16px;
  color: var(--color-muted);
  font-size: 11px;
}

.go-link {
  color: var(--color-primary);
  font-size: 12px;
}

.crumb-current {
  color: var(--color-muted);
  font-size: 14px;
}
</style>
