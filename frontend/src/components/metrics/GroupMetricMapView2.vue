<script setup>
import { API_HOST } from "../../utils/config";
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildGroupMapFeatureSavePayload,
  buildContextSummaryRows as sharedBuildContextSummaryRows,
  buildSummaryRows as sharedBuildSummaryRows,
  getFeatureObject as sharedGetFeatureObject,
  getSummaryKeyForFeature as sharedGetSummaryKeyForFeature,
  getSessionId
} from "../../utils/report_builder_helper";

const route = useRoute();
const group = computed(() => String(route.params.group || ""));

const props = defineProps({ 
  runId: { type: [String, Number], required: true },
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true }
});

const emit = defineEmits(["go-back-safe"]);

const activeFeatureTab = ref("");
const MIN_JUST_LENGTH = 10;

const showHeavyTables = ref(false);

const DEFAULT_GRAVITY = 1;
const featureGravity = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function getGravityLabel(val) {
  const v = Number(val);
  if (v < 1.5) return "Low";
  if (v < 2.5) return "Low-Medium";
  if (v < 3.5) return "Medium";
  if (v < 4.5) return "Medium-High";
  return "High";
}

function ensureFeatureState(feature) {
  const featData = props.metricObj?.[feature] || {};

  if (!(feature in featureGravity.value)) {
    const savedGrav = featData.user_weight ?? featData.user_weight_report ?? featData.gravity ?? featData.gravity_report;
    featureGravity.value[feature] = savedGrav !== undefined ? Number(savedGrav) : DEFAULT_GRAVITY;
  }
  if (!(feature in featureJustifications.value)) {
    let savedJust = featData.user_justification ?? featData.user_justification_report ?? featData.justification;
    if (savedJust === DEFAULT_WEIGHT_JUSTIFICATION) savedJust = "";
    featureJustifications.value[feature] = savedJust !== undefined ? String(savedJust) : "";
  }
  if (!(feature in savedFeatures.value)) {
    const userHasSaved = featData.user_weight_report !== undefined || featData.user_justification_report !== undefined;
    savedFeatures.value[feature] = userHasSaved;
  }
}

function isFeatureSaved(feature) { ensureFeatureState(feature); return !!savedFeatures.value[feature]; }
function getFeatureGravity(feature) { ensureFeatureState(feature); return Number.isFinite(Number(featureGravity.value[feature])) ? Number(featureGravity.value[feature]) : DEFAULT_GRAVITY; }
function setFeatureGravity(feature, val) { ensureFeatureState(feature); featureGravity.value[feature] = Number(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function getFeatureJustification(feature) { ensureFeatureState(feature); return String(featureJustifications.value[feature] || ""); }
function setFeatureJustification(feature, val) { ensureFeatureState(feature); featureJustifications.value[feature] = String(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }

function featureNeedsJustification(feature) { ensureFeatureState(feature); return Number(getFeatureGravity(feature)) > 1; }

function isFeatureValid(feature) { 
  ensureFeatureState(feature); 
  const justLen = String(getFeatureJustification(feature)).trim().length;
  if (featureNeedsJustification(feature)) return justLen >= MIN_JUST_LENGTH;
  return justLen === 0 || justLen >= MIN_JUST_LENGTH;
}

async function saveFeature(feature) {
  ensureFeatureState(feature);
  if (saving.value) return;
  const gravityValue = Number(getFeatureGravity(feature));
  const userText = String(getFeatureJustification(feature)).trim();
  
  const justification = (gravityValue <= 1 && userText.length === 0) ? DEFAULT_WEIGHT_JUSTIFICATION : userText;
  
  if (!isFeatureValid(feature)) { saveError.value = `Justification required.`; return; }

  saving.value = true; saveError.value = ""; saveOk.value = false;

  try {
    const payload = buildGroupMapFeatureSavePayload({
      runId: props.runId, session_id: getSessionId(), group: group.value, metric: props.metricKey, schemaType: schemaTypeReport.value, 
      feature, metricObj: props.metricObj, weight: gravityValue, justification, formatLabel: prettifyLabel, formatValue: formatAny,
    });
    
    payload.gravity = gravityValue;
    payload.session_id = getSessionId();

    const resp = await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
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
      const payload = buildGroupMapFeatureSavePayload({
        runId: props.runId, group: group.value, metric: props.metricKey, schemaType: schemaTypeReport.value, 
        feature, metricObj: props.metricObj, weight: DEFAULT_GRAVITY, justification: DEFAULT_WEIGHT_JUSTIFICATION, formatLabel: prettifyLabel, formatValue: formatAny,
      });
      payload.gravity = DEFAULT_GRAVITY;
      await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      featureGravity.value[feature] = DEFAULT_GRAVITY; featureJustifications.value[feature] = ""; savedFeatures.value[feature] = true;
    }
  } catch (e) { console.error(e); } finally { saving.value = false; }
}

async function goBackSafely() { 
  if (activeFeatureTab.value && !isFeatureSaved(activeFeatureTab.value) && isFeatureValid(activeFeatureTab.value)) {
    await saveFeature(activeFeatureTab.value);
  }
  await saveMissingFeaturesWithDefaultWeight(); 
  emit("go-back-safe"); 
}
defineExpose({ goBackSafely });

const featureKeys = computed(() => {
  const obj = props.metricObj;
  if (!obj || typeof obj !== "object") return [];
  return Object.keys(obj).filter(k => k !== "__combined__" && k !== "(global)" && k !== "final_score" && k !== "gravity" && k !== "reversibility");
});

const resultSchemas = ref({});
const schemaTypeReport = computed(() => resultSchemas.value?.[props.metricKey]?.schema ?? null);

async function loadResultSchemas() {
  try {
    const resp = await fetch(`${API_HOST}/results/result_schemas?run_id=${encodeURIComponent(props.runId)}`);
    if (resp.ok) resultSchemas.value = await resp.json();
  } catch (e) {}
}

function prettifyLabel(str) { return (!str || typeof str !== "string") ? "" : str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function formatAny(v) { return typeof v === "number" ? (Number.isFinite(v) ? v.toFixed(3) : "—") : String(v); }
function isPlainObjectLocal(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }

function getContextSummaryRows(feature) { return sharedBuildContextSummaryRows(props.metricObj, feature, prettifyLabel, formatAny); }
function getSummaryRows(feature) { return sharedBuildSummaryRows(props.metricObj, feature, prettifyLabel, formatAny); }
function getSummaryTitle(featureKey) { const key = sharedGetSummaryKeyForFeature(props.metricObj, featureKey); return key ? prettifyLabel(key) : "Summary"; }

onMounted(() => {
  loadResultSchemas();
  featureKeys.value.forEach(ensureFeatureState);
  if (featureKeys.value.length > 0) activeFeatureTab.value = featureKeys.value[0];
});
</script>

<template>
  <div class="result-layout">
    
    <div v-if="loading" class="state-msg">Loading results...</div>
    <div v-else-if="error" class="error-banner">{{ error }}</div>

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
        
        <div class="weight-block">
          <div class="weight-card executive-panel">
            
            <div class="weight-header">
              <label class="gravity-label">Contextual Impact</label>
            </div>

            <div class="slider-container">
  <div class="slider-labels-top">
    <span>Gravity</span>
    <span class="weight-display">
      {{ Number(getFeatureGravity(activeFeatureTab)).toFixed(2) }} - {{ getGravityLabel(getFeatureGravity(activeFeatureTab)) }}
    </span>
  </div>
  
  <input 
    type="range" min="1" max="5" step="0.01" 
    :value="getFeatureGravity(activeFeatureTab)" 
    @input="setFeatureGravity(activeFeatureTab, $event.target.value)" 
    class="premium-slider" 
  />
  
  <div class="ticks-labels">
    <div class="tick-item"><span>Low</span></div>
    <div class="tick-item"><span>Low-Med</span></div>
    <div class="tick-item"><span>Medium</span></div>
    <div class="tick-item"><span>Med-High</span></div>
    <div class="tick-item"><span>High</span></div>
  </div>
</div>
               

            <div class="justification-area is-active">
              <div class="just-header">
                <label>Justification</label>
                <span v-if="!isFeatureValid(activeFeatureTab)" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                <span v-else-if="!featureNeedsJustification(activeFeatureTab) && getFeatureJustification(activeFeatureTab).trim().length === 0" class="optional-badge">Optional</span>
                <span v-else class="ok-badge">Valid ✓</span>
              </div>
              <textarea :value="getFeatureJustification(activeFeatureTab)" @input="setFeatureJustification(activeFeatureTab, $event.target.value)" class="modern-textarea" rows="2" placeholder="Explain the Gravity score..."></textarea>
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

        <div class="data-block">
          <button class="toggle-heavy-btn" @click="showHeavyTables = !showHeavyTables">
            {{ showHeavyTables ? '▲ HIDE RAW DATA SUMMARY' : '▼ VIEW RAW DATA SUMMARY' }}
          </button>

          <div v-show="showHeavyTables">
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
                    <span class="key">{{ (r.key === 'final_score' || r.key === 'final score') ? 'Likelihood' : prettifyLabel(r.key) }}</span>
                    <span class="val mono">{{ formatAny(r.value) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </main>
    </div>
  </div>
</template>

<style scoped>
.result-layout { font-family: 'Inter', sans-serif; color: #111; margin-top: 10px; }
.nested-split { display: grid; grid-template-columns: 240px 1fr; gap: 3rem; align-items: start; }
@media (max-width: 900px) { .nested-split { grid-template-columns: 1fr; } }
.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.5rem; }

.tabs-sidebar { position: sticky; top: 2rem; }
.tabs-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #555; margin-bottom: 1rem; }
.tabs-list { display: flex; flex-direction: column; gap: 0.5rem; }
.tab-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; text-align: left; background: #fff; border: 1px solid #e5e5e5; padding: 1rem; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #555; cursor: pointer; transition: 0.2s; }
.tab-btn:hover { border-color:  #1243e3; color:  #1243e3; }
.tab-btn.is-active { background:  #1243e3; color: #fff; border-color:  #1243e3; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.saved { background: #10b981; }
.status-dot.pending { background: #f59e0b; }

.executive-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 2.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 30px; }
.weight-header { margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }
.gravity-label { font-size: 14px; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; }

.slider-container { margin-bottom: 35px; }
.slider-labels-top { display: flex; justify-content: space-between; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; }
.weight-display { color: #1243e3; }
.premium-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; margin-bottom: 10px; }
.premium-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 22px; height: 22px; border-radius: 50%; background:  #1243e3; cursor: pointer; border: 4px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
.ticks-labels { display: flex; justify-content: space-between; padding: 0 5px; }
.tick-item { flex: 1; text-align: center; }
.tick-item:first-child { text-align: left; }
.tick-item:last-child { text-align: right; }
.tick-item span { font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; }

.justification-area { background: #f8fafc; border: 1px solid #e5e5e5; border-radius: 8px; padding: 1.2rem; transition: 0.3s; margin-bottom: 1.5rem; }
.justification-area.is-active { border-color: #cbd5e1; border-left: 4px solid  #1243e3; }
.just-header { display: flex; justify-content: space-between; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.optional-badge { font-size: 0.75rem; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 6px; font-family: 'Inter', sans-serif; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color:  #1243e3; }
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.save-status { font-size: 0.9rem; font-weight: 600; color: #f59e0b; }
.save-status.is-saved { color: #10b981; }
.btn-primary { background:  #1243e3; color: #fff; border: none; padding: 0.8rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }

.toggle-heavy-btn { width: 100%; background: #f1f5f9; color:  #1243e3; border: 1px dashed #cbd5e1; padding: 15px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; cursor: pointer; border-radius: 8px; transition: 0.2s; margin-bottom: 20px;}
.toggle-heavy-btn:hover { background: #e2e8f0; }
.data-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; }
.data-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; color: #111; }
.keyval-list { display: flex; flex-direction: column; gap: 0.8rem; }
.keyval-item { display: flex; justify-content: space-between; border-bottom: 1px solid #f9f9f9; padding-bottom: 0.4rem; }
.key { font-size: 0.85rem; color: #666; font-weight: 600; }
.val { font-weight: 700; color: #1e293b; }
.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
</style>