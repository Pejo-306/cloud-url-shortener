import { createRouter, createWebHistory } from 'vue-router'

import { isAuthenticated, logout } from '@/helpers/auth'

import Home from '@/views/Home.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegistrationForm from '@/components/auth/RegistrationForm.vue'
import ConfirmRegistrationForm from '@/components/auth/ConfirmRegistrationForm.vue'
import ResendConfirmationCodeForm from '@/components/auth/ResendConfirmationCodeForm.vue'
import PasswordResetForm from '@/components/auth/PasswordResetForm.vue'
import ConfirmPasswordResetForm from '@/components/auth/ConfirmPasswordResetForm.vue'

const routes = [
  {
    path: '/',
    components: { default: Home },
    name: 'home',
  },
  {
    path: '/login',
    components: { default: Home, modal: LoginForm },
    name: 'login',
  },
  {
    path: '/logout',
    redirect: () => {
      logout()
      return '/'
    },
    name: 'logout',
  },
  {
    path: '/register',
    components: { default: Home, modal: RegistrationForm },
    name: 'register',
  },
  {
    path: '/password-reset',
    components: { default: Home, modal: PasswordResetForm },
    name: 'password-reset',
  },
  {
    path: '/confirm-password-reset',
    components: { default: Home, modal: ConfirmPasswordResetForm },
    name: 'confirm-password-reset',
  },
  {
    path: '/confirm-registration',
    components: { default: Home, modal: ConfirmRegistrationForm },
    name: 'confirm-registration',
  },
  {
    path: '/resend-confirmation-code',
    components: { default: Home, modal: ResendConfirmationCodeForm },
    name: 'resend-confirmation-code',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authFlows = [
    'login',
    'register',
    'password-reset',
    'confirm-password-reset',
    'confirm-registration',
    'resend-confirmation-code',
  ]

  if (isAuthenticated()) {
    if (authFlows.includes(to.name)) {
      return { name: 'home' }
    }
  } else if (to.name === 'home') {
    return { name: 'login' }
  }
})

export default router
