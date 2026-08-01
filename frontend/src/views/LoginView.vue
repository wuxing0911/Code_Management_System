<template>
  <div class="login-page">
    <div class="login-panel flat-card">
      <div class="brand">项目代码版本管理</div>
      <p class="hint">嵌入式最终发布物 · 产品 / 版本 / 文件</p>
      <el-form :model="form" label-position="top" class="login-form" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin / dev / tester" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="onSubmit">
          登录
        </el-button>
      </el-form>
      <p class="seed">默认账号 admin / admin123</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const { setAuth } = useAuth()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function onSubmit() {
  loading.value = true
  try {
    const { data } = await api.post('/auth/login-json', form)
    localStorage.setItem('token', data.access_token)
    const me = await api.get('/auth/me')
    setAuth(data.access_token, me.data)
    ElMessage.success('登录成功')
    router.replace(route.query.redirect || '/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 20% 20%, #99f6e4 0, transparent 40%),
    radial-gradient(circle at 80% 10%, #bae6fd 0, transparent 35%),
    #f0faf8;
}

.login-panel {
  width: min(400px, 100%);
}

.brand {
  font-size: 26px;
  font-weight: 700;
  color: #0f766e;
  letter-spacing: 0.02em;
}

.hint {
  margin: 6px 0 20px;
  color: var(--color-muted);
  font-size: 13px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
  display: block;
}

.login-form :deep(.el-form-item__label) {
  display: block;
  float: none;
  width: 100% !important;
  padding-bottom: 4px;
  margin-bottom: 0;
  color: var(--color-text);
  font-weight: 500;
  line-height: 1.4;
  text-align: left;
  justify-content: flex-start;
}

.login-form :deep(.el-form-item__content) {
  display: block;
  width: 100% !important;
  margin-left: 0 !important;
}

.login-form :deep(.el-input) {
  width: 100%;
}

.login-form :deep(.el-input__wrapper) {
  width: 100%;
  box-sizing: border-box;
}

.login-btn {
  width: 100%;
  margin-top: 4px;
}

.seed {
  margin: 16px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}
</style>
