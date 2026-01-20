<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { confirmPasswordReset } from '@/helpers/auth'
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

const handleConfirmPasswordReset = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const code = event.target.code.value
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
  }

  errorMessage.value = ''
  isLoading.value = true

  confirmPasswordReset(email, code, password)
    .then(() => {
      router.push({ name: 'login', query: { email: encodeURIComponent(email) } })
    })
    .catch((err) => {
      errorMessage.value = err?.message ?? config.auth.errorMessages.resetPasswordFailed
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
      <h3>Confirm password reset</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleConfirmPasswordReset">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" :value="email" required />
          </div>
          <div>
            <label for="code">Reset Code</label>
            <input type="text" id="code" name="code" required />
          </div>
          <div>
            <label for="password">New Password</label>
            <input type="password" id="password" name="password" required />
          </div>
          <div>
            <label for="passwordConfirm">Confirm New Password</label>
            <input type="password" id="passwordConfirm" name="passwordConfirm" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" :to="{ name: 'password-reset' }">
              Back to request
            </router-link>
            <button type="submit">Update Password</button>
          </div>
          <p class="auth-secondary-link">
            Didn't receive a reset code?<br />
            <router-link
              :to="{ name: 'password-reset', query: { email: encodeURIComponent(email) } }"
            >
              Request a new code
            </router-link>
          </p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
