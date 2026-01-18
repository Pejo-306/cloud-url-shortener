import { createRouter, createWebHistory } from 'vue-router'

import { isAuthenticated } from '@/helpers/auth'

import Home from '@/views/Home.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegistrationForm from '@/components/auth/RegistrationForm.vue'
import PasswordResetForm from '@/components/auth/PasswordResetForm.vue'

const routes = [
  { path: '/', components: { default: Home } },
  { path: '/login', components: { default: Home, modal: LoginForm } },
  { path: '/register', components: { default: Home, modal: RegistrationForm } },
  { path: '/password-reset', components: { default: Home, modal: PasswordResetForm } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (isAuthenticated()) {
    if (to.path === '/login' || to.path === '/register' || to.path === '/password-reset') {
      return '/'
    }
  } else if (to.path === '/') {
    return '/login'
  }
})

export default router
