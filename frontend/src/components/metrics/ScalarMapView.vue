<script setup>
import { computed, reactive, ref, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  DEFAULT_WEIGHT,
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

const MIN_JUST_LENGTH = 10;
const weights = reactive({});         
const justifications = reactive({});  

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
      const init = Number(props.initialWeights?.[r.label]);
      weights[r.label] = Number.isFinite(init) ? init : DEFAULT_WEIGHT;
      if (justifications[r.label] === undefined) justifications[r.label] = "";
    }
    await nextTick();
    initialized.value = true;
  },
  { immediate: true }
);

function isChanged(label) { return Number(weights[label]) !== DEFAULT_WEIGHT; }
const anyChanged = computed(() => items.value.some((r) => isChanged(r.label)));

const missingJustifications = computed(() => {
  const missing = [];
  for (const r of items.value) {
    if (isChanged(r.label)) {
      const txt = String(justifications[r.label] || "").trim();
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

async function onWeightInput() {
  if (!initialized.value) return;
  await nextTick();
}

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

  for (const row of items.value) {
    const label = row.label;
    const w = Number(weights[label]);
    const finalWeight = Number.isFinite(w) ? w : DEFAULT_WEIGHT;

    weightsByLabel[label] = finalWeight;
    justificationsByLabel[label] = finalWeight === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(justifications[label] || "").trim();
  }

  return buildScalarMapSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    rows: items.value,
    weightsByLabel,
    justificationsByLabel,
  });
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
      <p class="metric-subtitle">Review the evaluation results across different parameters and assign contextual weights.</p>
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
            <div class="data-card-header">
              <h3 class="data-key">{{ prettifyLabel(row.label) }}</h3>
              <div class="score-badge" :class="valueBucket(row.value)">
                {{ Number(row.value).toFixed(3) }}
              </div>
            </div>
            
            <div class="inline-weight-control">
              <label>Weight (W = {{ weights[row.label] }})</label>
              <div class="slider-container">
                <input 
                  type="range" min="0" max="10" step="0.5" 
                  v-model.number="weights[row.label]" 
                  @input="onWeightInput" 
                  class="modern-slider"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="context-column">
        <h2 class="section-label">Contextual Impact</h2>
        
        <div class="weight-card">
          <p class="help-text">Standard weight is 5. If a different weight is provided for any parameter, it will need a textual justification below.</p>

          <div v-if="!anyChanged" class="just-placeholder">
            <div class="icon-circle">✓</div>
            <p>All weights are set to default (5). No justifications required.</p>
          </div>

          <div v-else class="justifications-list">
            <div 
              v-for="row in items" 
              :key="'j_' + row.label"
              v-show="isChanged(row.label)"
              class="justification-area is-active"
            >
              <div class="just-header">
                <label>{{ prettifyLabel(row.label) }}</label>
                <span v-if="String(justifications[row.label] || '').trim().length < MIN_JUST_LENGTH" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                <span v-else class="ok-badge">Valid ✓</span>
              </div>
              <textarea 
                v-model="justifications[row.label]" 
                class="modern-textarea" 
                rows="3" 
                placeholder="Explain why you changed this weight..."
              ></textarea>
            </div>

            <div v-if="missingJustifications.length" class="error-msg" style="margin-top: 1rem;">
              You have {{ missingJustifications.length }} missing justification(s).
            </div>
          </div>


          <div class="action-row" style="margin-top: 2rem;">
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
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; display: inline-block; margin-bottom: 1rem; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

/* Layout Split */
.content-split { display: grid; grid-template-columns: 1fr 420px; gap: 2rem; align-items: start; }
@media (max-width: 900px) { .content-split { grid-template-columns: 1fr; } }

.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; }

/* Legend */
.legend-box { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 1.5rem; }
.legend-title { font-size: 0.85rem; font-weight: 600; color: #555; text-transform: uppercase; }
.legend-scale { display: flex; flex: 1; height: 24px; border-radius: 6px; overflow: hidden; }
.legend-item { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.legend-item span { background: rgba(255,255,255,0.8); padding: 2px 6px; border-radius: 4px; color: #111; }

/* Bucket Colors */
.b81_100 { background: #2f76b7; color: #fff; }
.b61_80  { background: #8fc2e6; }
.b41_60  { background: #f6f2b8; }
.b21_40  { background: #ffbf85; }
.b0_20   { background: #ff9a9a; }

/* Left Column: Results Stack */
.data-stack { display: flex; flex-direction: column; gap: 1rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
.data-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.data-key { font-size: 1.1rem; font-weight: 600; color: #111; margin: 0; }
.score-badge { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; font-weight: 700; padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); }

.inline-weight-control label { display: block; font-size: 0.8rem; font-weight: 600; color: #666; margin-bottom: 8px; text-transform: uppercase; }
.slider-container { width: 100%; }
.modern-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; transition: 0.2s; }
.modern-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #111; cursor: pointer; border: 2px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: 0.2s; }
.modern-slider::-webkit-slider-thumb:hover { transform: scale(1.1); background: #1243e3; }

/* Right Column: Weight & Justification */
.weight-card { background: #fafafa; border: 1px solid #e5e5e5; border-radius: 16px; padding: 2rem; position: sticky; top: 20px; }
.help-text { font-size: 0.95rem; color: #666; line-height: 1.5; margin-bottom: 2rem; margin-top: 0; }

.just-placeholder { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 3rem 1rem; color: #888; }
.icon-circle { width: 48px; height: 48px; background: #e5e7eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 1rem; color: #555; }

.justifications-list { display: flex; flex-direction: column; gap: 1rem; }
.justification-area { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.2rem; transition: border-color 0.3s; }
.justification-area.is-active { border-color: #111; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.just-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; color: #111; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.9rem; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1243e3; box-shadow: 0 0 0 3px rgba(18,67,227,0.1); }

.error-msg { color: #e11d48; font-size: 0.9rem; font-weight: 600; text-align: center; background: #fff1f2; padding: 10px; border-radius: 8px; }

/* Actions */
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; padding: 0.5rem; }
.btn-ghost:hover { color: #111; }
.btn-primary { background: #111; color: #fff; border: 1px solid #111; padding: 0.8rem 1.5rem; border-radius: 4px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.btn-primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
</style>