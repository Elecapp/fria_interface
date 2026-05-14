<script setup>
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";

import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  rowsToDict,
  isPlainObject,
  isScalar,
  looksLikeGroupMap,
  buildGroupMapSummaryRows,
  buildGroupMapFeatureSavePayload,
} from "../../utils/report_builder_helper";

const route = useRoute();
const group = computed(() => String(route.params.group || ""));

const emit = defineEmits(["go-back-safe"]);

const props = defineProps({
  runId: { type: [String, Number], required: true },
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true },
});

const MIN_JUST_LENGTH = 10;
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

const activeFeatureTab = ref("");

function prettifyLabel(str) { return !str ? "" : String(str).replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }
function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "—";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}
function formatGroupLabel(v) {
  const num = Number(v);
  if (!Number.isNaN(num) && String(v).trim() !== "") return Number.isInteger(num) ? String(num) : num.toFixed(3);
  return prettifyLabel(String(v));
}

const featureKeys = computed(() => props.metricObj && typeof props.metricObj === "object" ? Object.keys(props.metricObj).filter(k => k !== "__combined__" && k !== "(global)") : []);

const featureWeights = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});

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

const resultSchemas = ref({});
const schemaTypeReport = computed(() => resultSchemas.value?.[props.metricKey]?.schema ?? null);

async function loadResultSchemas() {
  try {
    const resp = await fetch(`http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(props.runId)}`);
    if (resp.ok) resultSchemas.value = await resp.json();
  } catch (e) { console.error(e); }
}

onMounted(loadResultSchemas);

function getFeatureObject(featureKey) {
  if (!props.metricObj || !featureKey) return null;
  const obj = props.metricObj[featureKey];
  return isPlainObject(obj) ? obj : null;
}

function buildSummaryRows(featureKey) { return buildGroupMapSummaryRows(props.metricObj, featureKey, prettifyLabel, formatAny); }
function getSummaryRows(feature) { return buildSummaryRows(feature); }

function getGroupMapKey(feature) { const o = getFeatureObject(feature); return isPlainObject(o) ? Object.keys(o).find(k => looksLikeGroupMap(o[k])) ?? null : null; }
function getGroupMapObj(feature) { const o = getFeatureObject(feature); const key = getGroupMapKey(feature); return key ? o?.[key] ?? null : null; }
function getGroupMapTitle(feature) { const key = getGroupMapKey(feature); return key ? `${prettifyLabel(key)} Table` : "Distribution Table"; }
function getFirstColTitle(feature) { const key = getGroupMapKey(feature); return key ? prettifyLabel(key) : "Group"; }

function getRows(feature) {
  const obj = getGroupMapObj(feature);
  if (!isPlainObject(obj)) return [];
  return Object.entries(obj).map(([g, value]) => ({ group: g, value: Number.isFinite(Number(value)) ? Number(value) : null }));
}

async function saveFeature(feature) {
  ensureFeatureState(feature);
  if (saving.value) return;

  const weight = Number(getFeatureWeight(feature));
  const justification = weight === DEFAULT_WEIGHT ? DEFAULT_WEIGHT_JUSTIFICATION : String(getFeatureJustification(feature) || "");

  if (!isFeatureValid(feature)) { saveError.value = "Justification required."; return; }

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    const payload = buildGroupMapFeatureSavePayload({
      runId: props.runId, metric: props.metricKey, schemaType: schemaTypeReport.value,
      feature, metricObj: props.metricObj, weight, justification, formatLabel: prettifyLabel, formatValue: formatAny,
    });
    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!resp.ok) throw new Error("Failed to save feature");
    
    savedFeatures.value[feature] = true;
    saveOk.value = true;
  } catch (e) { saveError.value = e?.message || String(e); } finally { saving.value = false; }
}

async function saveMissingFeaturesWithDefaultWeight() {
  if (saving.value) return;
  saving.value = true;
  try {
    for (const feature of featureKeys.value) {
      ensureFeatureState(feature);
      if (isFeatureSaved(feature)) continue;
      const payload = buildGroupMapFeatureSavePayload({
        runId: props.runId, metric: props.metricKey, schemaType: schemaTypeReport.value,
        feature, metricObj: props.metricObj, weight: DEFAULT_WEIGHT, justification: DEFAULT_WEIGHT_JUSTIFICATION, formatLabel: prettifyLabel, formatValue: formatAny,
      });
      await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      featureWeights.value[feature] = DEFAULT_WEIGHT;
      featureJustifications.value[feature] = DEFAULT_WEIGHT_JUSTIFICATION;
      savedFeatures.value[feature] = true;
    }
  } catch (e) { console.error(e); } finally { saving.value = false; }
}

async function goBackSafely() {
  await saveMissingFeaturesWithDefaultWeight();
  emit("go-back-safe");
}

defineExpose({ goBackSafely });

onMounted(() => {
  for (const feature of featureKeys.value) ensureFeatureState(feature);
  if (featureKeys.value.length > 0) activeFeatureTab.value = featureKeys.value[0];
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
      <p class="metric-subtitle">Review group distributions and adjust their contextual impact.</p>
    </div>

    <div v-if="featureKeys.length === 0" class="error-banner">No features available for this metric.</div>

    <div v-else class="nested-split">
      <aside class="tabs-sidebar">
        <h3 class="tabs-title">Evaluated Features</h3>
        <div class="tabs-list">
          <button 
            v-for="k in featureKeys" :key="k" 
            class="tab-btn" :class="{ 'is-active': activeFeatureTab === k }" 
            @click="activeFeatureTab = k"
          >
            {{ prettifyLabel(k) }}
            <span class="status-dot" :class="isFeatureSaved(k) ? 'saved' : 'pending'"></span>
          </button>
        </div>
      </aside>

      <main class="active-feature-content" v-if="activeFeatureTab">
        
        <div class="data-block">
          <h2 class="section-label">Results for {{ prettifyLabel(activeFeatureTab) }}</h2>
          
          <div class="data-card" v-if="getSummaryRows(activeFeatureTab).length">
            <h3>Summary</h3>
            <div class="keyval-list">
              <div v-for="r in getSummaryRows(activeFeatureTab)" :key="r.key" class="keyval-item">
                <span class="key">{{ prettifyLabel(r.key) }}</span>
                <span class="val mono">{{ r.value }}</span>
              </div>
            </div>
          </div>

          <div class="table-card" v-if="getRows(activeFeatureTab).length && getGroupMapKey(activeFeatureTab)">
            <h3>{{ getGroupMapTitle(activeFeatureTab) }}</h3>
            <div class="table-responsive">
              <table class="modern-table">
                <thead>
                  <tr>
                    <th>{{ getFirstColTitle(activeFeatureTab) }}</th>
                    <th>Values</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in getRows(activeFeatureTab)" :key="r.group">
                    <td><strong>{{ formatGroupLabel(r.group) }}</strong></td>
                    <td class="mono">{{ r.value === null ? "—" : r.value.toFixed(3) }}</td>
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
.result-layout { max-width: 1200px; margin: 0 auto; padding: 2rem; font-family: 'Inter', sans-serif; color: #111; }
.header-area { margin-bottom: 3rem; }
.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.domain-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; }
.btn-ghost { background: transparent; border: none; font-family: 'Inter', sans-serif; font-weight: 600; color: #666; cursor: pointer; transition: 0.2s; }
.btn-ghost:hover { color: #111; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; margin: 0 0 0.5rem 0; color: #1A365D; line-height: 1.1; }
.metric-subtitle { font-size: 1.1rem; color: #555; max-width: 700px; line-height: 1.5; margin: 0; }
.error-banner { background: #fff1f2; color: #e11d48; padding: 1rem; border-radius: 8px; border: 1px solid #fecdd3; text-align: center; }

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
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
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
.modern-table th { background: #fafafa; padding: 1rem; font-weight: 600; color: #555; border-bottom: 2px solid #e5e5e5; }
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