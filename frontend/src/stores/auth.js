import { reactive } from 'vue'

export const ROLE_DEFAULT_PERMISSIONS = {
  admin: ['manage_users', 'manage_products', 'manage_versions', 'upload_files', 'download_files', 'delete_files'],
  developer: ['manage_products', 'manage_versions', 'upload_files', 'download_files', 'delete_files'],
  tester: ['download_files'],
}

const state = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

export function useAuth() {
  function setAuth(token, user) {
    state.token = token
    state.user = user
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
  }

  function clearAuth() {
    state.token = ''
    state.user = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  function updateCurrentUser(user) {
    if (state.user?.id !== user?.id) return
    state.user = user
    localStorage.setItem('user', JSON.stringify(user))
  }

  function hasPermission(permission) {
    if (!state.user) return false
    const permissions = Array.isArray(state.user.permissions)
      ? state.user.permissions
      : ROLE_DEFAULT_PERMISSIONS[state.user.role] || []
    return permissions.includes(permission)
  }

  function canUpload() {
    return hasPermission('upload_files')
  }

  function canDownload() {
    return hasPermission('download_files')
  }

  function canDeleteFiles() {
    return hasPermission('delete_files')
  }

  function canManageProducts() {
    return hasPermission('manage_products')
  }

  function canManageVersions() {
    return hasPermission('manage_versions')
  }

  function canManageUsers() {
    return hasPermission('manage_users')
  }

  return {
    state,
    setAuth,
    clearAuth,
    updateCurrentUser,
    hasPermission,
    canUpload,
    canDownload,
    canDeleteFiles,
    canManageProducts,
    canManageVersions,
    canManageUsers,
  }
}
