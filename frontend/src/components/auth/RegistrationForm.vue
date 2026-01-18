<script setup>
import { ref } from 'vue'
import Modal from '@/components/Modal.vue'

import { register } from '@/helpers/auth'

const isLoading = ref(false)

const handleRegister = (event) => {
  event.preventDefault()
  const email = event.target.email.value
  const password = event.target.password.value
  const passwordConfirm = event.target.passwordConfirm.value
  // TODO: validate email and password
  // TODO: validate password confirmation
  isLoading.value = true
  register(email, password)
  isLoading.value = false
  // TODO: handle register response
  // TODO: mark as authenticated, redirect router to home
}
</script>

<template>
  <Modal :is-loading="isLoading">
    <div class="auth-modal">
      <h3>Sign up for a new account</h3>
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
        </fieldset>
      </form>
    </div>
  </Modal>
</template>
