<template>
  <AppLayout>
    <template #crumb>
      <span class="crumb-current">用户管理</span>
    </template>

    <div class="toolbar">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">管理员可创建账号并分配角色</p>
      </div>
      <el-button type="primary" @click="showCreate = true">新建用户</el-button>
    </div>

    <el-table :data="users" stripe class="flat-table">
      <el-table-column prop="username" label="用户名" />
      <el-table-column label="角色" width="140">
        <template #default="{ row }">{{ roleMap[row.role] || row.role }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ row.is_active ? '启用' : '禁用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button text type="primary" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
          <el-button text type="primary" @click="openReset(row)">重置密码</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建用户" width="420px">
      <el-form label-position="top">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="开发" value="developer" />
            <el-option label="测试" value="tester" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createUser">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReset" title="重置密码" width="420px">
      <el-input v-model="resetPassword" type="password" placeholder="新密码" />
      <template #footer>
        <el-button @click="showReset = false">取消</el-button>
        <el-button type="primary" @click="resetPwd">确定</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import AppLayout from '../components/AppLayout.vue'

const users = ref([])
const showCreate = ref(false)
const showReset = ref(false)
const resetPassword = ref('')
const current = ref(null)
const form = reactive({ username: '', password: '', role: 'tester' })
const roleMap = { admin: '管理员', developer: '开发', tester: '测试' }

async function load() {
  const { data } = await api.get('/users')
  users.value = data
}

async function createUser() {
  try {
    await api.post('/users', form)
    ElMessage.success('已创建')
    showCreate.value = false
    form.username = ''
    form.password = ''
    form.role = 'tester'
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function toggleActive(row) {
  await api.patch(`/users/${row.id}`, { is_active: !row.is_active })
  await load()
}

function openReset(row) {
  current.value = row
  resetPassword.value = ''
  showReset.value = true
}

async function resetPwd() {
  await api.patch(`/users/${current.value.id}`, { password: resetPassword.value })
  ElMessage.success('密码已重置')
  showReset.value = false
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.flat-table {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

.crumb-current {
  color: #ecfeff;
  font-size: 14px;
}
</style>
