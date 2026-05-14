<script setup>
import { computed } from "vue";

const props = defineProps({
  node: { type: Object, required: true },
  meta: { type: Object, default: () => ({}) },
  metricKey: { type: String, default: "" },
  featureKey: { type: String, default: null },
  pageNumber: { type: Number, default: 1 },
});

const node = computed(() => props.node ?? {});
const context = computed(() => node.value?.context_report ?? {});
const total_score = computed(() => {
  const v = props.node?.total_score_report;
  return v !== undefined && v !== null ? Number(v).toFixed(2) : "-";
});
const weight = computed(() => node.value?.user_weight_report ?? "-");
const justification = computed(() => node.value?.user_justification_report ?? "");

const metricDescription = computed(() => 
  node.value?.metric_description_report || "Detailed analysis of the metric based on dataset parameters."
);

const rightGroup = computed(() =>
  node.value?.metric_right_report || node.value?.group_report || "Not available"
);

function prettifyLabel(str) {
  if (!str) return "";
  return String(str).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(v) {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "-";
  if (typeof v === "boolean") return v ? "True" : "False";
  return String(v);
}

const title = computed(() => {
  return context.value?.metric || prettifyLabel(props.metricKey) || "Metric Analysis";
});

const contextRows = computed(() => {
  return Object.entries(context.value || {})
    .filter(([key]) => key.toLowerCase().replace(/_/g, " ") !== "final score")
    .map(([key, value]) => ({
      label: prettifyLabel(key),
      value: typeof value === "string" ? prettifyLabel(value) : formatValue(value),
    }));
});

const totalScoreLabel = computed(() => {
  const v = Number(total_score.value);
  if (v <= 2) return "Critical Compliance";
  if (v <= 4) return "Low-Medium Compliance";
  if (v <= 6) return "Moderate Compliance";
  if (v <= 8) return "Good Compliance";
  return "Optimal Compliance";
});

const needleRotation = computed(() => {
  const v = Math.max(0, Math.min(10, Number(total_score.value)));
  return (v / 10) * 180 - 90;
});

const gaugeTicks = computed(() => {
  const ticks = [0, 2, 4, 6, 8, 10];
  const radius = 22; const centerX = 45; const centerY = 33;
  return ticks.map((value) => {
    const angleDeg = -180 + (value / 10) * 180;
    const angleRad = (angleDeg * Math.PI) / 180;
    const x = centerX + radius * Math.cos(angleRad);
    const y = centerY + radius * Math.sin(angleRad);
    return { value, style: { left: `${x}mm`, top: `${y}mm`, transform: "translate(-50%, -50%)" } };
  });
});
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
      <div class="title-section">
        <div class="domain-tag">{{ prettifyLabel(rightGroup) }} Domain</div>
        <h1 class="page-title">{{ title }}</h1>
        <div v-if="featureKey && featureKey !== '(global)'" class="feature-tag">
          Feature: <strong>{{ prettifyLabel(featureKey) }}</strong>
        </div>
      </div>

      <div class="main-grid">
        <div class="left-column">
          <section class="info-section">
            <h3 class="section-label">Metric Description</h3>
            <p class="description-text">{{ metricDescription }}</p>
          </section>

          <section class="info-section" v-if="contextRows.length">
            <h3 class="section-label">Evaluation Summary</h3>
            <div class="summary-list">
              <div v-for="row in contextRows" :key="row.label" class="summary-item">
                <span class="s-label">{{ row.label }}</span>
                <span class="s-value mono">{{ row.value }}</span>
              </div>
            </div>
          </section>

          <section class="info-section scores-row">
             <div class="score-pill">
               <span class="p-label">Weight</span>
               <span class="p-value">{{ weight }}</span>
             </div>
             <div class="score-pill blue">
               <span class="p-label">Metric Score</span>
               <span class="p-value">{{ total_score }}</span>
             </div>
          </section>
        </div>

        <div class="right-column">
          <section class="gauge-box">
            <h3 class="section-label central">Visual Assessment</h3>
            <div class="gauge-wrap">
              <div class="gauge-shell">
                <div class="gauge-arc">
                  <div class="segment seg-1"></div>
                  <div class="segment seg-2"></div>
                  <div class="segment seg-3"></div>
                  <div class="segment seg-4"></div>
                  <div class="segment seg-5"></div>
                </div>
                <div class="needle" :style="{ transform: `translateX(-50%) rotate(${needleRotation}deg)` }"></div>
                <div class="needle-center"></div>
                <div class="gauge-readout">
                  <div class="gauge-number">{{ total_score }}</div>
                  <div class="gauge-text">{{ totalScoreLabel }}</div>
                </div>
                <span v-for="tick in gaugeTicks" :key="tick.value" class="tick" :style="tick.style">{{ tick.value }}</span>
              </div>
            </div>
          </section>

          <section v-if="justification && justification !== 'No justification provided.'" class="justification-box">
            <h3 class="section-label">Contextual Justification</h3>
            <p class="justification-text">"{{ justification }}"</p>
          </section>
        </div>
      </div>
    </div>

    <div class="page-number">{{ pageNumber }}</div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

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
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 10mm;
  font-size: 10px; font-weight: 600; color: #64748b; letter-spacing: 0.5px;
}
.sep { margin: 0 8px; color: #cbd5e1; }
.brand { color: #1e293b; font-weight: 800; }

/* Title Section */
.title-section { margin-bottom: 10mm; }
.domain-tag { font-size: 10px; font-weight: 800; text-transform: uppercase; color: #3b82f6; letter-spacing: 1px; margin-bottom: 4px; }
.page-title { font-family: 'Instrument Serif', serif; font-size: 42px; line-height: 1.1; margin: 0; font-weight: 400; }
.feature-tag { margin-top: 8px; font-size: 13px; color: #475569; }

/* Grid Layout */
.main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12mm; align-items: start; }

.section-label { font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }
.section-label.central { text-align: center; }

/* Info Sections */
.info-section { margin-bottom: 8mm; }
.description-text { font-size: 13px; line-height: 1.6; color: #334155; font-style: italic; }

.summary-list { display: flex; flex-direction: column; gap: 8px; }
.summary-item { display: flex; justify-content: space-between; font-size: 12px; padding-bottom: 6px; border-bottom: 1px solid #f8fafc; }
.s-label { color: #64748b; font-weight: 500; }
.s-value { font-weight: 700; color: #1e293b; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Score Pills */
.scores-row { display: flex; gap: 10px; }
.score-pill { flex: 1; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; align-items: center; }
.score-pill.blue { background: #eff6ff; border-color: #dbeafe; }
.p-label { font-size: 9px; font-weight: 800; text-transform: uppercase; color: #64748b; }
.p-value { font-size: 20px; font-weight: 800; color: #1e293b; }
.score-pill.blue .p-value { color: #1d4ed8; }

/* Justification */
.justification-box { background: #fdfdfd; border-left: 3px solid #3b82f6; padding: 15px; margin-top: 5mm; }
.justification-text { font-size: 12px; line-height: 1.5; color: #475569; margin: 0; }

/* Gauge Styles */
.gauge-box { background: #fff; border: 1px solid #f1f5f9; border-radius: 12px; padding: 20px 10px; }
.gauge-wrap { display: flex; justify-content: center; transform: scale(0.9); }
.gauge-shell { position: relative; width: 90mm; height: 45mm; overflow: hidden; }
.gauge-arc { position: absolute; inset: 0; overflow: hidden; }
.gauge-arc::after { content: ""; position: absolute; left: 0; right: 0; bottom: -2mm; height: 12mm; background: #fff; z-index: 6; }
.segment { position: absolute; left: 50%; top: 70%; width: 60mm; height: 60mm; border-radius: 50%; border: 7mm solid transparent; transform-origin: center center; }
.seg-1 { transform: translate(-50%, -50%) rotate(-103deg); border-top-color: #ef4444; z-index: 5; }
.seg-2 { transform: translate(-50%, -50%) rotate(-65deg); border-top-color: #f97316; z-index: 4; }
.seg-3 { transform: translate(-50%, -50%) rotate(-22deg); border-top-color: #facc15; z-index: 3; }
.seg-4 { transform: translate(-50%, -50%) rotate(14deg); border-top-color: #38bdf8; z-index: 2; }
.seg-5 { transform: translate(-50%, -50%) rotate(54deg); border-top-color: #1d4ed8; z-index: 1; }
.needle { position: absolute; left: 50%; bottom: 12.5mm; width: 1.5mm; height: 26mm; background: #1e293b; border-radius: 99px; z-index: 10; transform-origin: bottom center; }
.needle-center { position: absolute; left: 50%; bottom: 10mm; width: 5mm; height: 5mm; background: #1e293b; border-radius: 50%; transform: translateX(-50%); z-index: 11; }
.gauge-readout { position: absolute; left: 50%; bottom: 0mm; transform: translateX(-50%); text-align: center; z-index: 12; width: 100%; }
.gauge-number { font-size: 16px; font-weight: 800; color: #1e293b; }
.gauge-text { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-top: 2px; }
.tick { position: absolute; font-size: 9px; font-weight: 800; color: #94a3b8; z-index: 7; }

.page-number { position: absolute; bottom: 10mm; right: 20mm; font-size: 10px; font-family: monospace; color: #94a3b8; }

@media print { .report-page-content { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style>