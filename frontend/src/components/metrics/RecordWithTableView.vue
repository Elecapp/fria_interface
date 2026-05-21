<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
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
    ? Object.keys(props.metricObj).filter((k) => k !== "__combined__" && k !== "(global)" && k !== "final_score" && k !== "gravity" && k !== "reversibility")
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
    if (k === "final_score" || k === "gravity" || k === "reversibility") continue; // Filtra chiavi di sistema
    
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

// --- STATI EXECUTIVE ---
const MIN_JUST_LENGTH = 10;
const DEFAULT_GRAVITY = 0;
const metricGravity = ref(DEFAULT_GRAVITY);
const metricReversibility = ref(false);
const metricJustification = ref("");

const gravityLabels = {
  0: "0 - None",
  1: "1 - Low",
  2: "2 - Medium",
  3: "3 - High",
  4: "4 - Very High"
};

function isChangedMetric() { return Number(metricGravity.value) > 0; }
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
  const finalGravity = isChangedMetric() ? Number(metricGravity.value) : DEFAULT_GRAVITY;
  
  const payload = buildRecordWithTableSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    metricObj: contextReport,
    userWeight: finalGravity, 
    userJustification: finalGravity === DEFAULT_GRAVITY ? DEFAULT_WEIGHT_JUSTIFICATION : String(metricJustification.value || "").trim(),
  });

  // Aggiungiamo i dati per il nuovo backend Python
  payload.gravity = finalGravity;
  payload.reversibility = metricReversibility.value;

  return payload;
}

async function postSaveMetric() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildSavePayload()),
  });
  if (!resp.ok) throw new Error("Failed to save data");
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

const emit = defineEmits(["go-back-safe"]);
async function goBackSafely() {
  if (isChangedMetric() && canSave.value) {
    await onSave();
  } else if (!isChangedMetric()) {
    try { await postSaveMetric(); } catch(e){}
  }
  emit("go-back-safe");
}
defineExpose({ goBackSafely });
</script>

<template>
  <div class="result-layout">
    
    <div class="content-split">
      
      <div class="results-column">
        
        <div v-if="summaryRows.length" class="executive-panel" style="margin-bottom: 20px;">
          <h3 style="margin-top:0;">Summary</h3>
          <div class="metrics-grid">
            <div v-for="r in summaryRows" :key="r.key" class="data-item">
              <span class="data-key">{{ (r.key === 'final_score' || r.key === 'final score') ? 'Likelihood' : prettifyLabel(r.key) }}</span>
              <span class="data-value mono-text">{{ formatAny(r.value) }}</span>
            </div>
          </div>
        </div>

        <div v-for="tb in tableBlocks" :key="tb.key" class="table-card executive-panel" style="padding: 0; overflow: hidden; margin-bottom: 20px;">
          <h3 style="padding: 20px 20px 10px 20px; margin:0;">{{ tb.title }}</h3>
          <div class="table-responsive">
            <table class="modern-table">
              <thead>
                <tr>
                  <th v-for="c in tb.columns" :key="c">{{ prettifyLabel(c) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in tb.rows" :key="idx">
                  <td v-for="c in tb.columns" :key="c" class="mono-text">{{ formatAny(r[c]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="!summaryRows.length && !tableBlocks.length" class="executive-panel empty-state">
          <h3>Raw output</h3>
          <pre class="raw-data">{{ JSON.stringify(featureObj || metricObj, null, 2) }}</pre>
        </div>
      </div>

      <div class="context-column">
        
        <div class="weight-card executive-panel">
          
          <div class="weight-header" style="margin-bottom: 20px;">
            <label class="gravity-label">Contextual Impact</label>
          </div>
          
          <div class="slider-container">
            <div class="slider-labels-top">
              <span>Gravity</span>
              <span class="weight-display">{{ gravityLabels[metricGravity] }}</span>
            </div>
            
            <input 
              type="range" min="0" max="4" step="1" 
              v-model.number="metricGravity" 
              class="premium-slider"
            />
            
            <div class="ticks-labels">
              <div class="tick-item"><span>None</span></div>
              <div class="tick-item"><span>Low</span></div>
              <div class="tick-item"><span>Med</span></div>
              <div class="tick-item"><span>High</span></div>
              <div class="tick-item"><span>Very High</span></div>
            </div>
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
                rows="3" 
                placeholder="Explain the impact..."
              ></textarea>
            </div>
            <div v-else class="just-placeholder">
              <p>Gravity is None. No justification needed.</p>
            </div>
          </div>

          <div v-if="saveError" class="error-msg-box">{{ saveError }}</div>

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
.result-layout { font-family: 'Inter', sans-serif; color: #111; margin-top: 10px; }
.content-split { display: grid; grid-template-columns: 1fr 400px; gap: 2rem; align-items: start; }
@media (max-width: 900px) { .content-split { grid-template-columns: 1fr; } }
.section-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; color: #888; margin: 0 0 1rem 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }

/* EXECUTIVE PANEL STYLES */
.executive-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }

/* Left Column - Data */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; margin-top: 15px;}
.data-item { display: flex; flex-direction: column; gap: 0.5rem; padding-bottom: 1rem; border-bottom: 1px solid #f0f0f0; }
.data-key { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
.data-value { font-size: 1.8rem; font-weight: 700; color: #1e293b; line-height: 1; }
.mono-text { font-family: 'JetBrains Mono', monospace; }

/* Tables */
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
.modern-table th { background: #f8fafc; padding: 12px; font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0; white-space: nowrap; font-family: 'JetBrains Mono', monospace; font-size: 11px; text-transform: uppercase; }
.modern-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; }
.empty-state { color: #666; }
.raw-data { background: #f8fafc; padding: 1rem; border-radius: 8px; font-size: 0.85rem; overflow-x: auto; border: 1px solid #e5e5e5; }

/* Right Column - Impact */
.weight-card { position: sticky; top: 20px; }
.gravity-label { font-size: 14px; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; }

.slider-container { margin-bottom: 30px; }
.slider-labels-top { display: flex; justify-content: space-between; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; }
.weight-display { color: #1243e3; }
.premium-slider { -webkit-appearance: none; width: 100%; height: 6px; border-radius: 999px; background: #e5e5e5; outline: none; margin-bottom: 10px; }
.premium-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 22px; height: 22px; border-radius: 50%; background: #1A365D; cursor: pointer; border: 4px solid #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
.ticks-labels { display: flex; justify-content: space-between; padding: 0 5px; }
.tick-item { flex: 1; text-align: center; }
.tick-item:first-child { text-align: left; }
.tick-item:last-child { text-align: right; }
.tick-item span { font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; }

.reversibility-toggle { display: flex; align-items: center; gap: 12px; cursor: pointer; margin-bottom: 25px; }
.reversibility-toggle input { display: none; }
.checkbox-box { width: 24px; height: 24px; border: 2px solid #cbd5e1; display: inline-block; position: relative; transition: 0.2s; border-radius: 4px; }
.reversibility-toggle input:checked ~ .checkbox-box { background-color: #1A365D; border-color: #1A365D; }
.reversibility-toggle input:checked ~ .checkbox-box:after { content: ""; position: absolute; left: 7px; top: 3px; width: 5px; height: 11px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.checkbox-text { font-family: 'Inter', sans-serif; font-size: 0.95rem; font-weight: 600; color: #1e293b; }

.justification-area { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.2rem; transition: 0.3s; margin-bottom: 1.5rem; }
.justification-area.is-active { border-color: #cbd5e1; border-left: 4px solid #1A365D; }
.just-header { display: flex; justify-content: space-between; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e2e8f0; border-radius: 6px; font-family: 'Inter', sans-serif; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1A365D; }
.just-placeholder p { margin: 0; font-size: 0.9rem; color: #888; text-align: center; font-style: italic; }

.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 1.5rem; }
.btn-primary { background: #1A365D; color: #fff; border: none; padding: 1rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 1rem; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }
.error-msg-box { color: #e11d48; font-size: 0.9rem; font-weight: 600; text-align: center; background: #fff1f2; padding: 10px; border-radius: 6px; margin-bottom: 15px;}
</style>