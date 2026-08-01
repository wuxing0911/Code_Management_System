import { reactive } from 'vue'

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

  function canUpload() {
    return state.user && ['admin', 'developer'].includes(state.user.role)
  }

  function isAdmin() {
    return state.user?.role === 'admin'
  }

  return { state, setAuth, clearAuth, canUpload, isAdmin }
}
