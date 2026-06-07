import config from '@/config'
import { clearSession, getSession, isAuthenticated, persistSession } from '@/helpers/session'

const loadAuthProvider = async () => {
  const authProvider = config.backend.cloudProvider || 'aws'
  switch (authProvider) {
    case 'gcp':
      return import('@/gcp/auth')
    case 'aws':
    default:
      return import('@/helpers/auth')
  }
}

const auth = await loadAuthProvider()

export const isGcpAuthProvider = config.backend.cloudProvider === 'gcp'
export const confirmPasswordReset = auth.confirmPasswordReset
export const confirmRegistration = auth.confirmRegistration
export const login = auth.login
export const logout = auth.logout
export const register = auth.register
export const requestPasswordReset = auth.requestPasswordReset
export const resendConfirmationCode = auth.resendConfirmationCode

export { clearSession, getSession, isAuthenticated, persistSession }
