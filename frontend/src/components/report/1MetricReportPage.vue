<script setup>
const props = defineProps({
  meta: { type: Object, required: true },
  pageNumber: { type: [String, Number], default: 2 },
});
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="meta-left">
        <span class="brand">FRIA SYSTEM</span>
        <span class="sep">|</span>
        <span class="dataset">{{ meta.dataset_name }}</span>
      </div>
      <div class="meta-right">{{ meta.evaluation_date }}</div>
    </header>

    <div class="title-section">
      <h1 class="h1">Interpretation Guide</h1>
      <h2 class="h2">
        A reference key to interpreting the quantitative results and the Contextual Impact (Gravity) obtained during the algorithmic evaluation.
      </h2>
    </div>

    <div class="legend-container">
      
      <div class="legend-row">
        <div class="color-indicator"><div class="dot red"></div></div>
        <div class="score-info">
          <div class="score-name">Low Score</div>
          <div class="score-range">0.0 – 2.0</div>
        </div>
        <div class="description">
          <strong>Critical:</strong> Strong evidence of violations or significant risks to fundamental rights. Immediate mitigation measures and model redesign are required.
        </div>
      </div>

      <div class="legend-row">
        <div class="color-indicator"><div class="dot orange"></div></div>
        <div class="score-info">
          <div class="score-name">Low-Medium</div>
          <div class="score-range">2.01 – 4.0</div>
        </div>
        <div class="description">
          <strong>Problematic:</strong> Notable imbalances or vulnerabilities detected. Acceptable only as a preliminary stage; requires a thorough review of the dataset or model parameters.
        </div>
      </div>

      <div class="legend-row">
        <div class="color-indicator"><div class="dot yellow"></div></div>
        <div class="score-info">
          <div class="score-name">Medium Score</div>
          <div class="score-range">4.01 – 6.0</div>
        </div>
        <div class="description">
          <strong>Moderate:</strong> Consistent with core principles, but with visible room for optimization. The system is considered compliant but remains under active monitoring.
        </div>
      </div>

      <div class="legend-row">
        <div class="color-indicator"><div class="dot lightblue"></div></div>
        <div class="score-info">
          <div class="score-name">Medium-High</div>
          <div class="score-range">6.01 – 8.0</div>
        </div>
        <div class="description">
          <strong>Good:</strong> High level of consistency with fundamental rights. Minor optimizations may be suggested to reach the top-tier compliance level.
        </div>
      </div>

      <div class="legend-row">
        <div class="color-indicator"><div class="dot blue"></div></div>
        <div class="score-info">
          <div class="score-name">High Score</div>
          <div class="score-range">8.01 – 10.0</div>
        </div>
        <div class="description">
          <strong>Optimal:</strong> Fully compliant. No evidence of risk emerges from this metric. The system meets the highest requirements for fairness and privacy.
        </div>
      </div>

    </div>

    <div class="page-number">{{ pageNumber }}</div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap');

.page {
  height: 100%;
  padding: 20mm 20mm 15mm;
  box-sizing: border-box;
  position: relative;
  font-family: 'Inter', sans-serif;
  color: #1a202c;
  background: white;
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

/* Titoli */
.title-section { margin-bottom: 12mm; }
.h1 {
  font-family: 'Instrument Serif', serif;
  font-size: 48px;
  line-height: 1;
  margin: 0 0 12px 0;
  font-weight: 400;
  color: #1e293b;
}
.h2 {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
  color: #64748b;
  max-width: 80%;
}

/* Legenda */
.legend-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-row {
  display: grid;
  grid-template-columns: 40px 140px 1fr;
  align-items: center;
  padding: 18px 0;
  border-bottom: 1px solid #f1f5f9;
}

.dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.05);
}

.red { background: #ef4444; }
.orange { background: #f97316; }
.yellow { background: #facc15; }
.lightblue { background: #38bdf8; }
.blue { background: #1d4ed8; }

.score-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}
.score-range {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  font-family: monospace;
}

.description {
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
}
.description strong { color: #1e293b; }

.page-number {
  position: absolute;
  bottom: 10mm;
  right: 20mm;
  font-size: 10px;
  font-family: monospace;
  color: #94a3b8;
}

@media print {
  .page { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>