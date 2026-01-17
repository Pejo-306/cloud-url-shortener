<script setup>
</script>

<template>
  <div class="backdrop">
    <div class="modal">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 100;
}

.modal {
  width: 400px;
  height: 200px;
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  margin: 100px auto;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>