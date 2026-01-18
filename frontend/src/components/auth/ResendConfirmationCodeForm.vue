<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import Modal from '@/components/Modal.vue'

import { resendConfirmationCode } from '@/helpers/auth'
import { validateEmail } from '@/helpers/validations'

const router = useRouter()
const errorMessage = ref('')
const isLoading = ref(false)

const handleResendConfirmationCode = (event) => {
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
  resendConfirmationCode(email)
    .then(() => {
      router.push('/confirm-registration')
    })
    .catch((err) => {
      errorMessage.value = err?.message ?? config.auth.errorMessages.resendConfirmationCodeFailed
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
      <h3>Resend confirmation code</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleResendConfirmationCode">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" to="/confirm-registration">Back to confirmation</router-link>
            <button type="submit">Resend</button>
          </div>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>