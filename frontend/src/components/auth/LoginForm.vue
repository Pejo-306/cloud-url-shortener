<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { validateEmail, validatePassword } from '@/helpers/validations'
import { login, persistSession } from '@/helpers/auth'

const email = ref('')
const router = useRouter()
const route = useRoute()
const errorMessage = ref('')
const isLoading = ref(false)

// Populate email field from query parameter
onMounted(() => {
  const emailParam = route.query.email
  if (emailParam) {
    email.value = decodeURIComponent(emailParam)
  }
})

const handleLogin = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const password = event.target.password.value

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
      router.replace({ name: 'home' })
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
            <input type="email" id="email" name="email" :value="email" required />
          </div>
          <div>
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" :to="{ name: 'password-reset' }">
              Forgot password?
            </router-link>
            <button type="submit">Login</button>
          </div>
          <p class="auth-secondary-link">
            New? <router-link :to="{ name: 'register' }">Sign up</router-link>
          </p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
