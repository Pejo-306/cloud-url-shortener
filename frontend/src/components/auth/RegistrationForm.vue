<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import Modal from '@/components/Modal.vue'

import config from '@/config'
import { register } from '@/helpers/auth'
import { validateEmail, validatePassword, validatePasswordConfirmation } from '@/helpers/validations'

const router = useRouter()
const errorMessage = ref('')
const isLoading = ref(false)

const handleRegister = (event) => {
  event.preventDefault()

  const email = event.target.email.value
  const password = event.target.password.value
  const passwordConfirm = event.target.passwordConfirm.value

  const emailValidation = validateEmail(email)
  const passwordValidation = validatePassword(password)
  const passwordConfirmationValidation = validatePasswordConfirmation(password, passwordConfirm)
  if (!emailValidation.valid || !passwordValidation.valid || !passwordConfirmationValidation.valid) {
    errorMessage.value = emailValidation.message || passwordValidation.message || passwordConfirmationValidation.message
    return
  } else {
    errorMessage.value = ''
  }

  isLoading.value = true
  register(email, password)
    .then((response) => {
      if (response.userConfirmed) {
        router.push('/login')
      } else {
        router.push('/confirm-registration')
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
            <input type="email" id="email" name="email" required />
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
            <router-link class="auth-link" to="/login">Back to login</router-link>
            <button type="submit">Register</button>
          </div>
          <p class="auth-secondary-link">Got a confirmation code? <router-link to="/confirm-registration">Confirm registration</router-link></p>
        </fieldset>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>

<!--
response:  
{user: CognitoUser2, userConfirmed: false, userSub: 'a3e4a872-b041-7041-da12-9309d90f3bfa', codeDeliveryDetails: {…}}
codeDeliveryDetails
: 
{AttributeName: 'email', DeliveryMedium: 'EMAIL', Destination: 'l***@e***'}
user
: 
CognitoUser2 {username: 'lambda123@example.com', pool: CognitoUserPool2, Session: null, client: Client2, signInUserSession: null, …}
userConfirmed
: 
false
userSub
: 
"a3e4a872-b041-7041-da12-9309d90f3bfa"
[[Prototype]]
: 
Object

-->