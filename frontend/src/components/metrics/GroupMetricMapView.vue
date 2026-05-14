<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildConditionalNestedFeatureSavePayload,
  buildContextSummaryRows as sharedBuildContextSummaryRows,
  buildSummaryRows as sharedBuildSummaryRows,
  getFeatureObject as sharedGetFeatureObject,
  getSummaryKeyForFeature as sharedGetSummaryKeyForFeature,
  isPlainObject,
} from "../../utils/report_builder_helper";

const route = useRoute();
const group = computed(() => String(route.params.group || ""));
const metricKey = computed(() => String(route.params.metric || ""));

const loading = ref(false);
const error = ref("");
const metricObj = ref(null);
const items = ref([]); 

const props = defineProps({ runId: { type: String, required: true } });
const emit = defineEmits(["go-back-safe"]);

const activeFeatureTab = ref("");
const MIN_JUST_LENGTH = 10;
const featureWeights = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function ensureFeatureState(feature) {
  if (!(feature in featureWeights.value)) featureWeights.value[feature] = DEFAULT_WEIGHT;
  if (!(feature in featureJustifications.value)) featureJustifications.value[feature] = "";
  if (!(feature in savedFeatures.value)) savedFeatures.value[feature] = false;
}

function isFeatureSaved(feature) { ensureFeatureState(feature); return !!savedFeatures.value[feature]; }
function getFeatureWeight(feature) { ensureFeatureState(feature); return Number.isFinite(Number(featureWeights.value[feature])) ? Number(featureWeights.value[feature]) : DEFAULT_WEIGHT; }
function setFeatureWeight(feature, val) { ensureFeatureState(feature); featureWeights.value[feature] = Number(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function getFeatureJustification(feature) { ensureFeatureState(feature); return String(featureJustifications.value[feature] || ""); }
function setFeatureJustification(feature, val) { ensureFeatureState(feature); featureJustifications.value[feature] = String(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function featureNeedsJustification(feature) { ensureFeatureState(feature); return Number(getFeatureWeight(feature)) !== DEFAULT_WEIGHT; }
function isFeatureValid(feature) { ensureFeatureState(feature); if (!featureNeedsJustification(feature)) return true; return String(getFeatureJustification(feature)).trim().length >= MIN_JUST_LENGTH; }

async function saveFeature(feature) {
  ensureFeatureState(feature);
  if (saving.value) return;
  const weight = Number(getFeatureWeight(feature));
  const justification = Number(weight) === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(getFeatureJustification(feature) || "");
  if (!isFeatureValid(feature)) { saveError.value = `Justification required.`; return; }

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    const payload = buildConditionalNestedFeatureSavePayload({
      runId: props.runId, group: group.value, metric: metricKey.value, schemaType: schemaTypeReport.value, 
      feature, metricObj: metricObj.value, weight, justification, formatLabel: prettifyLabel, formatValue: formatAny,
    });
    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!resp.ok) throw new Error("Failed to save feature");
    savedFeatures.value[feature] = true; saveOk.value = true;
  } catch (e) { saveError.value = e?.message || String(e); } finally { saving.value = false; }
}

async function saveMissingFeaturesWithDefaultWeight() {
  if (saving.value) return;
  saving.value = true;
  try {
    for (const feature of featureKeys.value) {
      ensureFeatureState(feature);
      if (isFeatureSaved(feature)) continue;
      const payload = buildConditionalNestedFeatureSavePayload({
        runId: props.runId, group: group.value, metric: metricKey.value, schemaType: schemaTypeReport.value, 
        feature, metricObj: metricObj.value, weight: DEFAULT_WEIGHT, justification: DEFAULT_WEIGHT_JUSTIFICATION, formatLabel: prettifyLabel, formatValue: formatAny,
      });
      await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      featureWeights.value[feature] = DEFAULT_WEIGHT; featureJustifications.value[feature] = DEFAULT_WEIGHT_JUSTIFICATION; savedFeatures.value[feature] = true;
    }
  } catch (e) { console.error(e); } finally { saving.value = false; }
}

async function goBackSafely() {
  await saveMissingFeaturesWithDefaultWeight();
  emit("go-back-safe");
}
defineExpose({ goBackSafely });

const featureKeys = computed(() => {
  const obj = metricObj.value;
  if (!obj || typeof obj !== "object") return [];
  return Object.keys(obj).filter(k => k !== "__combined__" && k !== "(global)");
});

const resultSchemas = ref({});
const schemaTypeReport = computed(() => resultSchemas.value?.[metricKey.value]?.schema ?? null);

async function loadResultSchemas() {
  try {
    const resp = await fetch(`http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(props.runId)}`);
    if (resp.ok) resultSchemas.value = await resp.json();
  } catch (e) {}
}
onMounted(loadResultSchemas);

function prettifyLabel(str) { return (!str || typeof str !== "string") ? "" : str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  return typeof v === "number" ? (Number.isFinite(v) ? v.toFixed(3) : "—") : String(v);
}
function formatHeaderKey(k) { const num = Number(k); return !Number.isNaN(num) && k !== "" ? num.toFixed(3) : prettifyLabel(k); }
function isScalar(v) { return v === null || v === undefined || ["string", "number", "boolean"].includes(typeof v); }
function looksLikeGroupMap(v) { if (!isPlainObject(v)) return false; const entries = Object.entries(v); return entries.length > 0 && entries.every(([k, val]) => typeof k === "string" && isScalar(val)); }

function getFeatureObject(featureKey) { return sharedGetFeatureObject(metricObj.value, featureKey); }
function getConditionsKeyForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return null;
  let bestKey = null, bestRows = -1;
  for (const [k, v] of Object.entries(featureObjLocal)) {
    if (!isPlainObject(v)) continue;
    const rows = Object.values(v);
    if (rows.length > 0 && rows.every(isPlainObject) && rows.length > bestRows) { bestRows = rows.length; bestKey = k; }
  }
  return bestKey;
}
function getContextSummaryRows(feature) { return sharedBuildContextSummaryRows(metricObj.value, feature, prettifyLabel, formatAny); }
function getSummaryRows(feature) { return sharedBuildSummaryRows(metricObj.value, feature, prettifyLabel, formatAny); }
function getConditionsKey(feature) { const obj = getFeatureObject(feature); return obj ? getConditionsKeyForFeature(obj) : null; }
function getConditionsRows(feature) {
  const obj = getFeatureObject(feature); const key = getConditionsKey(feature);
  if (!obj || !key || !isPlainObject(obj[key])) return [];
  return Object.entries(obj[key]).map(([condName, condObj]) => ({ condition: condName, ...(isPlainObject(condObj) ? condObj : {}) }));
}
function getConditionsColumns(feature) {
  const rows = getConditionsRows(feature);
  if (!rows.length) return [];
  const set = new Set();
  for (const row of rows) { for (const k of Object.keys(row)) { if (k !== "condition") set.add(k); } }
  const all = Array.from(set);
  const tail = ["raw_difference", "normalized_score", "weight", "total_samples"];
  const head = all.filter((k) => !tail.includes(k)).sort();
  const end = tail.filter((k) => all.includes(k));
  return [...head, ...end];
}
function getSummaryKeyForFeature(featureKey) { return sharedGetSummaryKeyForFeature(metricObj.value, featureKey); }
function getSummaryTitle(featureKey) { const key = getSummaryKeyForFeature(featureKey); return key ? prettifyLabel(key) : "Summary"; }
function getConditionsFirstColTitle(feature) { const key = getConditionsKey(feature); return key ? prettifyLabel(key) : "Conditions"; }
function getConditionsTableTitle(feature) { const key = getConditionsKey(feature); return key ? `${prettifyLabel(key)} Table` : "Conditions Table"; }

// Numeric Mode Helpers
function markerLeft(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0%";
  const clamped = Math.max(0, Math.min(10, num));
  return `${(clamped / 10) * 100}%`;
}
function valueClass(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  if (num >= 8) return "ok";
  if (num >= 5) return "warn";
  return "bad";
}
function toNumberMaybe(x) {
  if (typeof x === "number") return x;
  if (x && typeof x === "object") {
    const vals = Object.values(x);
    if (vals.length === 1 && typeof vals[0] === "number") return vals[0];
  }
  return null;
}
function extractFeatureValues(metricObjLocal) {
  const out = [];
  if (!metricObjLocal || typeof metricObjLocal !== "object") return out;
  for (const [featureName, featureVal] of Object.entries(metricObjLocal)) {
    if (featureName === "(global)") continue;
    const num = toNumberMaybe(featureVal);
    if (num !== null) out.push({ label: featureName, value: num });
  }
  return out;
}

onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";
    
    const res = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    const all = data?.results?.results ?? data?.results ?? data ?? {};
    metricObj.value = all[metricKey.value];

    if (!metricObj.value) { error.value = `Metric "${metricKey.value}" not found.`; return; }

    const extracted = extractFeatureValues(metricObj.value);
    if (extracted.length) {
      items.value = extracted;
    } else {
      featureKeys.value.forEach(ensureFeatureState);
      if (featureKeys.value.length > 0) activeFeatureTab.value = featureKeys.value[0];
    }

  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="result-layout">
    <div class="header-area">
      <div class="header-top">
        <div class="domain-tag">{{ prettifyLabel(group) }}</div>
        <button class="btn-ghost" @click="goBackSafely">← Back to Dashboard</button>
      </div>
      <h1 class="metric-title">{{ prettifyLabel(metricKey) }}</h1>
      <p class="metric-subtitle">Review evaluation results and adjust contextual impact.</p>
    </div>

    <div v-if="loading" class="state-msg">Loading results...</div>
    <div v-else-if="error" class="error-banner">{{ error }}</div>

    <div v-else-if="items.length" class="numeric-mode-container">
      <h2 class="section-label">Feature Scores</h2>
      <div class="numeric-cards-grid">
        <div v-for="it in items" :key="it.label" class="num-card">
          <div class="num-header">
            <h3>{{ prettifyLabel(it.label) }}</h3>
            <span class="num-badge" :class="valueClass(it.value)">{{ Number(it.value).toFixed(3) }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: markerLeft(it.value) }"></div>
          </div>
          <div class="progress-labels">
            <span>0</span><span>5</span><span>10</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="featureKeys.length" class="nested-split">
      <aside class="tabs-sidebar">
        <h3 class="tabs-title">Evaluated Features</h3>
        <div class="tabs-list">
          <button v-for="k in featureKeys" :key="k" class="tab-btn" :class="{ 'is-active': activeFeatureTab === k }" @click="activeFeatureTab = k">
            {{ prettifyLabel(k) }}
            <span class="status-dot" :class="isFeatureSaved(k) ? 'saved' : 'pending'"></span>
          </button>
        </div>
      </aside>

      <main class="active-feature-content" v-if="activeFeatureTab">
        
        <div class="data-block">
          <h2 class="section-label">Results for {{ prettifyLabel(activeFeatureTab) }}</h2>
          <div class="data-cards-grid">
            <div class="data-card" v-if="getContextSummaryRows(activeFeatureTab).length">
              <h3>Context</h3>
              <div class="keyval-list">
                <div v-for="r in getContextSummaryRows(activeFeatureTab)" :key="r.key" class="keyval-item">
                  <span class="key">{{ prettifyLabel(r.key) }}</span><span class="val mono">{{ formatAny(r.value) }}</span>
                </div>
              </div>
            </div>

            <div class="data-card" v-if="getSummaryRows(activeFeatureTab).length">
              <h3>{{ getSummaryTitle(activeFeatureTab) }}</h3>
              <div class="keyval-list">
                <div v-for="r in getSummaryRows(activeFeatureTab)" :key="r.key" class="keyval-item">
                  <span class="key">{{ prettifyLabel(r.key) }}</span><span class="val mono">{{ formatAny(r.value) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="table-card" v-if="getConditionsRows(activeFeatureTab).length">
            <h3>{{ getConditionsTableTitle(activeFeatureTab) }}</h3>
            <div class="table-responsive">
              <table class="modern-table">
                <thead>
                  <tr>
                    <th>{{ getConditionsFirstColTitle(activeFeatureTab) }}</th>
                    <th v-for="c in getConditionsColumns(activeFeatureTab)" :key="c">{{ formatHeaderKey(c) }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in getConditionsRows(activeFeatureTab)" :key="r.condition">
                    <td><strong>{{ Number(r.condition) ? Number(r.condition).toFixed(3) : r.condition }}</strong></td>
                    <td v-for="c in getConditionsColumns(activeFeatureTab)" :key="c" class="mono">{{ formatAny(r[c]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="weight-block">
          <h2 class="section-label">Contextual Impact</h2>
          <div class="weight-card">
            <div class="weight-header">
              <p class="help-text">Set the specific weight (0-10) for this feature. Default is 5.</p>
              <span class="weight-display">W = {{ getFeatureWeight(activeFeatureTab) }}</span>
            </div>

            <input type="range" min="0" max="10" step="0.5" :value="getFeatureWeight(activeFeatureTab)" @input="setFeatureWeight(activeFeatureTab, $event.target.value)" class="modern-slider" />

            <div class="justification-area" :class="{ 'is-active': featureNeedsJustification(activeFeatureTab) }">
              <div v-if="featureNeedsJustification(activeFeatureTab)">
                <div class="just-header">
                  <label>Justification</label>
                  <span v-if="!isFeatureValid(activeFeatureTab)" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                  <span v-else class="ok-badge">Valid ✓</span>
                </div>
                <textarea :value="getFeatureJustification(activeFeatureTab)" @input="setFeatureJustification(activeFeatureTab, $event.target.value)" class="modern-textarea" rows="3" placeholder="Explain this weight..."></textarea>
              </div>
              <div v-else class="just-placeholder">
                <p>Weight is 5. No justification needed.</p>
              </div>
            </div>

            <div class="action-row">
              <span class="save-status" :class="{ 'is-saved': isFeatureSaved(activeFeatureTab) }">
                {{ isFeatureSaved(activeFeatureTab) ? '✓ Saved' : 'Unsaved changes' }}
              </span>
              <button class="btn-primary" :disabled="saving || !isFeatureValid(activeFeatureTab)" @click="saveFeature(activeFeatureTab)">
                {{ saving ? "Saving..." : "Save Feature" }}
              </button>
            </div>
            <div v-if="saveError" class="error-msg">{{ saveError }}</div>

          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.result-layout { max-width: 1300px; margin: 0 auto; padding: 2rem; font-family: 'Inter', sans-serif; color: #111; }
.header-area { margin-bottom: 3rem; }
.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; }
.btn-ghost:hover { color: #111; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

/* Numeric Mode */
.numeric-mode-container { width: 100%; margin-top: 1rem; }
.numeric-cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }
.num-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; }
.num-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.num-header h3 { margin: 0; font-size: 1.1rem; color: #111; }
.num-badge { font-family: 'JetBrains Mono', monospace; font-weight: 700; padding: 4px 10px; border-radius: 6px; }
.num-badge.ok { background: #dcfce7; color: #065f46; }
.num-badge.warn { background: #fef3c7; color: #92400e; }
.num-badge.bad { background: #fee2e2; color: #991b1b; }
.progress-track { height: 8px; background: #f0f0f0; border-radius: 999px; overflow: hidden; margin-bottom: 0.5rem; }
.progress-fill { height: 100%; background: #111; border-radius: 999px; transition: width 0.3s ease; }
.progress-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: #888; font-weight: 600; }

/* Nested Split Mode */
.nested-split { display: grid; grid-template-columns: 240px 1fr; gap: 3rem; align-items: start; }
@media (max-width: 900px) { .nested-split { grid-template-columns: 1fr; } }
.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.5rem; }
.tabs-sidebar { position: sticky; top: 2rem; }
.tabs-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #555; margin-bottom: 1rem; }
.tabs-list { display: flex; flex-direction: column; gap: 0.5rem; }
.tab-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; text-align: left; background: #fff; border: 1px solid #e5e5e5; padding: 1rem; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #555; cursor: pointer; transition: 0.2s; }
.tab-btn:hover { border-color: #111; color: #111; }
.tab-btn.is-active { background: #111; color: #fff; border-color: #111; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.saved { background: #10b981; }
.status-dot.pending { background: #f59e0b; }
.active-feature-content { display: flex; flex-direction: column; gap: 3rem; }
.data-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; }
.data-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; color: #111; }
.keyval-list { display: flex; flex-direction: column; gap: 0.8rem; }
.keyval-item { display: flex; justify-content: space-between; border-bottom: 1px solid #f9f9f9; padding-bottom: 0.4rem; }
.key { font-size: 0.85rem; color: #666; font-weight: 600; }
.val { font-weight: 700; }
.table-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; overflow: hidden; }
.table-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; }
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
.modern-table th { background: #fafafa; padding: 1rem; font-weight: 600; color: #555; border-bottom: 2px solid #e5e5e5; white-space: nowrap; }
.modern-table td { padding: 1rem; border-bottom: 1px solid #f0f0f0; }
.modern-table tr:hover td { background: #fdfdfd; }
.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
.weight-card { background: #fafafa; border: 1px solid #e5e5e5; border-radius: 12px; padding: 2rem; }
.weight-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
.help-text { font-size: 0.9rem; color: #666; margin: 0; max-width: 80%; }
.weight-display { font-family: 'JetBrains Mono', monospace; font-weight: 700; background: #111; color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 0.9rem; }
.modern-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; transition: 0.2s; margin-bottom: 2rem; }
.modern-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #1243e3; cursor: pointer; border: 2px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
.justification-area { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; padding: 1.2rem; transition: 0.3s; margin-bottom: 1.5rem; }
.justification-area.is-active { border-color: #111; }
.just-header { display: flex; justify-content: space-between; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 6px; font-family: 'Inter', sans-serif; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1243e3; }
.just-placeholder p { margin: 0; font-size: 0.9rem; color: #888; text-align: center; font-style: italic; }
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.save-status { font-size: 0.9rem; font-weight: 600; color: #f59e0b; }
.save-status.is-saved { color: #10b981; }
.btn-primary { background: #111; color: #fff; border: 1px solid #111; padding: 0.8rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.btn-primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
.error-msg { color: #e11d48; font-size: 0.9rem; margin-top: 1rem; font-weight: 500; }
</style>