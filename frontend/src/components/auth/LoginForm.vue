<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { validateEmail, validatePassword } from '@/helpers/validations'
import { login, persistSession } from '@/helpers/auth'

const router = useRouter()
const errorMessage = ref('')
const isLoading = ref(false)

const handleLogin = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const password = event.target.password.value
  
  // validate email and password
  const emailValidation = validateEmail(email)
  const passwordValidation = validatePassword(password)
  if (!emailValidation.valid || !passwordValidation.valid) {
    errorMessage.value = emailValidation.message || passwordValidation.message
    return
  } else {
    errorMessage.value = ''
  }

  isLoading.value = true
  login(email, password)
    .then((session) => {
      persistSession(session)
      router.replace('/')
    })
    .catch((err) => {
      errorMessage.value = err?.message ?? config.auth.errorMessages.loginFailed
      console.error(err)
    })
    .finally(() => {
      isLoading.value = false
    })
}
</script>

<template>
  <Modal :is-loading="isLoading">
    <div class="auth-modal">
      <h3>Login</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleLogin">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" required />
          </div>
          <div>
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" to="/password-reset"> Forgot password? </router-link>
            <button type="submit">Login</button>
          </div>
          <p class="auth-secondary-link">New? <router-link to="/register">Sign up</router-link></p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
