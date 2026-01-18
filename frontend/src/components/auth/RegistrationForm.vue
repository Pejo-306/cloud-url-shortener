<script setup>
import Modal from '@/components/Modal.vue'
</script>

<template>
  <Modal>
    <div class="auth-modal">
      <h3>Sign up for a new account</h3>
      <form class="auth-form">
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
      </form>
    </div>
  </Modal>
</template>
