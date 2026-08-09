<template>
  <AppLayout>
    <template #crumb>
      <span class="crumb-current">用户管理</span>
    </template>

    <div class="toolbar">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">角色提供默认权限，也可以为每个人员单独调整具体权限。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-table :data="users" stripe class="flat-table">
      <el-table-column prop="username" label="用户名" min-width="130" />
      <el-table-column label="角色" width="110">
        <template #default="{ row }">{{ roleMap[row.role] || row.role }}</template>
      </el-table-column>
      <el-table-column label="具体权限" min-width="360">
        <template #default="{ row }">
          <div class="permission-tags">
            <el-tag v-for="permission in row.permissions" :key="permission" size="small" effect="plain">
              {{ permissionMap[permission] || permission }}
            </el-tag>
            <span v-if="!row.permissions?.length" class="no-permission">无操作权限</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">{{ row.is_active ? '启用' : '禁用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" align="center">
        <template #default="{ row }">
          <el-button text type="primary" @click="openEdit(row)">角色与权限</el-button>
          <el-button text type="primary" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
          <el-button text type="primary" @click="openReset(row)">重置密码</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建用户" width="580px">
      <el-form label-position="top">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" @change="applyRoleDefaults(form)">
            <el-option v-for="option in roleOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <PermissionPicker v-model="form.permissions" />
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createUser">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" title="修改角色与权限" width="580px">
      <el-form label-position="top">
        <el-form-item label="用户名"><el-input :model-value="editForm.username" disabled /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%" @change="onEditRoleChange">
            <el-option v-for="option in roleOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="具体权限">
          <el-checkbox-group v-model="editForm.permissions" class="permission-grid">
            <el-checkbox
              v-for="item in permissionOptions"
              :key="item.value"
              :value="item.value"
              :disabled="editForm.id === state.user?.id && item.value === 'manage_users'"
              border
            >
              <span class="permission-option">
                <strong>{{ item.label }}</strong>
                <small>{{ item.description }}</small>
              </span>
            </el-checkbox>
          </el-checkbox-group>
          <p v-if="editForm.id === state.user?.id" class="self-tip">为避免失去管理入口，不能移除自己的用户管理权限。</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="updateUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReset" title="重置密码" width="420px">
      <el-input v-model="resetPassword" type="password" show-password placeholder="新密码（至少 4 位）" />
      <template #footer>
        <el-button @click="showReset = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="resetPwd">确定</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { defineComponent, h, onMounted, reactive, ref } from 'vue'
import { ElCheckbox, ElCheckboxGroup, ElFormItem, ElMessage } from 'element-plus'
import api from '../api'
import AppLayout from '../components/AppLayout.vue'
import { ROLE_DEFAULT_PERMISSIONS, useAuth } from '../stores/auth'

const permissionOptions = [
  { value: 'manage_users', label: '用户管理', description: '创建人员、修改角色权限、启停账号和重置密码' },
  { value: 'manage_products', label: '产品管理', description: '新建、编辑和删除产品' },
  { value: 'manage_versions', label: '版本管理', description: '新建、编辑和删除版本' },
  { value: 'upload_files', label: '文件上传', description: '上传程序代码和界面工程' },
  { value: 'download_files', label: '文件下载', description: '下载文件、文件夹及整版本' },
  { value: 'delete_files', label: '文件删除', description: '删除单个或批量文件和文件夹' },
]

const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'developer', label: '开发' },
  { value: 'tester', label: '测试' },
]

const roleMap = Object.fromEntries(roleOptions.map((item) => [item.value, item.label]))
const permissionMap = Object.fromEntries(permissionOptions.map((item) => [item.value, item.label]))

const PermissionPicker = defineComponent({
  props: { modelValue: { type: Array, required: true } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h(ElFormItem, { label: '具体权限' }, () =>
        h(
          ElCheckboxGroup,
          {
            modelValue: props.modelValue,
            'onUpdate:modelValue': (value) => emit('update:modelValue', value),
            class: 'permission-grid',
          },
          () =>
            permissionOptions.map((item) =>
              h(
                ElCheckbox,
                { key: item.value, value: item.value, border: true },
                () => h('span', { class: 'permission-option' }, [h('strong', item.label), h('small', item.description)]),
              ),
            ),
        ),
      )
  },
})

const { state, updateCurrentUser } = useAuth()
const users = ref([])
const showCreate = ref(false)
const showEdit = ref(false)
const showReset = ref(false)
const saving = ref(false)
const resetPassword = ref('')
const current = ref(null)
const form = reactive({ username: '', password: '', role: 'tester', permissions: [] })
const editForm = reactive({ id: null, username: '', role: 'tester', permissions: [] })

function roleDefaults(role) {
  return [...(ROLE_DEFAULT_PERMISSIONS[role] || [])]
}

function applyRoleDefaults(target) {
  target.permissions = roleDefaults(target.role)
}

async function load() {
  const { data } = await api.get('/users')
  users.value = data
}

function openCreate() {
  Object.assign(form, { username: '', password: '', role: 'tester', permissions: roleDefaults('tester') })
  showCreate.value = true
}

async function createUser() {
  saving.value = true
  try {
    await api.post('/users', form)
    ElMessage.success('用户已创建')
    showCreate.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

function openEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    username: row.username,
    role: row.role,
    permissions: [...(row.permissions || roleDefaults(row.role))],
  })
  showEdit.value = true
}

function onEditRoleChange() {
  editForm.permissions = roleDefaults(editForm.role)
  if (editForm.id === state.user?.id && !editForm.permissions.includes('manage_users')) {
    editForm.permissions.push('manage_users')
  }
}

async function updateUser() {
  saving.value = true
  try {
    const { data } = await api.patch(`/users/${editForm.id}`, {
      role: editForm.role,
      permissions: editForm.permissions,
    })
    updateCurrentUser(data)
    ElMessage.success('角色与权限已更新')
    showEdit.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  try {
    const { data } = await api.patch(`/users/${row.id}`, { is_active: !row.is_active })
    updateCurrentUser(data)
    await load()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '状态修改失败')
  }
}

function openReset(row) {
  current.value = row
  resetPassword.value = ''
  showReset.value = true
}

async function resetPwd() {
  saving.value = true
  try {
    await api.patch(`/users/${current.value.id}`, { password: resetPassword.value })
    ElMessage.success('密码已重置')
    showReset.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '密码重置失败')
  } finally {
    saving.value = false
  }
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
  color: var(--color-muted);
  font-size: 14px;
}

.permission-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.no-permission,
.self-tip {
  color: var(--color-muted);
  font-size: 12px;
}

.self-tip {
  width: 100%;
  margin: 8px 0 0;
}

:deep(.permission-grid) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

:deep(.permission-grid .el-checkbox) {
  width: 100%;
  height: auto;
  min-height: 58px;
  margin: 0;
  padding: 10px 12px;
  align-items: flex-start;
}

:deep(.permission-grid .el-checkbox__input) {
  margin-top: 3px;
}

:deep(.permission-grid .el-checkbox__label) {
  min-width: 0;
  white-space: normal;
}

.permission-option strong,
.permission-option small {
  display: block;
}

.permission-option small {
  margin-top: 2px;
  color: var(--color-muted);
  font-size: 11px;
  line-height: 1.35;
}

@media (max-width: 640px) {
  :deep(.permission-grid) {
    grid-template-columns: 1fr;
  }
}
</style>
