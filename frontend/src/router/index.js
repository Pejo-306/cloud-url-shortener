import { createRouter, createWebHistory } from 'vue-router'

import { isAuthenticated } from '@/helpers/auth'

import Home from '@/views/Home.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegistrationForm from '@/components/auth/RegistrationForm.vue'
import ConfirmRegistrationForm from '@/components/auth/ConfirmRegistrationForm.vue'
import ResendConfirmationCodeForm from '@/components/auth/ResendConfirmationCodeForm.vue'
import PasswordResetForm from '@/components/auth/PasswordResetForm.vue'

const routes = [
  { path: '/', components: { default: Home } },
  { path: '/login', components: { default: Home, modal: LoginForm } },
  { path: '/register', components: { default: Home, modal: RegistrationForm } },
  { path: '/password-reset', components: { default: Home, modal: PasswordResetForm } },
  { path: '/confirm-registration', components: { default: Home, modal: ConfirmRegistrationForm } },
  { path: '/resend-confirmation-code', components: { default: Home, modal: ResendConfirmationCodeForm } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authFlows = ['/login', '/register', '/password-reset', '/confirm-registration', '/resend-confirmation-code']

  if (isAuthenticated()) {
    if (authFlows.includes(to.path)) {
      return '/'
    }
  } else if (to.path === '/') {
    return '/login'
  }
})

export default router
