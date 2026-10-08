<script setup lang="ts">
import { ref } from 'vue'
import { createSuperResolution, uploadStudy, type Job, type Study } from './api/client'

const study = ref<Study | null>(null)
const job = ref<Job | null>(null)
const busy = ref(false)
const error = ref('')

async function onUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  busy.value = true
  error.value = ''
  try {
    study.value = await uploadStudy(file)
    job.value = null
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

async function onSuperResolve() {
  if (!study.value) return
  busy.value = true
  error.value = ''
  try {
    job.value = await createSuperResolution(study.value.id)
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="shell">
    <header>
      <div><span class="eyebrow">RESEARCH WORKSPACE</span><h1>MRI Agent</h1><p>医学 MRI 超分辨率工作台</p></div>
      <span class="badge">演示环境</span>
    </header>
    <section class="hero">
      <div><h2>从影像到可追踪的增强任务</h2><p>上传一份脱敏影像，创建超分辨率任务，并通过 Agent 获取流程建议。</p></div>
      <div class="hero-mark">MRI<br /><small>SR</small></div>
    </section>
    <section class="grid">
      <div class="card">
        <h3>01 · 上传影像</h3>
        <label class="drop"><input type="file" accept="image/*,.nii,.nii.gz,.dcm" @change="onUpload" /><strong>选择 MRI 文件</strong><span>PNG / JPEG / TIFF / DICOM / NIfTI</span></label>
        <div v-if="study" class="file">{{ study.filename }}<small>{{ Math.round(study.size_bytes / 1024) }} KB · {{ study.status }}</small></div>
      </div>
      <div class="card">
        <h3>02 · 创建增强任务</h3>
        <p class="muted">当前使用可替换的 Lanczos 基线管线。接入训练模型后可在后端配置模型权重。</p>
        <button :disabled="!study || busy" @click="onSuperResolve">{{ busy ? '处理中…' : '创建 2× 超分任务' }}</button>
        <div v-if="job" class="status"><span class="dot" :class="job.status" />{{ job.status }}<small v-if="job.error">{{ job.error }}</small></div>
      </div>
      <div class="card agent">
        <h3>03 · Agent 助手</h3><p>Agent 会帮助你规划处理步骤，并提示研究与临床安全边界。</p>
        <div class="message">请先上传影像，再告诉我你希望进行的处理。</div>
        <div class="safety">研究用途提示：超分结果不能替代影像科医生诊断。</div>
      </div>
    </section>
    <div v-if="error" class="error">{{ error }}</div>
  </main>
</template>
