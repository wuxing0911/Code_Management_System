<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand-area">
        <router-link to="/" class="logo"><span class="logo-mark">V</span> 项目代码版本管理</router-link>
        <span class="brand-subtitle">嵌入式发布物中心</span>
      </div>
      <div class="right">
        <span class="user">{{ userLabel }}</span>
        <el-button v-if="isAdmin()" text type="primary" @click="$router.push('/users')">用户管理</el-button>
        <el-button text type="primary" @click="logout">退出</el-button>
      </div>
    </header>
    <div class="workspace" :style="{ '--sidebar-width': `${sidebarWidth}px` }">
      <aside class="sidebar">
        <nav class="main-nav">
          <router-link to="/" class="nav-item" :class="{ active: $route.name === 'products' }">
            产品总览
          </router-link>
          <router-link v-if="isAdmin()" to="/users" class="nav-item" :class="{ active: $route.name === 'users' }">
            用户管理
          </router-link>
        </nav>

        <section class="overview-panel">
          <span class="panel-caption"><i></i> 资源概览</span>
          <div class="overview-numbers">
            <div><strong>{{ products.length }}</strong><small>产品</small></div>
            <div><strong>{{ versionTotal }}</strong><small>版本</small></div>
          </div>
        </section>

        <section class="quick-products">
          <div class="section-heading">
            <span>产品快捷导航</span>
            <router-link to="/">全部</router-link>
          </div>
          <div v-if="products.length" class="product-links">
            <router-link
              v-for="product in products"
              :key="product.id"
              :to="`/products/${product.id}`"
              class="product-link"
              :class="{ active: String($route.params.productId) === String(product.id) }"
            >
              <span class="product-link-name">{{ product.name }}</span>
              <small>{{ product.version_count }} 个版本</small>
            </router-link>
          </div>
          <p v-else class="empty-tip">暂未创建产品</p>
        </section>
      </aside>
      <div
        class="sidebar-resizer"
        role="separator"
        aria-label="调整侧栏宽度"
        aria-orientation="vertical"
        @pointerdown="startResize"
      ></div>

      <main class="content">
        <div class="breadcrumb-row">
          <el-button class="back-button" text @click="goBack">‹ 返回上一页</el-button>
          <span class="breadcrumb-divider"></span>
          <slot name="crumb" />
        </div>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const { state, clearAuth, isAdmin } = useAuth()
const products = ref([])
const sidebarWidth = ref(Number(localStorage.getItem('sidebar-width')) || 250)

const roleMap = { admin: '管理员', developer: '开发', tester: '测试' }
const userLabel = computed(() => {
  if (!state.user) return ''
  return `${state.user.username}（${roleMap[state.user.role] || state.user.role}）`
})

const versionTotal = computed(() => products.value.reduce((sum, item) => sum + item.version_count, 0))

async function loadProducts() {
  try {
    const { data } = await api.get('/products')
    products.value = data
  } catch {
    products.value = []
  }
}

function logout() {
  clearAuth()
  router.push('/login')
}

function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/')
  }
}

function resizeSidebar(event) {
  sidebarWidth.value = Math.min(420, Math.max(210, event.clientX))
}

function stopResize() {
  document.body.classList.remove('resizing-sidebar')
  document.removeEventListener('pointermove', resizeSidebar)
  document.removeEventListener('pointerup', stopResize)
  localStorage.setItem('sidebar-width', String(sidebarWidth.value))
}

function startResize(event) {
  event.preventDefault()
  document.body.classList.add('resizing-sidebar')
  document.addEventListener('pointermove', resizeSidebar)
  document.addEventListener('pointerup', stopResize)
}

onMounted(loadProducts)
onBeforeUnmount(stopResize)
</script>

<style scoped>
.layout {
  min-height: 100vh;
  background: #eef6f7;
}

.topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  background: #0e3440;
  border-bottom: 1px solid rgba(94, 234, 212, 0.28);
  color: #fff;
}

.right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-area {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
}

.logo-mark {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border: 1px solid #5eead4;
  border-radius: 3px;
  color: #5eead4;
  font-family: monospace;
  font-size: 14px;
}

.brand-subtitle {
  padding-left: 12px;
  border-left: 1px solid rgba(255, 255, 255, 0.38);
  font-size: 12px;
  opacity: 0.82;
}

.user {
  font-size: 13px;
  opacity: 0.95;
  margin-right: 4px;
}

.right :deep(.el-button) {
  color: #fff !important;
}

.workspace {
  display: grid;
  grid-template-columns: var(--sidebar-width) 6px minmax(0, 1fr);
  min-height: calc(100vh - 60px);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 14px;
  background:
    linear-gradient(rgba(16, 55, 66, 0.96), rgba(10, 42, 52, 0.98)),
    repeating-linear-gradient(0deg, transparent 0, transparent 29px, rgba(94, 234, 212, 0.035) 30px);
  border-right: 1px solid #1c5965;
  min-width: 0;
  overflow: hidden;
}

.sidebar-resizer {
  position: relative;
  z-index: 2;
  cursor: col-resize;
  background: #123d49;
  touch-action: none;
}

.sidebar-resizer::after {
  position: absolute;
  top: 50%;
  left: 2px;
  width: 2px;
  height: 40px;
  border-radius: 2px;
  background: #4d8790;
  content: '';
  transform: translateY(-50%);
}

.sidebar-resizer:hover,
.sidebar-resizer:hover::after {
  background: #14b8a6;
}

.main-nav {
  display: grid;
  gap: 4px;
}

.nav-item {
  padding: 10px 12px;
  border-left: 2px solid transparent;
  color: #b7d4d6;
  font-size: 15px;
}

.nav-item:hover,
.nav-item.active {
  border-left-color: #5eead4;
  background: rgba(45, 212, 191, 0.12);
  color: #e6fffb;
  font-weight: 600;
}

.overview-panel {
  padding: 14px;
  border: 1px solid rgba(94, 234, 212, 0.3);
  border-radius: 3px;
  color: #bce8e3;
  font-size: 12px;
  background: rgba(4, 29, 39, 0.32);
}

.panel-caption {
  font-size: 12px;
}

.panel-caption i {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 5px;
  border-radius: 50%;
  background: #5eead4;
  box-shadow: 0 0 9px #5eead4;
}

.overview-numbers {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  margin-top: 10px;
}

.overview-numbers div + div {
  border-left: 1px solid rgba(94, 234, 212, 0.22);
  padding-left: 12px;
}

.overview-numbers strong,
.overview-numbers small {
  display: block;
}

.overview-numbers strong {
  color: #7af3dc;
  font-size: 23px;
  line-height: 1.15;
}

.overview-numbers small {
  margin-top: 3px;
  color: #91b8bc;
}

.quick-products {
  min-height: 0;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 8px;
  color: #8db7bb;
  font-size: 13px;
}

.section-heading a {
  font-size: 13px;
}

.product-links {
  display: grid;
  gap: 4px;
}

.product-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px;
  border-left: 2px solid transparent;
  color: #d4e9e9;
}

.product-link:hover,
.product-link.active {
  background: rgba(45, 212, 191, 0.1);
}

.product-link.active {
  border-left-color: #5eead4;
  padding-left: 8px;
}

.product-link-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.product-link small,
.empty-tip {
  color: #86afb3;
  font-size: 12px;
  white-space: nowrap;
}

.empty-tip {
  padding: 0 8px;
}

.content {
  width: 100%;
  max-width: 1500px;
  padding: 24px 32px 48px;
  background:
    linear-gradient(90deg, rgba(14, 165, 233, 0.025) 1px, transparent 1px),
    linear-gradient(rgba(20, 184, 166, 0.02) 1px, transparent 1px);
  background-size: 34px 34px;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  min-height: 28px;
  margin-bottom: 12px;
  color: #587880;
  font-size: 13px;
}

.breadcrumb-row::before {
  width: 5px;
  height: 5px;
  margin-right: 8px;
  border-radius: 50%;
  background: #14b8a6;
  box-shadow: 0 0 7px rgba(20, 184, 166, 0.8);
  content: '';
}

.back-button {
  padding: 0 8px 0 0;
  color: #167c80;
  font-size: 13px;
  font-weight: 600;
}

.back-button:hover {
  color: #075c61;
}

.breadcrumb-divider {
  width: 1px;
  height: 14px;
  margin: 0 10px 0 2px;
  background: #b9d5d7;
}

@media (max-width: 780px) {
  .topbar {
    padding: 0 16px;
  }

  .brand-subtitle,
  .user {
    display: none;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .sidebar-resizer {
    display: none;
  }

  .content {
    padding: 16px;
  }
}
</style>
