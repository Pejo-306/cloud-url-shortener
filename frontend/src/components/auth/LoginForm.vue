<script setup>
import Modal from '@/components/Modal.vue'
</script>

<template>
  <Modal>
    <div class="auth-modal">
      <h3>Login</h3>
      <form class="auth-form">
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
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
