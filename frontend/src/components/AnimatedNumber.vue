<template>
  <span class="animated-number" :aria-label="String(targetValue)">{{ displayValue }}</span>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  value: {
    type: Number,
    default: 0,
  },
  from: {
    type: Number,
    default: 0,
  },
  duration: {
    type: Number,
    default: 800,
  },
})

const displayValue = ref(Math.round(props.from))
const targetValue = ref(Math.round(props.value))
let animationFrame = 0
let mounted = false

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function stopAnimation() {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
    animationFrame = 0
  }
}

function animateTo(value) {
  stopAnimation()
  const target = Math.max(0, Math.round(Number(value) || 0))
  const start = displayValue.value
  targetValue.value = target

  if (start === target || props.duration <= 0 || prefersReducedMotion()) {
    displayValue.value = target
    return
  }

  const startedAt = performance.now()
  const distance = target - start

  function tick(now) {
    const progress = Math.min((now - startedAt) / props.duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    displayValue.value = Math.round(start + distance * eased)
    if (progress < 1) {
      animationFrame = requestAnimationFrame(tick)
    } else {
      animationFrame = 0
      displayValue.value = target
    }
  }

  animationFrame = requestAnimationFrame(tick)
}

watch(
  () => props.value,
  (value) => {
    if (mounted) animateTo(value)
  },
)

onMounted(() => {
  mounted = true
  displayValue.value = Math.max(0, Math.round(props.from))
  animateTo(props.value)
})

onBeforeUnmount(stopAnimation)
</script>

<style scoped>
.animated-number {
  display: inline-block;
  min-width: 1ch;
  font-variant-numeric: tabular-nums;
}
</style>
