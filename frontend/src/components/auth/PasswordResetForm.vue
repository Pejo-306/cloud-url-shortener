<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { requestPasswordReset } from '@/helpers/auth'
import { validateEmail } from '@/helpers/validations'

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

const handleRequestPasswordReset = (event) => {
  event.preventDefault()

  const email = event.target.email.value

  const emailValidation = validateEmail(email)
  if (!emailValidation.valid) {
    errorMessage.value = emailValidation.message
    return
  } else {
    errorMessage.value = ''
  }

  isLoading.value = true
  requestPasswordReset(email)
    .then(() => {
      router.push({ name: 'confirm-password-reset', query: { email: encodeURIComponent(email) } })
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
      <h3>Reset your password</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleRequestPasswordReset">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" :value="email" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" :to="`/login?email=${encodeURIComponent(email)}`">
              Back to login
            </router-link>
            <button type="submit">Send Reset Code</button>
          </div>
          <p class="auth-secondary-link">
            Already have a reset code?<br />
            <router-link
              :to="{ name: 'confirm-password-reset', query: { email: encodeURIComponent(email) } }"
            >
              Confirm password reset
            </router-link>
          </p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
