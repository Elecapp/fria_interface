<script setup>
const props = defineProps({
  meta: {
    type: Object,
    required: true,
  },
  pageNumber: {
    type: [Number, String],
    default: 1
  }
});
</script>

<template>
  <div class="cover">
    <div class="brand-tag">FRIA SYSTEM — RIGHTS & AI</div>

    <div class="center-content">
      <h1 class="title">Final Evaluation<br />Report</h1>
      <div class="divider"></div>
      <p class="subtitle">AI Impact Assessment on Fundamental Rights</p>
    </div>

    <div class="bottom-metadata">
      <div class="meta-item">
        <span class="meta-label">Evaluation Date</span>
        <span class="meta-value">{{ meta.evaluation_date }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Dataset Analyzed</span>
        <span class="meta-value">{{ meta.dataset_name }}</span>
      </div>
      <div class="meta-item" v-if="meta.evaluator">
        <span class="meta-label">Issued By</span>
        <span class="meta-value">{{ meta.evaluator }}</span>
      </div>
    </div>

    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
/* Importazione font se non presenti globalmente */
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;800&display=swap');

.cover {
  width: 100%;
  height: 100%;
  background-color: #1a202c; /* Slate molto scuro / Navy */
  color: #f8fafc;
  position: relative;
  font-family: 'Inter', sans-serif;
  box-sizing: border-box;
  padding: 60px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.brand-tag {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #94a3b8;
  border-left: 2px solid #3b82f6;
  padding-left: 12px;
}

.center-content {
  text-align: left;
  margin-top: -40px; /* Bilanciamento ottico */
}

.title {
  font-family: 'Instrument Serif', serif;
  font-size: 72px;
  line-height: 0.95;
  font-weight: 400;
  margin: 0;
  color: #fff;
}

.divider {
  width: 80px;
  height: 4px;
  background-color: #3b82f6; /* Accento blu */
  margin: 30px 0;
}

.subtitle {
  font-size: 20px;
  font-weight: 400;
  color: #94a3b8;
  max-width: 400px;
  line-height: 1.4;
}

.bottom-metadata {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px;
  padding-bottom: 40px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-label {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #64748b;
}

.meta-value {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.page-number {
  position: absolute;
  bottom: 20px;
  right: 60px;
  font-family: monospace;
  font-size: 11px;
  color: #475569;
}

/* Ottimizzazione per la stampa PDF */
@media print {
  .cover {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
</style>