<script setup>
import { computed, defineEmits, defineProps, ref } from 'vue'

import { pickLoadingMessage, pickParrot } from '@/helpers/parrots'
import Modal from '@/components/Modal.vue'

const emit = defineEmits(['close'])
const props = defineProps({
  disableInput: {
    type: Boolean,
    required: true,
  },
  status: {
    type: String,
    default: 'loading',
    validator: (value) => ['loading', 'success', 'fail'].includes(value),
  },
})

const closeModal = () => {
  emit('close')
}

const statusText = computed(() => {
  if (props.status === 'success') {
    return 'Success'
  }
  if (props.status === 'fail') {
    return 'Fail'
  }
  return loadingText.value
})

const statusClass = computed(() => `is-${props.status}`)

const loadingText = ref(pickLoadingMessage())
const parrotSrc = ref(pickParrot())
</script>

<template>
  <Modal>
    <div class="loading-card">
      <div class="loading-modal">
        <div class="loading-shell" :class="statusClass">
          <div class="status-mark" aria-hidden="true">
            <span v-if="props.status === 'loading'" class="spinner"></span>
            <svg
              v-else-if="props.status === 'success'"
              class="status-icon success"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M4 12l5 5 11-11" />
            </svg>
            <svg
              v-else
              class="status-icon fail"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </div>
          <div class="loading-message">
            <p>{{ statusText }}</p>
          </div>
        </div>
        <div class="loading-gif">
          <img :src="parrotSrc" alt="Dancing party parrot" />
        </div>
        <button v-if="!disableInput" class="end-party" @click="closeModal">End Party :(</button>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
:deep(.backdrop) {
  background: rgba(2, 3, 8, 0.9);
  backdrop-filter: blur(10px);
}

.loading-card {
  width: 100%;
  min-height: 440px;
  background: radial-gradient(circle at top, rgba(20, 30, 45, 0.9), #0b0f14 65%);
  border-radius: 10px;
  padding: 24px;
  margin: 7vh auto 0;
  display: flex;
  justify-content: center;
  align-items: stretch;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 24px 60px rgba(2, 6, 16, 0.55),
    0 0 0 1px rgba(255, 255, 255, 0.03);
}

.loading-modal {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  color: #eef2ff;
  text-align: center;
  position: relative;
}

.loading-modal::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(255, 140, 50, 0.5), rgba(88, 125, 255, 0.2));
  opacity: 0.3;
  pointer-events: none;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}

.loading-modal::after {
  content: '';
  position: absolute;
  inset: 12px;
  border-radius: 14px;
  background:
    radial-gradient(circle at 20% 20%, rgba(79, 135, 255, 0.2), transparent 45%),
    radial-gradient(circle at 80% 30%, rgba(255, 90, 160, 0.22), transparent 40%),
    radial-gradient(circle at 35% 80%, rgba(255, 196, 88, 0.2), transparent 45%),
    radial-gradient(circle at 75% 75%, rgba(108, 246, 162, 0.18), transparent 45%);
  opacity: 0.5;
  mix-blend-mode: screen;
  pointer-events: none;
  animation: disco-sweep 3.2s ease-in-out infinite;
}

.loading-shell {
  width: 100%;
  min-height: 68px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 1rem;
  padding: 0.45rem 1.1rem;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(14, 22, 36, 0.95), rgba(10, 15, 24, 0.85));
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.02),
    0 12px 26px rgba(4, 8, 16, 0.35);
}

.loading-shell.is-success {
  background: linear-gradient(135deg, rgba(11, 40, 27, 0.95), rgba(8, 24, 18, 0.9));
  border-color: rgba(74, 222, 128, 0.25);
}

.loading-shell.is-fail {
  background: linear-gradient(135deg, rgba(45, 12, 14, 0.95), rgba(24, 8, 10, 0.9));
  border-color: rgba(248, 113, 113, 0.25);
}

.status-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.05);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.spinner {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.18);
  border-top-color: #ff8a2a;
  border-right-color: #ffb369;
  animation: spin 1s linear infinite;
}

.status-icon {
  width: 22px;
  height: 22px;
}

.status-icon.success {
  color: #38f2a1;
  filter: drop-shadow(0 0 6px rgba(56, 242, 161, 0.45));
}

.status-icon.fail {
  color: #ff6b6b;
  filter: drop-shadow(0 0 6px rgba(255, 107, 107, 0.45));
}

.loading-message p {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-align: left;
}

.loading-gif {
  width: 100%;
  flex: 1;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.08), transparent 60%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
  padding: 1rem;
}

.loading-gif img {
  width: min(220px, 60vw);
  height: auto;
  image-rendering: auto;
  filter: drop-shadow(0 12px 18px rgba(0, 0, 0, 0.35));
  animation:
    groove-fast 0.7s ease-in-out infinite,
    frame-jitter 0.35s steps(2, end) infinite;
}

.end-party {
  border: none;
  background: linear-gradient(135deg, #ff7a1a, #ff9b3d);
  color: #0b0f14;
  font-size: 1rem;
  font-weight: 700;
  padding: 0.7rem 1.5rem;
  border-radius: 16px;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
  box-shadow:
    0 10px 24px rgba(255, 122, 26, 0.35),
    inset 0 0 0 1px rgba(255, 255, 255, 0.2);
  animation: pulse-club 0.55s ease-in-out infinite;
}

.end-party:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
}

.end-party:active {
  transform: translateY(0) scale(0.98);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes groove-fast {
  0%,
  100% {
    transform: translateY(0) scale(1) rotate(0deg);
  }
  50% {
    transform: translateY(-6px) scale(1.05) rotate(-2deg);
  }
}

@keyframes frame-jitter {
  0% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(1px, -1px);
  }
  100% {
    transform: translate(-1px, 1px);
  }
}

@keyframes pulse-club {
  0% {
    transform: scale(1) translateY(0);
    box-shadow: 0 10px 24px rgba(255, 122, 26, 0.35);
  }
  25% {
    transform: scale(1.06) translateY(-2px) rotate(-1deg);
    box-shadow: 0 16px 30px rgba(255, 122, 26, 0.55);
  }
  55% {
    transform: scale(0.98) translateY(1px) rotate(1deg);
    box-shadow: 0 8px 18px rgba(255, 122, 26, 0.3);
  }
  100% {
    transform: scale(1) translateY(0);
    box-shadow: 0 10px 24px rgba(255, 122, 26, 0.35);
  }
}

@keyframes disco-sweep {
  0% {
    transform: translateX(-4%) translateY(2%);
    opacity: 0.35;
  }
  50% {
    transform: translateX(3%) translateY(-3%);
    opacity: 0.6;
  }
  100% {
    transform: translateX(-4%) translateY(2%);
    opacity: 0.35;
  }
}
</style>
