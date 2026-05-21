<script setup>
import { computed, reactive, ref, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildScalarMapSavePayload,
} from "../../utils/report_builder_helper";

const router = useRouter();
const route = useRoute();

const group = computed(() => String(route.params.group || ""));

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true },
  initialWeights: { type: Object, default: () => ({}) },
  runId: { type: String, required: true },
});

function prettifyLabel(str) {
  return String(str || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// --- STATI EXECUTIVE ---
const MIN_JUST_LENGTH = 10;
const DEFAULT_GRAVITY = 0;

const gravityLabels = {
  0: "0 - None",
  1: "1 - Low",
  2: "2 - Medium",
  3: "3 - High",
  4: "4 - Very High"
};

const featureGravity = reactive({});         
const featureJustifications = reactive({});  
const featureReversibility = reactive({}); // Aggiunta Reversibilità

const initialized = ref(false);

const items = computed(() => {
  const obj = props.metricObj || {};
  return Object.entries(obj)
    .filter(([k, v]) => k !== "__combined__" && k !== "(global)" && typeof v === "number")
    .map(([label, value]) => ({ label, value }));
});

watch(
  items,
  async (rows) => {
    initialized.value = false;
    for (const r of rows) {
      // Leggiamo i pesi vecchi o impostiamo il default (0)
      const init = Number(props.initialWeights?.[r.label]);
      featureGravity[r.label] = Number.isFinite(init) ? init : DEFAULT_GRAVITY;
      if (featureJustifications[r.label] === undefined) featureJustifications[r.label] = "";
      if (featureReversibility[r.label] === undefined) featureReversibility[r.label] = false;
    }
    await nextTick();
    initialized.value = true;
  },
  { immediate: true }
);

function isChanged(label) { return Number(featureGravity[label]) > 0; }
const anyChanged = computed(() => items.value.some((r) => isChanged(r.label)));

const missingJustifications = computed(() => {
  const missing = [];
  for (const r of items.value) {
    if (isChanged(r.label)) {
      const txt = String(featureJustifications[r.label] || "").trim();
      if (txt.length < MIN_JUST_LENGTH) missing.push(r.label);
    }
  }
  return missing;
});

const canSave = computed(() => {
  if (!initialized.value) return false;
  if (!anyChanged.value) return true; 
  return missingJustifications.value.length === 0; 
});

function valueBucket(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "b41_60";
  if (n <= 0.2) return "b0_20";
  if (n <= 0.4) return "b21_40";
  if (n <= 0.6) return "b41_60";
  if (n <= 0.8) return "b61_80";
  return "b81_100";
}

const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function buildSavePayload() {
  const weightsByLabel = {};
  const justificationsByLabel = {};
  const reversibilityByLabel = {}; // Prepariamo l'invio al backend

  for (const row of items.value) {
    const label = row.label;
    const g = Number(featureGravity[label]);
    const finalGravity = Number.isFinite(g) ? g : DEFAULT_GRAVITY;

    weightsByLabel[label] = finalGravity;
    justificationsByLabel[label] = finalGravity === DEFAULT_GRAVITY ? DEFAULT_WEIGHT_JUSTIFICATION : String(featureJustifications[label] || "").trim();
    reversibilityByLabel[label] = featureReversibility[label];
  }

  const payload = buildScalarMapSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    rows: items.value,
    weightsByLabel,
    justificationsByLabel,
  });

  // Aggiungiamo i dati per il nuovo backend Python
  payload.reversibilityByLabel = reversibilityByLabel;

  return payload;
}

async function postSaveMetric() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save weights");
  }
  return resp.json().catch(() => ({}));
}

async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    await postSaveMetric()
    saveOk.value = true;
    router.back();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="result-layout">
    
    <div class="header-area">
      <div class="domain-tag">{{ prettifyLabel(group) }}</div>
      <h1 class="metric-title">{{ prettifyLabel(metricKey) }}</h1>
      <p class="metric-subtitle">Review the evaluation results across different parameters and assign contextual impact.</p>
    </div>

    <div class="content-split">
      
      <div class="results-column">
        
        <div class="legend-box">
          <span class="legend-title">Score Interpretation</span>
          <div class="legend-scale">
            <div class="legend-item b0_20"><span>0 - 0.2</span></div>
            <div class="legend-item b21_40"><span>0.2 - 0.4</span></div>
            <div class="legend-item b41_60"><span>0.4 - 0.6</span></div>
            <div class="legend-item b61_80"><span>0.6 - 0.8</span></div>
            <div class="legend-item b81_100"><span>0.8 - 1.0</span></div>
          </div>
        </div>

        <h2 class="section-label">Evaluation Data</h2>
        
        <div class="data-stack">
          <div v-for="row in items" :key="row.label" class="data-card">
            <div class="data-card-header" style="margin-bottom: 0;">
              <h3 class="data-key">{{ prettifyLabel(row.label) }}</h3>
              <div class="score-badge" :class="valueBucket(row.value)">
                {{ Number(row.value).toFixed(3) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="context-column">
        <h2 class="section-label">Contextual Impact</h2>
        
        <div class="weight-card executive-panel">
          <p class="help-text">Standard gravity is None (0). If a higher gravity is selected, a textual justification will be required.</p>

          <div v-if="!anyChanged" class="just-placeholder">
            <div class="icon-circle">✓</div>
            <p>All gravities are set to None. No justifications required.</p>
          </div>

          <div v-else class="justifications-list">
            <div 
              v-for="row in items" 
              :key="'j_' + row.label"
              v-show="isChanged(row.label)"
              class="justification-area is-active"
            >
              <div class="just-header" style="border-bottom: 1px solid #e5e5e5; padding-bottom: 10px; margin-bottom: 15px;">
                <label style="font-size: 1.1rem; color: #1A365D;">{{ prettifyLabel(row.label) }}</label>
              </div>
              
              <label class="reversibility-toggle">
                <input 
                  type="checkbox" 
                  v-model="featureReversibility[row.label]" 
                />
                <span class="checkbox-box"></span>
                <span class="checkbox-text">Reversibility (Yes)</span>
              </label>

              <div class="just-header">
                <label>Justification</label>
                <span v-if="String(featureJustifications[row.label] || '').trim().length < MIN_JUST_LENGTH" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                <span v-else class="ok-badge">Valid ✓</span>
              </div>
              <textarea 
                v-model="featureJustifications[row.label]" 
                class="modern-textarea" 
                rows="3" 
                placeholder="Explain the impact..."
              ></textarea>
            </div>

            <div v-if="missingJustifications.length" class="error-msg" style="margin-top: 1rem;">
              You have {{ missingJustifications.length }} missing justification(s).
            </div>
          </div>

        </div>

        <div class="action-card" style="margin-top: 20px; background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e5e5e5;">
          <div v-for="row in items" :key="'g_' + row.label" style="margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px;">
            <div class="slider-labels-top">
              <span>Gravity for: {{ prettifyLabel(row.label) }}</span>
              <span class="weight-display">{{ gravityLabels[featureGravity[row.label]] }}</span>
            </div>
            
            <input 
              type="range" min="0" max="4" step="1" 
              v-model.number="featureGravity[row.label]" 
              class="premium-slider"
            />
            
            <div class="ticks-labels">
              <div class="tick-item"><span>None</span></div>
              <div class="tick-item"><span>Low</span></div>
              <div class="tick-item"><span>Med</span></div>
              <div class="tick-item"><span>High</span></div>
              <div class="tick-item"><span>V. High</span></div>
            </div>
          </div>

          <div class="action-row">
            <button class="btn-ghost" @click="router.back()">Cancel</button>
            <button class="btn-primary" :disabled="!canSave || saving" @click="onSave">
              {{ saving ? "Saving..." : "Save & Return" }}
            </button>
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<style scoped>
.result-layout { max-width: 1200px; margin: 0 auto; padding: 2rem; font-family: 'Inter', sans-serif; color: #111; }

/* Header */
.header-area { margin-bottom: 2rem; }
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1A365D; background: #e2e8f0; padding: 4px 10px; border-radius: 4px; display: inline-block; margin-bottom: 1rem; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

/* Layout Split */
.content-split { display: grid; grid-template-columns: 1fr 450px; gap: 2rem; align-items: start; }
@media (max-width: 900px) { .content-split { grid-template-columns: 1fr; } }

.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; }

/* Legend */
.legend-box { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 1.5rem; }
.legend-title { font-size: 0.85rem; font-weight: 600; color: #555; text-transform: uppercase; }
.legend-scale { display: flex; flex: 1; height: 24px; border-radius: 6px; overflow: hidden; }
.legend-item { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.legend-item span { background: rgba(255,255,255,0.8); padding: 2px 6px; border-radius: 4px; color: #111; }

/* Bucket Colors */
.b81_100 { background: #1A365D; color: #fff; }
.b61_80  { background: #2f76b7; color: #fff;}
.b41_60  { background: #8fc2e6; }
.b21_40  { background: #ffbf85; }
.b0_20   { background: #e11d48; color: #fff;}

/* Left Column: Results Stack */
.data-stack { display: flex; flex-direction: column; gap: 1rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
.data-card-header { display: flex; justify-content: space-between; align-items: center; }
.data-key { font-size: 1.1rem; font-weight: 600; color: #111; margin: 0; }
.score-badge { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; font-weight: 700; padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); }

/* Right Column: Weight & Justification */
.executive-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
.help-text { font-size: 0.95rem; color: #666; line-height: 1.5; margin-bottom: 2rem; margin-top: 0; }

.just-placeholder { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 3rem 1rem; color: #888; }
.icon-circle { width: 48px; height: 48px; background: #e5e7eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 1rem; color: #555; }

.justifications-list { display: flex; flex-direction: column; gap: 1rem; }
.justification-area { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.2rem; transition: border-color 0.3s; }
.justification-area.is-active { border-color: #cbd5e1; border-left: 4px solid #1A365D; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.just-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; color: #111; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.9rem; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1A365D; box-shadow: 0 0 0 3px rgba(26,54,93,0.1); }

/* Nuovi Slider Premium */
.slider-labels-top { display: flex; justify-content: space-between; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; }
.weight-display { color: #1A365D; }
.premium-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; margin-bottom: 10px; }
.premium-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 22px; height: 22px; border-radius: 50%; background: #1A365D; cursor: pointer; border: 4px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
.ticks-labels { display: flex; justify-content: space-between; padding: 0 5px; }
.tick-item { flex: 1; text-align: center; }
.tick-item:first-child { text-align: left; }
.tick-item:last-child { text-align: right; }
.tick-item span { font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; }

/* Reversibility Toggle */
.reversibility-toggle { display: flex; align-items: center; gap: 12px; cursor: pointer; margin-bottom: 25px; }
.reversibility-toggle input { display: none; }
.checkbox-box { width: 24px; height: 24px; border: 2px solid #cbd5e1; display: inline-block; position: relative; transition: 0.2s; border-radius: 4px; }
.reversibility-toggle input:checked ~ .checkbox-box { background-color: #1A365D; border-color: #1A365D; }
.reversibility-toggle input:checked ~ .checkbox-box:after { content: ""; position: absolute; left: 7px; top: 3px; width: 5px; height: 11px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.checkbox-text { font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #1e293b; }

.error-msg { color: #e11d48; font-size: 0.9rem; font-weight: 600; text-align: center; background: #fff1f2; padding: 10px; border-radius: 8px; }

/* Actions */
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; padding: 0.5rem; }
.btn-ghost:hover { color: #111; }
.btn-primary { background: #1A365D; color: #fff; border: 1px solid #1A365D; padding: 0.8rem 1.5rem; border-radius: 4px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; }
.btn-primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
</style>