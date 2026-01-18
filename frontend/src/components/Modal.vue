<script setup>
const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false,
  },
})
</script>

<template>
  <teleport to="#modals">
    <div class="backdrop">
      <div class="modal" role="dialog" aria-modal="true" :class="{ 'is-loading': props.isLoading }">
        <div class="modal-content" :aria-busy="props.isLoading">
          <slot></slot>
          <div v-if="props.isLoading" class="modal-loading">
            <span class="modal-spinner"></span>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<style>
.backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 100;
}

.modal {
  width: 400px;
  max-width: 92vw;
  background: transparent;
  padding: 0;
  margin: 100px auto 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  position: relative;
}

.modal-content {
  width: 100%;
  position: relative;
}

.modal.is-loading .modal-content {
  pointer-events: none;
  user-select: none;
}

.modal-loading {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(2px);
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: grid;
  place-items: center;
  z-index: 1;
}

.modal-spinner {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 3px solid rgba(59, 130, 246, 0.25);
  border-top-color: #3b82f6;
  animation: modal-spin 1s linear infinite;
}

@keyframes modal-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
