<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  isPlainObject,
  isScalar,
  buildCardMapSavePayload,
} from "../../utils/report_builder_helper";

const router = useRouter();
const route = useRoute();

const group = computed(() => String(route.params.group || ""));

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true }, 
  runId: { type: [String, Number], required: true },
});

/** ---------- helpers ---------- */
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isListOfDicts(v) {
  return Array.isArray(v) && v.length > 0 && v.every(isPlainObject);
}

function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "—";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

/** ---------- pick the record to show (card_map) ---------- */
const cardRecord = computed(() => {
  const o = props.metricObj;
  if (!isPlainObject(o)) return null;

  if (isPlainObject(o["(global)"])) return o["(global)"];

  const keys = Object.keys(o).filter((k) => k !== "__combined__");
  if (keys.length === 1 && isPlainObject(o[keys[0]])) return o[keys[0]];

  const hasNestedDict = Object.values(o).some(isPlainObject);
  return hasNestedDict ? null : o;
});

/** ---------- Summary rows ---------- */
const summaryRows = computed(() => {
  const rec = cardRecord.value;
  if (!isPlainObject(rec)) return [];

  const rows = [];
  for (const [k, v] of Object.entries(rec)) {
    if (isPlainObject(v) || isListOfDicts(v)) continue;

    const smallArray = Array.isArray(v) && v.length <= 80 && v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (isScalar(v) || smallArray) rows.push({ key: k, value: v });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
});

// Metric level weight
const MIN_JUST_LENGTH = 10;
const metricWeight = ref(DEFAULT_WEIGHT);
const metricJustification = ref("");
const contextualOpen = ref(true);

function isChangedMetric() {
  return Number(metricWeight.value) !== DEFAULT_WEIGHT;
}

const missingJustifications = computed(() => {
  if (!isChangedMetric()) return [];
  const txt = String(metricJustification.value || "").trim();
  return txt.length < MIN_JUST_LENGTH ? ["(global)"] : [];
});

const canSave = computed(() => {
  if (!isChangedMetric()) return true;
  return missingJustifications.value.length === 0;
});

function onWeightInput() {
  contextualOpen.value = true;
}

// Save state
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function buildSavePayload() {
  const contextReport = Object.fromEntries(
    summaryRows.value.map((row) => [prettifyLabel(row.key), row.value])
  );

  return buildCardMapSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    metricObj: { "(global)": { context_report: contextReport } },
    userWeight: Number(metricWeight.value),
    userJustification: Number(metricWeight.value) === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(metricJustification.value || "").trim(),
  });
}

async function postSaveWeights() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
  }
  return resp.json().catch(() => ({}));
}

async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    await postSaveWeights();
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
      <p class="metric-subtitle">Review the evaluation results and assign a contextual weight based on your scenario.</p>
    </div>

    <div class="content-split">
      
      <div class="results-column">
        <h2 class="section-label">Evaluation Data</h2>
        
        <div class="data-card">
          <div v-if="summaryRows.length" class="metrics-grid">
            <div v-for="r in summaryRows" :key="r.key" class="data-item">
              <span class="data-key">{{ prettifyLabel(r.key) }}</span>
              <span class="data-value">{{ formatAny(r.value) }}</span>
            </div>
          </div>
          
          <div v-else class="empty-state">
            <p>No formatted summary available.</p>
            <pre class="raw-data">{{ JSON.stringify(cardRecord || metricObj, null, 2) }}</pre>
          </div>
        </div>
      </div>

      <div class="context-column">
        <h2 class="section-label">Contextual Impact</h2>
        
        <div class="weight-card">
          <div class="weight-header">
            <h3>Metric Weight</h3>
            <span class="weight-display">W = {{ metricWeight }}</span>
          </div>
          
          <p class="help-text">Adjust the impact score (0–10). A higher value means this metric is critical for your specific use case. Default is 5.</p>

          <div class="slider-container">
            <div class="slider-labels">
              <span>0</span><span>5</span><span>10</span>
            </div>
            <input 
              type="range" min="0" max="10" step="0.5" 
              v-model.number="metricWeight" 
              @input="onWeightInput" 
              class="modern-slider"
            />
          </div>

          <div class="justification-area" :class="{ 'is-active': isChangedMetric() }">
            <div v-if="isChangedMetric()">
              <div class="just-header">
                <label>Justification</label>
                <span v-if="missingJustifications.length" class="req-badge">Required (min {{ MIN_JUST_LENGTH }} chars)</span>
                <span v-else class="ok-badge">Valid ✓</span>
              </div>
              <textarea 
                v-model="metricJustification" 
                class="modern-textarea" 
                rows="4" 
                placeholder="Explain why this metric requires a custom weight in your context..."
              ></textarea>
            </div>
            <div v-else class="just-placeholder">
              <p>Keep the default weight (5) to bypass justification.</p>
            </div>
          </div>

          <div v-if="saveError" class="error-msg">{{ saveError }}</div>

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
.result-layout {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Inter', sans-serif;
  color: #111;
}

/* Header */
.header-area { margin-bottom: 3rem; }
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; display: inline-block; margin-bottom: 1rem; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

/* Layout Split */
.content-split { display: grid; grid-template-columns: 1fr 400px; gap: 2rem; align-items: start; }
@media (max-width: 900px) { .content-split { grid-template-columns: 1fr; } }

.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; }

/* Left Column: Results */
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; }
.data-item { display: flex; flex-direction: column; gap: 0.5rem; padding-bottom: 1rem; border-bottom: 1px solid #f0f0f0; }
.data-key { font-size: 0.85rem; font-weight: 600; color: #666; text-transform: uppercase; }
.data-value { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: #111; line-height: 1; }

.empty-state { color: #666; }
.raw-data { background: #f8fafc; padding: 1rem; border-radius: 8px; font-size: 0.85rem; overflow-x: auto; margin-top: 1rem; border: 1px solid #e5e5e5; }

/* Right Column: Weight */
.weight-card { background: #fafafa; border: 1px solid #e5e5e5; border-radius: 16px; padding: 2rem; }
.weight-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.weight-header h3 { font-size: 1.1rem; font-weight: 700; margin: 0; }
.weight-display { font-family: 'JetBrains Mono', monospace; font-weight: 700; background: #111; color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 0.9rem; }
.help-text { font-size: 0.9rem; color: #666; line-height: 1.4; margin-bottom: 2rem; }

/* Slider */
.slider-container { margin-bottom: 2.5rem; }
.slider-labels { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: #888; margin-bottom: 8px; padding: 0 5px; }
.modern-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; transition: 0.2s; }
.modern-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #1243e3; cursor: pointer; border: 2px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: 0.2s; }
.modern-slider::-webkit-slider-thumb:hover { transform: scale(1.1); }

/* Justification */
.justification-area { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; transition: border-color 0.3s; }
.justification-area.is-active { border-color: #1243e3; }
.just-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 600; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.9rem; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1243e3; box-shadow: 0 0 0 3px rgba(18,67,227,0.1); }
.just-placeholder p { margin: 0; font-size: 0.9rem; color: #888; text-align: center; font-style: italic; }

.error-msg { color: #e11d48; font-size: 0.9rem; margin-bottom: 1rem; text-align: center; font-weight: 500; }

/* Actions */
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; padding: 0.5rem; }
.btn-ghost:hover { color: #111; }
.btn-primary { background: #111; color: #fff; border: 1px solid #111; padding: 0.8rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.btn-primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
</style>