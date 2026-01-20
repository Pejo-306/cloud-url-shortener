<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { confirmRegistration } from '@/helpers/auth'
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

const handleConfirmRegistration = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const code = event.target.code.value

  const emailValidation = validateEmail(email)
  if (!emailValidation.valid) {
    errorMessage.value = emailValidation.message
    return
  } else {
    errorMessage.value = ''
  }

  isLoading.value = true
  confirmRegistration(email, code)
    .then((success) => {
      if (success) {
        router.push({ name: 'login', query: { email: encodeURIComponent(email) } })
      } else {
        errorMessage.value = config.auth.errorMessages.confirmRegistrationFailed
      }
    })
    .catch((err) => {
      errorMessage.value = err?.message ?? config.auth.errorMessages.confirmRegistrationFailed
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
      <h3>Confirm your registration</h3>
      <transition name="auth-slide" mode="out-in">
        <div v-if="errorMessage" class="auth-error-box">
          <p>{{ errorMessage }}</p>
        </div>
      </transition>
      <form class="auth-form" @submit="handleConfirmRegistration">
        <fieldset :disabled="isLoading">
          <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" :value="email" required />
          </div>
          <div>
            <label for="code">Confirmation Code</label>
            <input type="text" id="code" name="code" required />
          </div>
          <div class="auth-form-actions">
            <router-link class="auth-link" :to="{ name: 'register' }">
              Back to registration
            </router-link>
            <button type="submit">Confirm</button>
          </div>
          <p class="auth-secondary-link">
            Didn't receive a confirmation code?<br />
            <router-link :to="`/resend-confirmation-code?email=${encodeURIComponent(email)}`">
              Resend confirmation code
            </router-link>
          </p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
