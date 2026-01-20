<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { register } from '@/helpers/auth'
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirmation,
} from '@/helpers/validations'

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

const handleRegister = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const password = event.target.password.value
  const passwordConfirm = event.target.passwordConfirm.value

  const emailValidation = validateEmail(email)
  const passwordValidation = validatePassword(password)
  const passwordConfirmationValidation = validatePasswordConfirmation(password, passwordConfirm)
  if (
    !emailValidation.valid ||
    !passwordValidation.valid ||
    !passwordConfirmationValidation.valid
  ) {
    errorMessage.value =
      emailValidation.message ||
      passwordValidation.message ||
      passwordConfirmationValidation.message
    return
  } else {
    errorMessage.value = ''
  }

  isLoading.value = true
  register(email, password)
    .then((response) => {
      if (response.userConfirmed) {
        router.push({ name: 'login', query: { email: encodeURIComponent(email) } })
      } else {
        router.push({ name: 'confirm-registration', query: { email: encodeURIComponent(email) } })
      }
    })
    .catch((err) => {
      errorMessage.value = err?.message ?? config.auth.errorMessages.registerFailed
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
      <h3>Sign up for a new account</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleRegister">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" :value="email" required />
          </div>
          <div>
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required />
          </div>
          <div>
            <label for="passwordConfirm">Confirm Password</label>
            <input type="password" id="passwordConfirm" name="passwordConfirm" required />
          </div>
          <div>
            <input type="checkbox" id="terms" name="terms" required />
            <label for="terms"
              >I agree to the <a href="#">terms of service</a> and
              <a href="#">privacy policy</a></label
            >
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" :to="{ name: 'login' }">Back to login</router-link>
            <button type="submit">Register</button>
          </div>
          <p class="auth-secondary-link">
            Got a confirmation code?
            <router-link :to="{ name: 'confirm-registration' }">Confirm registration</router-link>
          </p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
