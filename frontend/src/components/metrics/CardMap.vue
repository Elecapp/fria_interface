<script setup>
import { computed, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_HOST } from "../../utils/config";

import {
  DEFAULT_WEIGHT_JUSTIFICATION,
  isPlainObject,
  isScalar,
  buildCardMapSavePayload,
  getSessionId
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
    if (k === "final_score" || k === "gravity" || k === "reversibility") continue;

    const smallArray = Array.isArray(v) && v.length <= 80 && v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (isScalar(v) || smallArray) rows.push({ key: k, value: v });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
});

// --- STATI EXECUTIVE ---
const MIN_JUST_LENGTH = 10;
const DEFAULT_GRAVITY = 1;
const metricGravity = ref(DEFAULT_GRAVITY);
const metricJustification = ref("");

onMounted(() => {
  let savedData = props.metricObj || {};
  
  if (savedData["(global)"]) {
    savedData = { ...savedData, ...savedData["(global)"] };
  }

  const savedGrav = savedData.user_weight ?? savedData.user_weight_report ?? savedData.gravity ?? savedData.gravity_report;
  if (savedGrav !== undefined) metricGravity.value = Number(savedGrav);

  let savedJust = savedData.user_justification ?? savedData.user_justification_report ?? savedData.justification;
  if (savedJust === DEFAULT_WEIGHT_JUSTIFICATION) savedJust = "";
  if (savedJust !== undefined) metricJustification.value = String(savedJust);
});

function getGravityLabel(val) {
  const v = Number(val);
  if (v < 1.5) return "Low";
  if (v < 2.5) return "Low-Medium";
  if (v < 3.5) return "Medium";
  if (v < 4.5) return "Medium-High";
  return "High";
}

function metricNeedsJustification() { return Number(metricGravity.value) > 1; }

const missingJustifications = computed(() => {
  const txt = String(metricJustification.value || "").trim();
  if (metricNeedsJustification() && txt.length < MIN_JUST_LENGTH) return ["(global)"];
  return [];
});

const canSave = computed(() => {
  return missingJustifications.value.length === 0;
});

// Save state
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

function buildSavePayload() {
  const contextReport = Object.fromEntries(
    summaryRows.value.map((row) => [prettifyLabel(row.key), row.value])
  );
  
  const finalGravity = Number(metricGravity.value);
  const userText = String(metricJustification.value || "").trim();
  
  const justification = (finalGravity <= 1 && userText.length === 0) ? DEFAULT_WEIGHT_JUSTIFICATION : userText;

  const payload = buildCardMapSavePayload({
    runId: props.runId,
    sessionId: getSessionId(),
    group: group.value,
    metric: props.metricKey,
    metricObj: { "(global)": { context_report: contextReport } },
    userWeight: finalGravity,
    userJustification: justification,
  });

  payload.gravity = finalGravity;
  

  return payload;
}

async function postSaveWeights() {
  const resp = await fetch(`${API_HOST}/results/save_weights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save data");
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
    // NIENTE PIÙ router.back() QUI!
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

const emit = defineEmits(["go-back-safe"]);
async function goBackSafely() {
  if (canSave.value) {
    await onSave();
  }
  emit("go-back-safe"); // Ora è lui e solo lui a innescare il ritorno!
}
defineExpose({ goBackSafely });
</script>

<template>
  <div class="result-layout">
    
    <div class="content-split">
      
      <div class="results-column">
        
        <div class="executive-panel data-card">
          <h3 style="margin-top:0;">Summary</h3>
          <div v-if="summaryRows.length" class="metrics-grid">
            <div v-for="r in summaryRows" :key="r.key" class="data-item">
              <span class="data-key">{{ (r.key === 'final_score' || r.key === 'final score') ? 'Likelihood' : prettifyLabel(r.key) }}</span>
              <span class="data-value mono-text">{{ formatAny(r.value) }}</span>
            </div>
          </div>
          
          <div v-else class="empty-state">
            <p>No formatted summary available.</p>
            <pre class="raw-data">{{ JSON.stringify(cardRecord || metricObj, null, 2) }}</pre>
          </div>
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
              <span v-if="missingJustifications.length" class="req-badge">Req. (min {{ MIN_JUST_LENGTH }} chars)</span>
              <span v-else-if="!metricNeedsJustification() && metricJustification.trim().length === 0" class="optional-badge">Optional</span>
              <span v-else class="ok-badge">Valid ✓</span>
            </div>
            <textarea 
              v-model="metricJustification" 
              class="modern-textarea" 
              rows="3" 
              placeholder="Explain the Gravity score..."
            ></textarea>
          </div>

          <div v-if="saveError" class="error-msg-box">{{ saveError }}</div>

          <div class="action-row">
            <button class="btn-primary" :disabled="!canSave || saving" @click="goBackSafely" style="width: 100%;">
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

.executive-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }

.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; margin-top: 15px;}
.data-item { display: flex; flex-direction: column; gap: 0.5rem; padding-bottom: 1rem; border-bottom: 1px solid #f0f0f0; }
.data-key { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
.data-value { font-size: 1.8rem; font-weight: 700; color: #1e293b; line-height: 1; }
.mono-text { font-family: 'JetBrains Mono', monospace; }

.empty-state { color: #666; }
.raw-data { background: #f8fafc; padding: 1rem; border-radius: 8px; font-size: 0.85rem; overflow-x: auto; margin-top: 1rem; border: 1px solid #e5e5e5; }

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

.justification-area { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.2rem; transition: 0.3s; margin-bottom: 1.5rem; }
.justification-area.is-active { border-color: #cbd5e1; border-left: 4px solid #1A365D; }
.just-header { display: flex; justify-content: space-between; margin-bottom: 0.8rem; }
.just-header label { font-size: 0.9rem; font-weight: 700; }
.req-badge { font-size: 0.75rem; font-weight: 700; color: #e11d48; background: #fff1f2; padding: 2px 6px; border-radius: 4px; }
.ok-badge { font-size: 0.75rem; font-weight: 700; color: #16a34a; background: #f0fdf4; padding: 2px 6px; border-radius: 4px; }
.optional-badge { font-size: 0.75rem; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
.modern-textarea { width: 100%; padding: 0.8rem; border: 1px solid #e2e8f0; border-radius: 6px; font-family: 'Inter', sans-serif; resize: vertical; box-sizing: border-box; }
.modern-textarea:focus { outline: none; border-color: #1A365D; }

.action-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 1.5rem; }
.btn-primary { background: #1A365D; color: #fff; border: none; padding: 1rem 1.5rem; border-radius: 6px; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 1rem; cursor: pointer; transition: 0.2s; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }
.error-msg-box { color: #e11d48; font-size: 0.9rem; font-weight: 600; text-align: center; background: #fff1f2; padding: 10px; border-radius: 6px; margin-bottom: 15px;}
</style>