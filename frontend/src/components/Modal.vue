<script setup></script>

<template>
  <teleport to="#modals">
    <div class="backdrop">
      <div class="modal" role="dialog" aria-modal="true">
        <slot></slot>
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
}
</style>
