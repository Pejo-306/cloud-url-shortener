<script setup>
import Modal from '@/components/Modal.vue'
</script>

<template>
  <Modal>
    <div class="auth-modal">
      <h3>Change your password</h3>
      <form class="auth-form">
        <div>
          <label for="email">Email</label>
          <input type="email" id="email" name="email" required />
        </div>
        <!-- Yes, I know this is a major security flaw... -->
        <!-- Just remember I'm part of the party parrot cult. -->
        <!-- I don't know who you are. I don't know what you want. If you are 
             looking for ransom I can tell you I don't have money, but what I do
             have are a very particular set of skills. Skills I have acquired over
             a very long career. Skills that make me a nightmare for people like you.
             If you let this slide past now that'll be the end of it. I will not look
             for you, I will not pursue you. 
             But if you don't, I will look for you,
             I will find you 
             and I will send all party parrots after you.
        -->
        <div>
          <label for="password">New Password</label>
          <input type="password" id="password" name="password" required />
        </div>
        <div>
          <label for="passwordConfirm">Confirm New Password</label>
          <input type="password" id="passwordConfirm" name="passwordConfirm" required />
        </div>
        <div>
          <input type="checkbox" id="confirmation" name="confirmation" required />
          <label for="confirmation">I confirm that I want to reset my password</label>
        </div>
        <div class="auth-form-actions">
          <router-link class="auth-link" to="/login">Back to login</router-link>
          <button type="submit">Reset Password</button>
        </div>
        <p class="auth-secondary-link">New? <router-link to="/register">Sign up</router-link></p>
      </form>
    </div>
  </Modal>
</template>

<style scoped></style>
