<script setup>
import { computed, ref } from 'vue'

import config from '@/config'
import shorten from '@/composables/shortenUrl'
import validateUrl from '@/helpers/validateUrl'
import sleep from '@/helpers/sleep'
import { formatMessage } from '@/helpers/htmlUtils'

const showStatus = ref(false)
const showResult = ref(false)
const showHint = ref(false)
const showLoading = ref(false)
const targetUrl = ref('')
const hint = ref('')
const { shortUrl, message, errorCode, details, load } = shorten(
  config.backend.host,
  config.backend.endpoints.shorten,
)

const formattedMessage = computed(() => formatMessage(message.value))

const shortenUrl = () => {
  /**
   *  1. Validate the URL
   *  2. Fetch from API
   *  3. Show loading modal & block input
   *  4. Await fetch response
   *  5. If success, show result & show message
   *  6. If error, show error message & show error code
   *  7. Unblock input & hide loading modal
   */
  if (!targetUrl.value || !validateUrl(targetUrl.value)) {
    hint.value = config.hints.enterValidUrl
    showHint.value = true
    setTimeout(() => (showHint.value = false), config.hints.timeout)
    return
  }

  // TODO: show loading modal while waiting
  showLoading.value = true
  // TODO: remove sleep after implementing actual backend
  sleep(1000).then(() => {
    load(targetUrl.value)
      .then(() => {
        showLoading.value = false
        showResult.value = true
        showStatus.value = true
      })
      .catch(() => {
        showLoading.value = false
        showStatus.value = true
      })
  })
}
</script>

<template>
  <section class="shortener">
    <h1 class="headline">Shorten your link</h1>
    <div class="input-stack">
      <div class="input-shell">
        <div class="input-row">
          <input v-model="targetUrl" type="url" placeholder="Your URL" :disabled="showLoading" />
          <button class="submit" @click="shortenUrl" :disabled="showLoading">↑</button>
        </div>
      </div>
      <transition name="stack-slide" mode="out-in">
        <div v-if="showHint" class="hint stack-box">
          <p>{{ hint }}</p>
        </div>
        <div
          v-else-if="showStatus"
          class="status status-stack stack-box"
          :class="{ error: errorCode }"
        >
          <p class="message" v-html="formattedMessage"></p>
          <p v-if="errorCode" class="error-code">error code: {{ errorCode }}</p>
        </div>
      </transition>
    </div>
    <transition name="fade-rise">
      <div v-if="showResult" class="result">
        <a class="result-link" :href="shortUrl" target="_blank">{{ shortUrl }}</a>
        <p class="quota">Remaining quota: {{ details.remainingQuota }}</p>
      </div>
    </transition>
  </section>
</template>

<style scoped>
/* Container */
.shortener {
  max-width: 47.5rem;
  margin: 3rem auto;
  padding: 2rem 1.75rem 1.75rem;
  border-radius: 1.125rem;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-soft);
  color: #1e2430;
}

/* Headline */
.headline {
  margin: 0 0 1.375rem;
  font-size: clamp(1.9rem, 3vw, 2.6rem);
  font-weight: 700;
  font-family:
    'Poppins',
    system-ui,
    -apple-system,
    sans-serif;
  letter-spacing: -0.02em;
  text-align: center;
}

/* Input Shell */
.input-shell {
  position: relative;
  padding: 0.375rem;
  border-radius: 999px;
  background: #fff;
  isolation: isolate;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
  z-index: 1;
}

.input-shell:focus-within {
  transform: translateY(-0.0625rem);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

.input-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 0.125rem;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff8a2a, #ffd18a, #ff8a2a);
  background-size: 200% 100%;
  animation: border-flow 3s linear infinite;
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

/* Input Row */
.input-row {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 999px;
  padding: 0.5rem 0.625rem 0.5rem 1.125rem;
  box-shadow: inset 0 0 0 1px rgba(255, 147, 55, 0.12);
  transition: box-shadow 0.2s ease;
}

.input-row:focus-within {
  box-shadow: inset 0 0 0 1px rgba(255, 147, 55, 0.3);
}

.input-row input {
  flex: 1;
  border: none;
  outline: none;
  font-size: var(--text-lg);
  font-weight: 500;
  font-family: inherit;
  color: #1f2937;
  background: transparent;
}

.input-row input::placeholder {
  color: #8c96a6;
}

/* Submit Button */
.submit {
  border: none;
  background: #ff7a1a;
  color: #fff;
  font-size: var(--text-xl);
  font-weight: 600;
  padding: 0.625rem 1.125rem;
  border-radius: 999px;
  cursor: pointer;
  transition:
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.submit:hover:not(:disabled) {
  transform: translateY(-0.0625rem);
  box-shadow: 0 8px 16px rgba(255, 122, 26, 0.35);
}

.submit:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
  box-shadow: 0 4px 10px rgba(255, 122, 26, 0.25);
}

.submit:disabled,
.input-row input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* Status Box */
.status {
  margin-top: 0.875rem;
  margin-bottom: 1rem;
  padding: 0.375rem 0.625rem 0.3125rem;
  border-radius: 0 0 0.875rem 0.875rem;
  background: #e8f6ee;
  border: 1px solid #2f8f5b;
  color: #17663e;
  font-weight: 500;
  font-size: var(--text-xs);
  box-shadow: 0 6px 14px rgba(17, 24, 39, 0.06);
}

/* Stack Slot */
.stack-box {
  width: 85%;
  margin: 0.25rem auto 0;
  border-top: none;
  padding: 0.375rem 0.625rem 0.3125rem;
  font-size: var(--text-xs);
  line-height: 1.3;
  will-change: transform, opacity;
}

.stack-box p {
  margin: 0;
}

.status-stack {
  border-top: none;
}

.status.error {
  background: #fdecec;
  border-color: #c73b3b;
  color: #8e1f1f;
}

/* Status Details */
.error-code {
  margin-top: 0.375rem;
  color: #b91c1c;
  font-weight: 700;
}

/* Message Text */
.message {
  margin: 0;
  color: inherit;
}

.message-url {
  font-weight: 700;
  color: #2f2f2f;
  text-decoration: none;
  transition:
    color 0.2s ease,
    text-decoration-color 0.2s ease;
}

/* Hint Box */
.hint {
  border-radius: 0 0 0.875rem 0.875rem;
  background: #f3f4f6;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-top: none;
  color: #4b5563;
  box-shadow: 0 8px 18px rgba(17, 24, 39, 0.08);
  position: relative;
  z-index: 0;
}

/* Result Box */
.result {
  margin-top: 1rem;
  padding: 1rem 1.125rem;
  border-radius: 0.9rem;
  background: linear-gradient(135deg, rgba(228, 244, 255, 0.9), rgba(219, 236, 255, 0.9));
  color: #0f3d57;
  position: relative;
  text-align: center;
  border: 1px solid rgba(72, 131, 188, 0.18);
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.08),
    inset 0 0 0 1px rgba(255, 255, 255, 0.6);
  overflow: hidden;
}

.result::before,
.result::after {
  content: '';
  position: absolute;
  left: -20%;
  right: -20%;
  height: 140%;
  top: -20%;
  background: radial-gradient(
    circle at 20% 50%,
    rgba(255, 255, 255, 0.8),
    rgba(255, 255, 255, 0.08)
  );
  opacity: 0.55;
  pointer-events: none;
  animation: wave-flow 6s ease-in-out infinite;
}

.result::after {
  animation-delay: -2.8s;
  opacity: 0.35;
  transform: scale(1.2);
}

.result > * {
  position: relative;
  z-index: 1;
}

/* Result Link */
.result-link {
  color: inherit;
  font-weight: 700;
  text-decoration: none;
  font-size: clamp(1.5rem, 3.2vw, 2.15rem);
  display: inline-block;
  margin: 0.625rem 0 1.75rem;
  background-image: linear-gradient(currentColor, currentColor);
  background-position: 0 100%;
  background-size: 0 0.125rem;
  background-repeat: no-repeat;
  transition:
    transform 0.25s ease,
    background-size 0.25s ease;
}

.result-link:hover {
  background-size: 100% 2px;
  transform: translateY(-0.05rem);
}

/* Quota Text */
.quota {
  position: absolute;
  left: 50%;
  bottom: 0.75rem;
  font-size: var(--text-xs);
  color: #2c5a78;
  margin: 0;
  transform: translateX(-50%);
}

/* Keyframes */
@keyframes border-flow {
  to {
    background-position: 200% 0;
  }
}

@keyframes wave-flow {
  0% {
    transform: translateX(-12%) translateY(0);
  }
  50% {
    transform: translateX(12%) translateY(8%);
  }
  100% {
    transform: translateX(-12%) translateY(0);
  }
}

/* Transitions */
.stack-slide-enter-active,
.stack-slide-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.stack-slide-enter-from,
.stack-slide-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}

.stack-slide-enter-to,
.stack-slide-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* Responsive */
@media (max-width: 48rem) {
  .shortener {
    margin: 2.5rem 1.25rem;
    padding: 1.75rem 1.25rem 1.5rem;
  }

  .headline {
    font-size: clamp(1.6rem, 5vw, 2.2rem);
  }

  .input-row {
    padding: 0.5rem 0.5rem 0.5rem 0.9rem;
  }

  .submit {
    padding: 0.5rem 0.9rem;
  }

  .stack-box {
    width: 92%;
  }
}

@media (max-width: 30rem) {
  .shortener {
    margin: 2rem 1rem;
    padding: 1.5rem 1rem 1.25rem;
  }

  .input-row input {
    font-size: var(--text-base);
  }

  .submit {
    font-size: var(--text-lg);
  }

  .result-link {
    font-size: clamp(1.1rem, 6vw, 1.6rem);
    word-break: break-all;
  }
}

.fade-rise-enter-active,
.fade-rise-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.fade-rise-enter-from,
.fade-rise-leave-to {
  opacity: 0;
  transform: translateY(0.625rem);
}

.fade-rise-enter-to,
.fade-rise-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>
