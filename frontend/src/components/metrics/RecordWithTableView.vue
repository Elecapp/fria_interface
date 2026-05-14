<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  rowsToDict,
  isScalar,
  isPlainObject,
  buildRecordWithTableSavePayload,
} from "../../utils/report_builder_helper";

const router = useRouter();
const route = useRoute();

const group = computed(() => String(route.params.group || "")); 

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true },
  runId: { type: [String, Number], required: true }, 
});

const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function prettifyLabel(str) {
  if (!str) return "";
  return String(str).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isListOfDicts(v) { return Array.isArray(v) && v.length > 0 && v.every(isPlainObject); }
function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "—";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

const featureKeys = computed(() =>
  props.metricObj && typeof props.metricObj === "object"
    ? Object.keys(props.metricObj).filter((k) => k !== "__combined__" && k !== "(global)")
    : []
);

const selectedFeature = ref("");
watch(featureKeys, (keys) => {
    if (!selectedFeature.value && keys.length) selectedFeature.value = keys[0];
    if (selectedFeature.value && !keys.includes(selectedFeature.value)) selectedFeature.value = keys[0] || "";
  }, { immediate: true }
);

const featureObj = computed(() => {
  const o = props.metricObj;
  if (!isPlainObject(o)) return null;

  const hasNestedObject = Object.values(o).some(isPlainObject);
  if (!hasNestedObject) return o;

  if (isPlainObject(o["(global)"])) return o["(global)"];
  return selectedFeature.value ? o[selectedFeature.value] ?? null : null;
});

const summaryRows = computed(() => {
  const o = featureObj.value;
  if (!isPlainObject(o)) return [];
  const rows = [];
  for (const [k, v] of Object.entries(o)) {
    if (isListOfDicts(v)) continue; 
    const scalar = isScalar(v);
    const smallArray = Array.isArray(v) && v.length <= 50 && v.every((x) => ["string", "number", "boolean"].includes(typeof x));
    if (scalar || smallArray) rows.push({ key: k, value: v });
  }
  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
});

const tableBlocks = computed(() => {
  const o = featureObj.value;
  if (!isPlainObject(o)) return [];
  const blocks = [];
  for (const [k, v] of Object.entries(o)) {
    if (!isListOfDicts(v)) continue;
    const colSet = new Set();
    for (const row of v) Object.keys(row).forEach((ck) => colSet.add(ck));
    const columns = Array.from(colSet).sort((a, b) => a.localeCompare(b));
    const grid = `repeat(${columns.length}, minmax(140px, 1fr))`;
    blocks.push({ key: k, title: prettifyLabel(k), rows: v, columns, grid });
  }
  return blocks;
});

const MIN_JUST_LENGTH = 10;
const metricWeight = ref(DEFAULT_WEIGHT);
const metricJustification = ref("");

function isChangedMetric() { return Number(metricWeight.value) !== DEFAULT_WEIGHT; }
const missingJustifications = computed(() => {
  if (!isChangedMetric()) return [];
  const txt = String(metricJustification.value || "").trim();
  return txt.length < MIN_JUST_LENGTH ? ["(global)"] : [];
});

const canSave = computed(() => {
  if (!isChangedMetric()) return true;
  return missingJustifications.value.length === 0;
});

function buildSavePayload() {
  const contextReport = rowsToDict(summaryRows.value);
  return buildRecordWithTableSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    metricObj: contextReport,
    userWeight: isChangedMetric() ? Number(metricWeight.value) : DEFAULT_WEIGHT,
    userJustification: Number(metricWeight.value) === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(metricJustification.value || "").trim(),
  });
}

async function postSaveMetric() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildSavePayload()),
  });
  if (!resp.ok) throw new Error("Failed to save weight");
  return resp.json().catch(() => ({}));
}

async function onSave() {
  if (!canSave.value || saving.value) return;
  saving.value = true;
  saveError.value = "";
  saveOk.value = false;
  try {
    await postSaveMetric();
    saveOk.value = true;
    router.back();
  } catch (e) { saveError.value = e?.message || String(e); } finally { saving.value = false; }
}

// Per emulare il goBackSafely di ConditionalNested e non rompere la dashboard
const emit = defineEmits(["go-back-safe"]);
async function goBackSafely() {
  if (isChangedMetric() && canSave.value) {
    await onSave();
  } else if (!isChangedMetric()) {
    // Save defaults silently before exiting if untouched
    try { await postSaveMetric(); } catch(e){}
  }
  emit("go-back-safe");
}
defineExpose({ goBackSafely });
</script>

<template>
  <div class="result-layout">
    
    <div class="header-area">
      <div class="header-top">
        <div class="domain-tag">{{ prettifyLabel(group) }}</div>
        <button class="btn-ghost" @click="goBackSafely">← Back to Dashboard</button>
      </div>
      <h1 class="metric-title">{{ prettifyLabel(metricKey) }}</h1>
      <p class="metric-subtitle">Review the evaluation data and assign a contextual weight based on your scenario.</p>
    </div>

    <div class="content-split">
      
      <div class="results-column">
        <h2 class="section-label">Evaluation Data</h2>
        
        <div v-if="summaryRows.length" class="data-card">
          <h3>Summary</h3>
          <div class="metrics-grid">
            <div v-for="r in summaryRows" :key="r.key" class="data-item">
              <span class="data-key">{{ prettifyLabel(r.key) }}</span>
              <span class="data-value">{{ formatAny(r.value) }}</span>
            </div>
          </div>
        </div>

        <div v-for="tb in tableBlocks" :key="tb.key" class="table-card">
          <h3>{{ tb.title }}</h3>
          <div class="table-responsive">
            <table class="modern-table">
              <thead>
                <tr>
                  <th v-for="c in tb.columns" :key="c">{{ prettifyLabel(c) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in tb.rows" :key="idx">
                  <td v-for="c in tb.columns" :key="c" class="mono">{{ formatAny(r[c]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="!summaryRows.length && !tableBlocks.length" class="data-card empty-state">
          <h3>Raw output</h3>
          <pre class="raw-data">{{ JSON.stringify(featureObj || metricObj, null, 2) }}</pre>
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
              class="modern-slider"
            />
          </div>

          <div class="justification-area" :class="{ 'is-active': isChangedMetric() }">
            <div v-if="isChangedMetric()">
              <div class="just-header">
                <label>Justification</label>
                <span v-if="missingJustifications.length" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
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
            <button class="btn-primary" :disabled="!canSave || saving" @click="onSave" style="width: 100%;">
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
.header-area { margin-bottom: 3rem; }
.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; display: inline-block; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; }
.btn-ghost:hover { color: #111; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

.content-split { display: grid; grid-template-columns: 1fr 400px; gap: 2rem; align-items: start; }
@media (max-width: 900px) { .content-split { grid-template-columns: 1fr; } }
.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; }

.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
.data-card h3 { margin: 0 0 1.5rem 0; font-size: 1.2rem; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; }
.data-item { display: flex; flex-direction: column; gap: 0.5rem; padding-bottom: 1rem; border-bottom: 1px solid #f0f0f0; }
.data-key { font-size: 0.85rem; font-weight: 600; color: #666; text-transform: uppercase; }
.data-value { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: #111; line-height: 1; }

.table-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; overflow: hidden; margin-bottom: 1.5rem; }
.table-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; }
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
.modern-table th { background: #fafafa; padding: 1rem; font-weight: 600; color: #555; border-bottom: 2px solid #e5e5e5; white-space: nowrap; }
.modern-table td { padding: 1rem; border-bottom: 1px solid #f0f0f0; }
.modern-table tr:hover td { background: #fdfdfd; }
.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }

.empty-state { color: #666; }
.raw-data { background: #f8fafc; padding: 1rem; border-radius: 8px; font-size: 0.85rem; overflow-x: auto; border: 1px solid #e5e5e5; }

/* Right Column: Weight */
.weight-card { background: #fafafa; border: 1px solid #e5e5e5; border-radius: 16px; padding: 2rem; position: sticky; top: 20px;}
.weight-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.weight-header h3 { font-size: 1.1rem; font-weight: 700; margin: 0; }
.weight-display { font-family: 'JetBrains Mono', monospace; font-weight: 700; background: #111; color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 0.9rem; }
.help-text { font-size: 0.9rem; color: #666; line-height: 1.4; margin-bottom: 2rem; }

.slider-container { margin-bottom: 2.5rem; }
.slider-labels { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: #888; margin-bottom: 8px; padding: 0 5px; }
.modern-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; transition: 0.2s; }
.modern-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #1243e3; cursor: pointer; border: 2px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: 0.2s; }
.modern-slider::-webkit-slider-thumb:hover { transform: scale(1.1); }

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

.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.btn-primary { background: #111; color: #fff; border: 1px solid #111; padding: 1rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 1rem; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.btn-primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
</style>