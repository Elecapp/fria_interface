<script setup>
import { API_HOST } from "../../utils/config";
import { computed } from "vue";

const props = defineProps({
  node: { type: Object, required: true },
  meta: { type: Object, default: () => ({}) },
  metricKey: { type: String, default: "" },
  featureKey: { type: String, default: null },
  pageNumber: { type: Number, default: 1 },
});

// IL TRUCCO: Estrarre il nodo corretto a seconda se è globale o no
const dataNode = computed(() => {
  const root = props.node ?? {};
  if (root["(global)"] && typeof root["(global)"] === "object") {
    return root["(global)"];
  }
  return root;
});

const context = computed(() => dataNode.value?.context_report ?? {});

// 1. Likelihood (Il valore originale calcolato dall'algoritmo 0-10)
const likelihoodScore = computed(() => {
  // Prova a estrarlo da dove capita (il backend lo salva in posti diversi)
  const v = context.value?.final_score ?? dataNode.value?.value ?? dataNode.value?.final_score;
  // Se era in base 1 (0.0-1.0), moltiplichiamo per 10 per coerenza visiva
  if (v !== undefined && v !== null) {
      const num = Number(v);
      return num <= 1 ? (num * 10).toFixed(2) : num.toFixed(2);
  }
  return "N/A";
});

// 2. Gravity (0-4) e Reversibility
const gravity = computed(() => dataNode.value?.gravity_report ?? "0");
const reversibility = computed(() => dataNode.value?.reversibility_report ? "YES" : "NO");

// 3. Final Risk Score (Il totale calcolato FRIA)
const total_score = computed(() => {
  const v = dataNode.value?.total_score_report;
  return v !== undefined && v !== null ? Number(v).toFixed(2) : "-";
});

const justification = computed(() => dataNode.value?.user_justification_report ?? "");

const metricDescription = computed(() => 
  dataNode.value?.metric_description_report || "Detailed analysis of the metric based on dataset parameters."
);

const rightGroup = computed(() =>
  dataNode.value?.metric_right_report || dataNode.value?.group_report || "Not available"
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

// ETICHETTE DEL GAUGE (Invariato)
const totalScoreLabel = computed(() => {
  const v = Number(total_score.value);
  if (isNaN(v)) return "Unknown";
  if (v <= 7.45) return "Optimal";
  if (v <= 15) return "Good";
  if (v <= 24.5) return "Moderate";
  if (v <= 42) return "Problematic";
  return "Critical";
});

// Funzione helper per mappare i valori in modo proporzionale sui 5 spicchi
function getSegmentPosition(value) {
  if (value <= 0) return 0;
  // Spicchio 1 (0 - 7.5)
  if (value <= 7.5) return 0 + (value - 0) / (7.5 - 0);
  // Spicchio 2 (7.5 - 15)
  if (value <= 15) return 1 + (value - 7.5) / (15 - 7.5);
  // Spicchio 3 (15 - 24.5)
  if (value <= 24.5) return 2 + (value - 15) / (24.5 - 15);
  // Spicchio 4 (24.5 - 42)
  if (value <= 42) return 3 + (value - 24.5) / (42 - 24.5);
  // Spicchio 5 (42 - 75)
  if (value <= 75) return 4 + (value - 42) / (75 - 42);
  return 5; // Oltre 75
}

// LANCETTA DEL GAUGE (Usa i 5 spicchi visivi)
const needleRotation = computed(() => {
  const v = Math.max(0, Math.min(75, Number(total_score.value) || 0));
  // Ottiene la posizione da 0 a 5, la divide per 5 (i totali spicchi) e calcola l'angolo
  const segmentPos = getSegmentPosition(v);
  return (segmentPos / 5) * 180 - 90;
});

// NUMERINI SUL GAUGE (Posizionati esattamente ai confini degli spicchi visivi)
const gaugeTicks = computed(() => {
  const ticks = [0, 7.5, 15, 24.5, 42, 75];
  const radius = 22; const centerX = 45; const centerY = 33;
  
  return ticks.map((value, index) => {
    // index va da 0 a 5. Diviso 5 ci dà le percentuali esatte: 0%, 20%, 40%, 60%, 80%, 100%
    const angleDeg = -180 + (index / 5) * 180; 
    const angleRad = (angleDeg * Math.PI) / 180;
    const x = centerX + radius * Math.cos(angleRad);
    const y = centerY + radius * Math.sin(angleRad);
    return { 
      value, 
      style: { left: `${x}mm`, top: `${y}mm`, transform: "translate(-50%, -50%)" } 
    };
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
          Context: <strong>{{ prettifyLabel(featureKey) }}</strong>
        </div>
      </div>

      <div class="main-grid">
        <div class="left-column">
          <section class="info-section">
            <h3 class="section-label">Metric Description</h3>
            <p class="description-text">{{ metricDescription }}</p>
          </section>

          <section class="info-section" v-if="contextRows.length">
            <h3 class="section-label">Summary Report</h3>
            <div class="summary-list">
              <div v-for="row in contextRows" :key="row.label" class="summary-item">
                <span class="s-label">{{ row.label }}</span>
                <span class="s-value mono">{{ row.value }}</span>
              </div>
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

          <section class="info-section scores-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 5mm;">
             
             <div class="score-pill">
               <span class="p-label">Likelihood (0-10)</span>
               <span class="p-value">{{ likelihoodScore }}</span>
             </div>

             <div class="score-pill">
               <span class="p-label">Gravity Impact (1-5)</span>
               <span class="p-value">{{ gravity }}</span>
             </div>
             
             <div class="score-pill" :class="{ 'red-pill': reversibility === 'NO', 'green-pill': reversibility === 'YES' }">
               <span class="p-label">Reversibility</span>
               <span class="p-value">{{ reversibility }}</span>
             </div>

             <div class="score-pill blue">
               <span class="p-label">FINAL RISK SCORE</span>
               <span class="p-value">{{ total_score }}</span>
             </div>
          </section>

          <section v-if="justification && justification !== 'No justification provided.'" class="justification-box">
            <h3 class="section-label">Justification</h3>
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
.page-title { font-family: 'Instrument Serif', serif; font-size: 42px; line-height: 1.1; margin: 0; font-weight: 400; color: #1e293b; }
.feature-tag { margin-top: 8px; font-size: 14px; color: #475569; }

/* Grid Layout */
.main-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 12mm; align-items: start; }

.section-label { font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }
.section-label.central { text-align: center; }

/* Info Sections */
.info-section { margin-bottom: 8mm; }

/* Testo descrizione rimpicciolito e tagliato se troppo lungo */
.description-text { 
  font-size: 10px; 
  line-height: 1.4; 
  color: #334155; 
  font-style: italic; 
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* --- MODIFICHE ALLA LISTA/TABELLA --- */
/* Ridotto il gap da 8px a 4px per stringere le righe */
.summary-list { display: flex; flex-direction: column; gap: 4px; }
/* Ridotto padding e font-size per recuperare spazio verticale */
.summary-item { display: flex; justify-content: space-between; font-size: 10px; padding-bottom: 4px; border-bottom: 1px solid #f8fafc; }
.s-label { color: #64748b; font-weight: 500; }
.s-value { font-weight: 700; color: #1e293b; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Score Pills */
.scores-container { display: flex; gap: 10px; margin-top: 5mm; margin-bottom: 8mm; }
.score-pill { flex: 1; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; align-items: center; }
.score-pill.blue { background: #eff6ff; border-color: #dbeafe; }
.p-label { font-size: 9px; font-weight: 800; text-transform: uppercase; color: #64748b; }
.p-value { font-size: 20px; font-weight: 800; color: #1e293b; }
.score-pill.blue .p-value { color: #1d4ed8; }

/* Justification */
.justification-box { 
  background: #fdfdfd; 
  border-left: 3px solid #3b82f6; 
  padding: 15px; 
  margin-top: 5mm; 
}
/* Testo giustificazione rimpicciolito e tagliato se troppo lungo */
.justification-text { 
  font-size: 10px; 
  line-height: 1.4; 
  color: #475569; 
  margin: 0; 
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Gauge Styles */
.gauge-box { background: #fff; border: 1px solid #f1f5f9; border-radius: 12px; padding: 20px 10px; margin-bottom: 5mm; }
.gauge-wrap { display: flex; justify-content: center; transform: scale(0.85); }
.gauge-shell { position: relative; width: 90mm; height: 45mm; overflow: hidden; }
.gauge-arc { position: absolute; inset: 0; overflow: hidden; }
.gauge-arc::after { content: ""; position: absolute; left: 0; right: 0; bottom: -2mm; height: 12mm; background: #fff; z-index: 6; }
.segment { position: absolute; left: 50%; top: 70%; width: 60mm; height: 60mm; border-radius: 50%; border: 7mm solid transparent; transform-origin: center center; }

.seg-1 { transform: translate(-50%, -50%) rotate(-103deg); border-top-color: #1d4ed8; z-index: 5; } /* Blu - 0.0-2.0 (Optimal) */
.seg-2 { transform: translate(-50%, -50%) rotate(-65deg); border-top-color: #38bdf8; z-index: 4; }  /* Lightblue - 2.0-4.0 (Good) */
.seg-3 { transform: translate(-50%, -50%) rotate(-22deg); border-top-color: #facc15; z-index: 3; }  /* Yellow - 4.0-6.0 (Moderate) */
.seg-4 { transform: translate(-50%, -50%) rotate(14deg); border-top-color: #f97316; z-index: 2; }   /* Orange - 6.0-8.0 (Problematic) */
.seg-5 { transform: translate(-50%, -50%) rotate(54deg); border-top-color: #ef4444; z-index: 1; }   /* Red - 8.0-10.0 (Critical) */
.needle { position: absolute; left: 50%; bottom: 12.5mm; width: 1.5mm; height: 26mm; background: #1e293b; border-radius: 99px; z-index: 10; transform-origin: bottom center; }
.needle-center { position: absolute; left: 50%; bottom: 10mm; width: 5mm; height: 5mm; background: #1e293b; border-radius: 50%; transform: translateX(-50%); z-index: 11; }
.gauge-readout { position: absolute; left: 50%; bottom: 0mm; transform: translateX(-50%); text-align: center; z-index: 12; width: 100%; }
.gauge-number { font-size: 16px; font-weight: 800; color: #1e293b; }
.gauge-text { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-top: 2px; }
.tick { position: absolute; font-size: 9px; font-weight: 800; color: #94a3b8; z-index: 7; }

.page-number { position: absolute; bottom: 10mm; right: 20mm; font-size: 10px; font-family: monospace; color: #94a3b8; }
/* Aggiungi queste definizioni per attivare i colori */
.red-pill { 
  background-color: #fee2e2 !important; 
  border-color: #fecaca !important; 
}
.red-pill .p-value { 
  color: #b91c1c !important; /* Testo rosso scuro */
}

.green-pill { 
  background-color: #dcfce7 !important; 
  border-color: #bbf7d0 !important; 
}
.green-pill .p-value { 
  color: #15803d !important; /* Testo verde scuro */
}
@media print { .report-page-content { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style>