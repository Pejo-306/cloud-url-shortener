<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  router.replace({ name: 'login' })
})
</script>

<template>
  <span aria-live="polite">Redirecting...</span>
</template>

<style scoped></style>
