export const isAuthenticated = () => {
  const accessToken = localStorage.getItem('session.accessToken')
  const idToken = localStorage.getItem('session.idToken')
  const refreshToken = localStorage.getItem('session.refreshToken')
  const expiresAt = Number(localStorage.getItem('session.expiresAt'))

  if (Date.now() >= expiresAt) {
    clearSession()
    return false
  }
  return accessToken && idToken && refreshToken && expiresAt
}

export const getSession = () => {
  const accessToken = localStorage.getItem('session.accessToken')
  const idToken = localStorage.getItem('session.idToken')
  const refreshToken = localStorage.getItem('session.refreshToken')
  return { accessToken, idToken, refreshToken }
}

export const persistSession = (session) => {
  const expiresAt = Date.now() + session.expiresIn

  localStorage.setItem('session.accessToken', session.accessToken)
  localStorage.setItem('session.idToken', session.idToken)
  localStorage.setItem('session.refreshToken', session.refreshToken)
  localStorage.setItem('session.expiresAt', String(expiresAt))
}

export const clearSession = () => {
  localStorage.removeItem('session.accessToken')
  localStorage.removeItem('session.idToken')
  localStorage.removeItem('session.refreshToken')
  localStorage.removeItem('session.expiresAt')
}
