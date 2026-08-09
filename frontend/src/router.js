import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from './stores/auth'
import LoginView from './views/LoginView.vue'
import ProductsView from './views/ProductsView.vue'
import VersionsView from './views/VersionsView.vue'
import FilesView from './views/FilesView.vue'
import UsersView from './views/UsersView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/', name: 'products', component: ProductsView },
  { path: '/products/:productId', name: 'versions', component: VersionsView },
  { path: '/products/:productId/versions/:versionId', name: 'files', component: FilesView },
  { path: '/users', name: 'users', component: UsersView, meta: { permission: 'manage_users' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const { state, hasPermission } = useAuth()
  if (!to.meta.public && !state.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.permission && !hasPermission(to.meta.permission)) {
    return { name: 'products' }
  }
  if (to.name === 'login' && state.token) {
    return { name: 'products' }
  }
})

export default router
