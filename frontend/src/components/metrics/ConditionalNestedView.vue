<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const group = computed(() => String(route.params.group || ""));
const metricKey = computed(() => String(route.params.metric || ""));

const loading = ref(false);
const error = ref("");

const metricObj = ref(null);
const items = ref([]); 

const props = defineProps({
  runId: { type: String, required: true },
});

const emit = defineEmits(["go-back-safe"]);

// --- GESTIONE TABS (Nuovo approccio UX) ---
const activeFeatureTab = ref("");

const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;
const DEFAULT_WEIGHT_JUSTIFICATION = "Since no weight has been assigned, the default weight 5 has been used";

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

function setFeatureWeight(feature, val) {
  ensureFeatureState(feature);
  featureWeights.value[feature] = Number(val);
  savedFeatures.value[feature] = false;
  saveOk.value = false;
  saveError.value = "";
}

function getFeatureJustification(feature) { ensureFeatureState(feature); return String(featureJustifications.value[feature] || ""); }

function setFeatureJustification(feature, val) {
  ensureFeatureState(feature);
  featureJustifications.value[feature] = String(val);
  savedFeatures.value[feature] = false;
  saveOk.value = false;
  saveError.value = "";
}

function featureNeedsJustification(feature) { ensureFeatureState(feature); return Number(getFeatureWeight(feature)) !== DEFAULT_WEIGHT; }
function isFeatureValid(feature) {
  ensureFeatureState(feature);
  if (!featureNeedsJustification(feature)) return true;
  return String(getFeatureJustification(feature)).trim().length >= MIN_JUST_LENGTH;
}

async function saveFeature(feature) {
  ensureFeatureState(feature);
  if (saving.value) return;

  const weight = Number(getFeatureWeight(feature));
  const justification = Number(weight) === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(getFeatureJustification(feature) || "");

  if (!isFeatureValid(feature)) {
    saveError.value = `Justification required for ${prettifyLabel(feature)}.`;
    return;
  }

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    const contextRows = buildContextSummaryRows(feature);
    const summaryRowsLocal = buildSummaryRows(feature);

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value,
        metric: metricKey.value,
        schema_type_report: schemaTypeReport.value,
        context_report: { [feature]: rowsToDict(contextRows) },
        summary_report: { [feature]: rowsToDict(summaryRowsLocal) },
        weights: { [feature]: weight },
        justifications: { [feature]: justification },
      }),
    });

    if (!resp.ok) throw new Error("Failed to save feature");

    savedFeatures.value[feature] = true;
    saveOk.value = true;
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

async function saveMissingFeaturesWithDefaultWeight() {
  if (saving.value) return;
  saving.value = true;

  try {
    for (const feature of featureKeys.value) {
      ensureFeatureState(feature);
      if (isFeatureSaved(feature)) continue;

      const contextRows = buildContextSummaryRows(feature);
      const summaryRowsLocal = buildSummaryRows(feature);

      await fetch("http://127.0.0.1:8000/results/save_weights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: props.runId,
          group: group.value,
          metric: metricKey.value,
          schema_type_report: schemaTypeReport.value,
          weights: { [feature]: DEFAULT_WEIGHT },
          justifications: { [feature]: DEFAULT_WEIGHT_JUSTIFICATION },
          context_report: { [feature]: rowsToDict(contextRows) },
          summary_report: { [feature]: rowsToDict(summaryRowsLocal) },
        }),
      });

      featureWeights.value[feature] = DEFAULT_WEIGHT;
      featureJustifications.value[feature] = DEFAULT_WEIGHT_JUSTIFICATION;
      savedFeatures.value[feature] = true;
    }
  } catch (e) {
    console.error("Auto-save failed", e);
  } finally {
    saving.value = false;
  }
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

function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) out[String(r.key)] = r.value;
  return out;
}

const resultSchemas = ref({});
const schemaTypeReport = computed(() => resultSchemas.value?.[metricKey.value]?.schema ?? null);

async function loadResultSchemas() {
  try {
    const resp = await fetch(`http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(props.runId)}`);
    if (resp.ok) resultSchemas.value = await resp.json();
  } catch (e) { console.error(e); }
}

onMounted(loadResultSchemas);

function prettifyLabel(str) {
  if (!str || typeof str !== "string") return "";
  return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : String(v);
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "string") return v;
  return String(v);
}

function formatHeaderKey(k) {
  const num = Number(k);
  return !Number.isNaN(num) && k !== "" ? num.toFixed(3) : prettifyLabel(k);
}

function isPlainObject(v) { return v && typeof v === "object" && !Array.isArray(v); }
function isScalar(v) { return v === null || v === undefined || ["string", "number", "boolean"].includes(typeof v); }

function flattenObject(obj, prefix = "", out = {}) {
  if (!isPlainObject(obj)) return out;
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (isScalar(v)) out[key] = v;
    else if (isPlainObject(v)) flattenObject(v, key, out);
  }
  return out;
}

function looksLikeGroupMap(v) {
  if (!isPlainObject(v)) return false;
  const entries = Object.entries(v);
  return entries.length > 0 && entries.every(([k, val]) => typeof k === "string" && isScalar(val));
}

function getFeatureObject(featureKey) {
  if (!metricObj.value || !featureKey) return null;
  const obj = metricObj.value[featureKey];
  return isPlainObject(obj) ? obj : null;
}

function getConditionsKeyForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return null;
  let bestKey = null, bestRows = -1;
  for (const [k, v] of Object.entries(featureObjLocal)) {
    if (!isPlainObject(v)) continue;
    const rows = Object.values(v);
    if (rows.length > 0 && rows.every(isPlainObject) && rows.length > bestRows) {
      bestRows = rows.length; bestKey = k;
    }
  }
  return bestKey;
}

function getTableDictKeysForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return [];
  const keys = Object.keys(featureObjLocal);
  const groupMaps = keys.filter((k) => looksLikeGroupMap(featureObjLocal[k]));
  const dictOfDicts = keys.filter((k) => {
    const v = featureObjLocal[k];
    return isPlainObject(v) && Object.values(v).length > 0 && Object.values(v).every(isPlainObject);
  });
  return Array.from(new Set([...groupMaps, ...dictOfDicts]));
}

function buildContextSummaryRows(featureKey) {
  const o = getFeatureObject(featureKey);
  if (!isPlainObject(o)) return [];
  const exclude = new Set(getTableDictKeysForFeature(o));
  const rows = [];
  for (const [k, v] of Object.entries(o)) {
    if (!exclude.has(k) && isScalar(v)) {
      rows.push({ key: k, value: typeof v === "string" ? prettifyLabel(v) : formatAny(v) });
    }
  }
  return rows.sort((a, b) => a.key.localeCompare(b.key));
}

function getSummaryKeyForFeature(featureKey) {
  const f = getFeatureObject(featureKey);
  if (!isPlainObject(f)) return null;
  let bestKey = null, bestSize = -1;
  for (const [k, v] of Object.entries(f)) {
    if (!isPlainObject(v)) continue;
    const rows = Object.values(v);
    if (rows.length > 0 && rows.every(isPlainObject)) continue;
    const size = Object.keys(flattenObject(v)).length;
    if (size > bestSize) { bestSize = size; bestKey = k; }
  }
  return bestKey;
}

function buildSummaryRows(featureKey) {
  const f = getFeatureObject(featureKey);
  if (!isPlainObject(f)) return [];
  const summaryKey = getSummaryKeyForFeature(featureKey);
  if (!summaryKey || !isPlainObject(f[summaryKey])) return [];
  const flat = flattenObject(f[summaryKey]);
  return Object.keys(flat).sort().map((k) => ({ key: k, value: formatAny(flat[k]) }));
}

function getContextSummaryRows(feature) { return buildContextSummaryRows(feature); }
function getSummaryRows(feature) { return buildSummaryRows(feature); }
function getConditionsKey(feature) { const obj = getFeatureObject(feature); return obj ? getConditionsKeyForFeature(obj) : null; }

function getConditionsRows(feature) {
  const obj = getFeatureObject(feature);
  const key = getConditionsKey(feature);
  if (!obj || !key || !isPlainObject(obj[key])) return [];
  return Object.entries(obj[key]).map(([condName, condObj]) => ({
    condition: condName,
    ...(isPlainObject(condObj) ? condObj : {}),
  }));
}

function getConditionsColumns(feature) {
  const rows = getConditionsRows(feature);
  if (!rows.length) return [];
  const set = new Set();
  for (const row of rows) {
    for (const k of Object.keys(row)) { if (k !== "condition") set.add(k); }
  }
  const all = Array.from(set);
  const tail = ["raw_difference", "normalized_score", "weight", "total_samples"];
  const head = all.filter((k) => !tail.includes(k)).sort();
  const end = tail.filter((k) => all.includes(k));
  return [...head, ...end];
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

    if (!metricObj.value) {
      error.value = `Metric "${metricKey.value}" not found.`;
      return;
    }

    featureKeys.value.forEach(ensureFeatureState);
    if (featureKeys.value.length > 0) activeFeatureTab.value = featureKeys.value[0];

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
      <p class="metric-subtitle">Review nested feature conditions and adjust their contextual impact.</p>
    </div>

    <div v-if="loading" class="state-msg">Loading nested results...</div>
    <div v-else-if="error" class="error-banner">{{ error }}</div>

    <div v-else-if="featureKeys.length" class="nested-split">
      
      <aside class="tabs-sidebar">
        <h3 class="tabs-title">Evaluated Features</h3>
        <div class="tabs-list">
          <button 
            v-for="k in featureKeys" 
            :key="k" 
            class="tab-btn" 
            :class="{ 'is-active': activeFeatureTab === k }"
            @click="activeFeatureTab = k"
          >
            {{ prettifyLabel(k) }}
            <span v-if="isFeatureSaved(k)" class="status-dot saved" title="Saved"></span>
            <span v-else class="status-dot pending" title="Pending Save"></span>
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
                  <span class="key">{{ prettifyLabel(r.key) }}</span>
                  <span class="val mono">{{ formatAny(r.value) }}</span>
                </div>
              </div>
            </div>

            <div class="data-card" v-if="getSummaryRows(activeFeatureTab).length">
              <h3>Summary</h3>
              <div class="keyval-list">
                <div v-for="r in getSummaryRows(activeFeatureTab)" :key="r.key" class="keyval-item">
                  <span class="key">{{ prettifyLabel(r.key) }}</span>
                  <span class="val mono">{{ formatAny(r.value) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="table-card" v-if="getConditionsRows(activeFeatureTab).length">
            <h3>Conditions Table</h3>
            <div class="table-responsive">
              <table class="modern-table">
                <thead>
                  <tr>
                    <th>Condition</th>
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

            <input 
              type="range" min="0" max="10" step="0.5" 
              :value="getFeatureWeight(activeFeatureTab)" 
              @input="setFeatureWeight(activeFeatureTab, $event.target.value)" 
              class="modern-slider"
            />

            <div class="justification-area" :class="{ 'is-active': featureNeedsJustification(activeFeatureTab) }">
              <div v-if="featureNeedsJustification(activeFeatureTab)">
                <div class="just-header">
                  <label>Justification</label>
                  <span v-if="!isFeatureValid(activeFeatureTab)" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                  <span v-else class="ok-badge">Valid ✓</span>
                </div>
                <textarea 
                  :value="getFeatureJustification(activeFeatureTab)" 
                  @input="setFeatureJustification(activeFeatureTab, $event.target.value)" 
                  class="modern-textarea" rows="3" placeholder="Explain this weight..."
                ></textarea>
              </div>
              <div v-else class="just-placeholder">
                <p>Weight is 5. No justification needed.</p>
              </div>
            </div>

            <div class="action-row">
              <span class="save-status" :class="{ 'is-saved': isFeatureSaved(activeFeatureTab) }">
                {{ isFeatureSaved(activeFeatureTab) ? '✓ Saved' : 'Unsaved changes' }}
              </span>
              <button 
                class="btn-primary" 
                :disabled="saving || !isFeatureValid(activeFeatureTab)" 
                @click="saveFeature(activeFeatureTab)"
              >
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
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1243e3; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }

.nested-split { display: grid; grid-template-columns: 240px 1fr; gap: 3rem; align-items: start; }
@media (max-width: 900px) { .nested-split { grid-template-columns: 1fr; } }

.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.5rem; }

/* Tabs Sidebar */
.tabs-sidebar { position: sticky; top: 2rem; }
.tabs-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #555; margin-bottom: 1rem; }
.tabs-list { display: flex; flex-direction: column; gap: 0.5rem; }
.tab-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; text-align: left; background: #fff; border: 1px solid #e5e5e5; padding: 1rem; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #555; cursor: pointer; transition: 0.2s; }
.tab-btn:hover { border-color: #111; color: #111; }
.tab-btn.is-active { background: #111; color: #fff; border-color: #111; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.saved { background: #10b981; }
.status-dot.pending { background: #f59e0b; }

/* Active Content */
.active-feature-content { display: flex; flex-direction: column; gap: 3rem; }

/* Data Cards */
.data-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; }
.data-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; color: #111; }
.keyval-list { display: flex; flex-direction: column; gap: 0.8rem; }
.keyval-item { display: flex; justify-content: space-between; border-bottom: 1px solid #f9f9f9; padding-bottom: 0.4rem; }
.key { font-size: 0.85rem; color: #666; font-weight: 600; }
.val { font-weight: 700; }

/* Table */
.table-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; overflow: hidden; }
.table-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; }
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
.modern-table th { background: #fafafa; padding: 1rem; font-weight: 600; color: #555; border-bottom: 2px solid #e5e5e5; white-space: nowrap; }
.modern-table td { padding: 1rem; border-bottom: 1px solid #f0f0f0; }
.modern-table tr:hover td { background: #fdfdfd; }

.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }

/* Weight Block */
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