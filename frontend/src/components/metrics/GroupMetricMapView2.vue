<script setup>
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";

import {
  DEFAULT_WEIGHT_JUSTIFICATION,
  isPlainObject,
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

// --- STATI EXECUTIVE E PROGRESSIVE DISCLOSURE ---
const showHeavyTables = ref(false);
const DEFAULT_GRAVITY = 0;
const featureGravity = ref({});
const featureReversibility = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});

const gravityLabels = {
  0: "0 - None",
  1: "1 - Low",
  2: "2 - Medium",
  3: "3 - High",
  4: "4 - Very High"
};

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

const featureKeys = computed(() => props.metricObj && typeof props.metricObj === "object" ? Object.keys(props.metricObj).filter(k => k !== "__combined__" && k !== "(global)" && k !== "final_score" && k !== "gravity" && k !== "reversibility") : []);

function ensureFeatureState(feature) {
  if (!(feature in featureGravity.value)) featureGravity.value[feature] = DEFAULT_GRAVITY;
  if (!(feature in featureReversibility.value)) featureReversibility.value[feature] = false;
  if (!(feature in featureJustifications.value)) featureJustifications.value[feature] = "";
  if (!(feature in savedFeatures.value)) savedFeatures.value[feature] = false;
}

function isFeatureSaved(feature) { ensureFeatureState(feature); return !!savedFeatures.value[feature]; }
function getFeatureGravity(feature) { ensureFeatureState(feature); return Number.isFinite(Number(featureGravity.value[feature])) ? Number(featureGravity.value[feature]) : DEFAULT_GRAVITY; }
function setFeatureGravity(feature, val) { ensureFeatureState(feature); featureGravity.value[feature] = Number(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function getFeatureReversibility(feature) { ensureFeatureState(feature); return !!featureReversibility.value[feature]; }
function setFeatureReversibility(feature, val) { ensureFeatureState(feature); featureReversibility.value[feature] = val; savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function getFeatureJustification(feature) { ensureFeatureState(feature); return String(featureJustifications.value[feature] || ""); }
function setFeatureJustification(feature, val) { ensureFeatureState(feature); featureJustifications.value[feature] = String(val); savedFeatures.value[feature] = false; saveOk.value = false; saveError.value = ""; }
function featureNeedsJustification(feature) { ensureFeatureState(feature); return Number(getFeatureGravity(feature)) > 0; }
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

  const gravityValue = Number(getFeatureGravity(feature));
  const reversibilityValue = getFeatureReversibility(feature);
  const justification = gravityValue === DEFAULT_GRAVITY ? DEFAULT_WEIGHT_JUSTIFICATION : String(getFeatureJustification(feature) || "");

  if (!isFeatureValid(feature)) { saveError.value = "Justification required."; return; }

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    const payload = buildGroupMapFeatureSavePayload({
      runId: props.runId, metric: props.metricKey, schemaType: schemaTypeReport.value,
      feature, metricObj: props.metricObj, weight: gravityValue, justification, formatLabel: prettifyLabel, formatValue: formatAny,
    });
    
    // Iniettiamo i nuovi campi
    payload.gravity = gravityValue;
    payload.reversibility = reversibilityValue;

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
        feature, metricObj: props.metricObj, weight: DEFAULT_GRAVITY, justification: DEFAULT_WEIGHT_JUSTIFICATION, formatLabel: prettifyLabel, formatValue: formatAny,
      });
      
      payload.gravity = DEFAULT_GRAVITY;
      payload.reversibility = false;

      await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      featureGravity.value[feature] = DEFAULT_GRAVITY;
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
    
    <div v-if="featureKeys.length === 0" class="error-json-box">No features available for this metric.</div>

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
        
        <div class="weight-block">
          <div class="weight-card executive-panel">
            
            <div class="weight-header">
              <label class="gravity-label">Contextual Impact</label>
            </div>

            <div class="slider-container">
              <div class="slider-labels-top">
                <span>Gravity</span>
                <span class="weight-display">{{ gravityLabels[getFeatureGravity(activeFeatureTab)] }}</span>
              </div>
              
              <input 
                type="range" min="0" max="4" step="1" 
                :value="getFeatureGravity(activeFeatureTab)" 
                @input="setFeatureGravity(activeFeatureTab, $event.target.value)" 
                class="premium-slider" 
              />
              
              <div class="ticks-labels">
                <div class="tick-item"><span>None</span></div>
                <div class="tick-item"><span>Low</span></div>
                <div class="tick-item"><span>Medium</span></div>
                <div class="tick-item"><span>High</span></div>
                <div class="tick-item"><span>Very High</span></div>
              </div>
            </div>



            <div class="justification-area" :class="{ 'is-active': featureNeedsJustification(activeFeatureTab) }">
              <div v-if="featureNeedsJustification(activeFeatureTab)">
                <div class="just-header">
                  <label>Justification</label>
                  <span v-if="!isFeatureValid(activeFeatureTab)" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
                  <span v-else class="ok-badge">Valid ✓</span>
                </div>
                <textarea :value="getFeatureJustification(activeFeatureTab)" @input="setFeatureJustification(activeFeatureTab, $event.target.value)" class="modern-textarea" rows="2" placeholder="Explain the impact..."></textarea>
              </div>
              <div v-else class="just-placeholder">
                <p>Gravity is None. No justification needed.</p>
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
            <div v-if="saveError" class="error-msg-box" style="margin-top:10px;">{{ saveError }}</div>

          </div>
        </div>

        <div class="data-block">
          <button class="toggle-heavy-btn" @click="showHeavyTables = !showHeavyTables">
            {{ showHeavyTables ? '▲ HIDE CONTEXT CONDITION TABLE & DISPARITY SUMMARY' : '▼ VIEW CONTEXT CONDITION TABLE & DISPARITY SUMMARY' }}
          </button>

          <div v-show="showHeavyTables">
            
            <div class="data-cards-grid">
              
              <div class="data-card" v-if="getSummaryRows(activeFeatureTab).length">
                <h3>Summary</h3>
                <div class="keyval-list">
                  <div v-for="r in getSummaryRows(activeFeatureTab)" :key="r.key" class="keyval-item">
                    <span class="key">{{ (r.key === 'final_score' || r.key === 'final score') ? 'Likelihood' : prettifyLabel(r.key) }}</span>
                    <span class="val mono">{{ r.value }}</span>
                  </div>
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

/* Sidebar Tabs */
.tabs-sidebar { position: sticky; top: 2rem; }
.tabs-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #555; margin-bottom: 1rem; }
.tabs-list { display: flex; flex-direction: column; gap: 0.5rem; }
.tab-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; text-align: left; background: #fff; border: 1px solid #e5e5e5; padding: 1rem; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #555; cursor: pointer; transition: 0.2s; }
.tab-btn:hover { border-color: #1A365D; color: #1A365D; }
.tab-btn.is-active { background: #1A365D; color: #fff; border-color: #1A365D; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.saved { background: #10b981; }
.status-dot.pending { background: #f59e0b; }

/* Pannello Executive */
.executive-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 2.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 30px; }
.weight-header { margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }
.gravity-label { font-size: 14px; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; }

/* Slider Modifiche */
.slider-container { margin-bottom: 35px; }
.slider-labels-top { display: flex; justify-content: space-between; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; }
.weight-display { color: #1243e3; }
.premium-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; margin-bottom: 10px; }
.premium-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 22px; height: 22px; border-radius: 50%; background: #1A365D; cursor: pointer; border: 4px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
.ticks-labels { display: flex; justify-content: space-between; padding: 0 5px; }
.tick-item { flex: 1; text-align: center; }
.tick-item:first-child { text-align: left; }
.tick-item:last-child { text-align: right; }
.tick-item span { font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; }

/* Reversibility */
.reversibility-toggle { display: flex; align-items: center; gap: 12px; cursor: pointer; margin-bottom: 25px; }
.reversibility-toggle input { display: none; }
.checkbox-box { width: 24px; height: 24px; border: 2px solid #cbd5e1; display: inline-block; position: relative; transition: 0.2s; border-radius: 4px; }
.reversibility-toggle input:checked ~ .checkbox-box { background-color: #1A365D; border-color: #1A365D; }
.reversibility-toggle input:checked ~ .checkbox-box:after { content: ""; position: absolute; left: 7px; top: 3px; width: 5px; height: 11px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.checkbox-text { font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #1e293b; }

/* Giustificazione e Bottoni */
.justification-area { background: #f8fafc; border: 1px solid #e5e5e5; border-radius: 8px; padding: 1.2rem; transition: 0.3s; margin-bottom: 1.5rem; }
.justification-area.is-active { border-color: #cbd5e1; border-left: 4px solid #1A365D; }
.just-header { display: flex; justify-content: space-between; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e5e5e5; border-radius: 6px; font-family: 'Inter', sans-serif; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1A365D; }
.just-placeholder p { margin: 0; font-size: 0.9rem; color: #888; text-align: center; font-style: italic; }
.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e5e5; padding-top: 1.5rem; }
.save-status { font-size: 0.9rem; font-weight: 600; color: #f59e0b; }
.save-status.is-saved { color: #10b981; }
.btn-primary { background: #1A365D; color: #fff; border: none; padding: 0.8rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }
.error-msg-box { color: #e11d48; font-size: 0.9rem; font-weight: 600; text-align: center; background: #fff1f2; padding: 10px; border-radius: 6px; }
.error-json-box { background: #fef2f2; border: 1px solid #fecaca; padding: 16px; color: #991b1b; border-radius: 8px;}

/* Dati Tabelle */
.toggle-heavy-btn { width: 100%; background: #f1f5f9; color: #1A365D; border: 1px dashed #cbd5e1; padding: 15px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; cursor: pointer; border-radius: 8px; transition: 0.2s; margin-bottom: 20px;}
.toggle-heavy-btn:hover { background: #e2e8f0; }
.data-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem; }
.data-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; }
.data-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; color: #111; }
.keyval-list { display: flex; flex-direction: column; gap: 0.8rem; }
.keyval-item { display: flex; justify-content: space-between; border-bottom: 1px solid #f9f9f9; padding-bottom: 0.4rem; }
.key { font-size: 0.85rem; color: #666; font-weight: 600; }
.val { font-weight: 700; color: #1e293b; }
.table-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; overflow: hidden; }
.table-card h3 { font-size: 1.1rem; margin: 0 0 1rem 0; }
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
.modern-table th { background: #fafafa; padding: 1rem; font-weight: 600; color: #555; border-bottom: 2px solid #e5e5e5; white-space: nowrap; }
.modern-table td { padding: 1rem; border-bottom: 1px solid #f0f0f0; }
.mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
</style>