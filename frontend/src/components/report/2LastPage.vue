<script setup>
import { computed } from "vue";

const props = defineProps({
  meta: { type: Object, required: true }, // Aggiunto per coerenza header
  rows: { type: Array, default: () => [] },
  pageNumber: { type: [String, Number], default: "" },
});

// Calcola la larghezza percentuale (0-10)
const normalizedRows = computed(() =>
  (props.rows || []).map((row) => {
    if (row.type !== "metric") return row;
    return {
      ...row,
      widthPercent: Math.max(0, Math.min(100, (row.score / 10) * 100)),
    };
  })
);

// Colori coerenti con la pagina "Interpretation Guide"
function getBarColor(score) {
  if (score <= 2) return "#ef4444";      // Red
  if (score <= 4) return "#f97316";      // Orange
  if (score <= 6) return "#facc15";      // Yellow
  if (score <= 8) return "#38bdf8";      // Light Blue
  return "#1d4ed8";                      // Dark Blue
}
</script>

<template>
  <div class="report-page-content">
    
    <header class="page-header">
      <div class="meta-left">
        <span class="brand">FRIA SYSTEM</span>
        <span class="sep">|</span>
        <span class="dataset">{{ meta.dataset_name }}</span>
      </div>
      <div class="meta-right">{{ meta.evaluation_date }}</div>
    </header>

    <div class="page-inner">
      <header class="title-block">
        <h1 class="page-title">Score Summary Overview</h1>
        <p class="page-subtitle">Aggregated evaluation results across all fundamental rights domains.</p>
      </header>

      <div class="scores-list">
        <template
          v-for="(row, index) in normalizedRows"
        >
          <div v-if="row.type === 'header'" :key="`header-${row.right}-${index}`" class="section-divider">
            <h2 class="section-title">
              {{ row.right }}
              <span v-if="row.continued" class="continued-tag">(continued)</span>
            </h2>
          </div>

          <div v-else :key="`metric-${row.right}-${index}`" class="bar-row">
            <div class="bar-info">
              <span class="bar-label">{{ row.label }}</span>
            </div>

            <div class="bar-visual">
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{
                    width: `${row.widthPercent}%`,
                    background: getBarColor(row.score)
                  }"
                ></div>
              </div>
              <div class="bar-value mono">
                {{ row.score.toFixed(2) }}
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;700&display=swap');

.report-page-content {
  height: 100%;
  padding: 20mm 20mm 15mm;
  box-sizing: border-box;
  position: relative;
  font-family: 'Inter', sans-serif;
  color: #1a202c;
  background: #fff;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
  margin-bottom: 15mm;
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
}
.sep { margin: 0 8px; color: #cbd5e1; }
.brand { color: #1e293b; font-weight: 800; }

/* Titles */
.title-block {
  text-align: left;
  margin-bottom: 12mm;
}

.page-title {
  font-family: 'Instrument Serif', serif;
  font-size: 42pt;
  line-height: 1;
  margin: 0 0 8px 0;
  font-weight: 400;
  color: #1e293b;
}

.page-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

/* Sections */
.section-divider {
  margin-top: 10mm;
  margin-bottom: 6mm;
  border-bottom: 2px solid #1e293b;
  padding-bottom: 4px;
}

.section-title {
  margin: 0;
  font-size: 12pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #1e293b;
}

.continued-tag {
  font-size: 10pt;
  font-weight: 400;
  color: #94a3b8;
  text-transform: none;
}

/* Rows & Bars */
.bar-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 5mm;
}

.bar-label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bar-visual {
  display: grid;
  grid-template-columns: 1fr 18mm;
  align-items: center;
  gap: 12px;
}

.bar-track {
  height: 6mm;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease-out;
}

.bar-value {
  font-size: 12pt;
  font-weight: 700;
  text-align: right;
  color: #1e293b;
}

.mono {
  font-family: monospace;
}

.page-number {
  position: absolute;
  bottom: 10mm;
  right: 20mm;
  font-size: 10px;
  font-family: monospace;
  color: #94a3b8;
}

@media print {
  .report-page-content { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>