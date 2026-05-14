<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();

const error = ref("");
const loading = ref(true);

const cfg = ref({});
const columns = ref([]);
const pluginRegistry = ref({});   
const selectedMetricIds = ref([]); 
const form = ref({});             

function flattenSelectedMetrics(metricsObj) {
  const vals = Object.values(metricsObj || {});
  return vals.flat().filter(Boolean);
}

function initDefaultValue(param) {
  const t = (param?.type || "").toLowerCase();
  if (t.startsWith("list")) return [];
  if (t === "int" || t === "integer" || t === "float" || t === "number") return param.default !== null ? param.default : null;
  return param.default !== null ? param.default : ""; 
} 

function shouldSkipParam(p) {
  return p?.key === "sensitive_features";
}

const metricCards = computed(() => {
  const out = [];
  for (const metricId of selectedMetricIds.value) {
    const spec = pluginRegistry.value?.[metricId];
    if (!spec) continue;

    const params = (Array.isArray(spec.params) ? spec.params : []).filter((p) => !shouldSkipParam(p));
    
    if (params.length === 0) continue;

    if (!form.value[metricId]) form.value[metricId] = {};

    for (const p of params) {
      if (form.value[metricId][p.key] === undefined) {
        form.value[metricId][p.key] = initDefaultValue(p);
      }
    }

    out.push({
      id: metricId,
      name: spec.name || metricId,
      description: spec.description || "",
      right: spec.right || "General",
      params,
    });
  }
  return out;
});

function validate() {
  error.value = "";
  if (!metricCards.value.length) return true; // Se nessuna metrica richiede parametri, passiamo.

  for (const card of metricCards.value) {
    for (const p of card.params) {
      if (!p.required) continue;

      const val = form.value?.[card.id]?.[p.key];
      const t = (p.type || "").toLowerCase();

      if (t.startsWith("list")) {
        if (!Array.isArray(val) || val.length === 0) {
          error.value = `Required: Select at least one value for "${p.label}" in ${card.name}.`;
          return false;
        }
      } else if (["int", "integer", "float", "number"].includes(t)) {
        if (val === null || val === undefined || val === "") {
          error.value = `Required: Enter a numerical value for "${p.label}" in ${card.name}.`;
          return false;
        }
      } else {
        if (!val) {
          error.value = `Required: Select a value for "${p.label}" in ${card.name}.`;
          return false;
        }
      }
    }
  }
  return true;
}

const canGoNext = computed(() => {
  if (metricCards.value.length === 0) return true;

  for (const card of metricCards.value) {
    for (const p of card.params) {
      if (!p.required) continue;
      const val = form.value?.[card.id]?.[p.key];
      const t = String(p.type || "").toLowerCase();

      if (t.startsWith("list")) {
        if (!Array.isArray(val) || val.length === 0) return false;
      } else if (["int", "integer", "float", "number"].includes(t)) {
        if (val === null || val === undefined || val === "") return false;
      } else {
        if (!val) return false;
      }
    }
  }
  return true;
});

function buildPayload() {
  const payload = {};
  for (const card of metricCards.value) {
    const specParams = pluginRegistry.value?.[card.id]?.params || [];
    const allowedKeys = specParams.filter((p) => !shouldSkipParam(p)).map((p) => p.key);
    
    const cleaned = {};
    for (const k of allowedKeys) {
      cleaned[k] = form.value[card.id]?.[k];
    }
    payload[card.id] = cleaned;
  }
  return payload;
}

async function fetchLatestConfig() {
  const res = await fetch("http://127.0.0.1:8000/configs/latest");
  if (!res.ok) throw new Error("Failed to fetch configuration");
  const payload = await res.json();
  const c = payload.config || payload;
  cfg.value = c;
  selectedMetricIds.value = flattenSelectedMetrics(c.metrics || {});
}

async function fetchPluginRegistry() {
  const res = await fetch("http://127.0.0.1:8000/plugin-registry");
  if (!res.ok) throw new Error("Failed to fetch plugin registry");
  pluginRegistry.value = await res.json();
}

async function fetchLatestColumns() {
  const res = await fetch("http://127.0.0.1:8000/headers");
  if (!res.ok) throw new Error("Failed to fetch dataset columns");
  const data = await res.json();
  columns.value = Array.isArray(data?.columns) ? data.columns : [];
}

function goBack() { router.back(); }

async function goNext() {
  if (!validate()) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }

  try {
    const payload = buildPayload();
    if (Object.keys(payload).length > 0) {
      const res = await fetch("http://127.0.0.1:8000/configs/parameters", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to save parameters");
    }
    router.push("/rm2"); // Oppure dove deve andare
  } catch (e) {
    error.value = e?.message || String(e);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    await Promise.all([fetchLatestConfig(), fetchPluginRegistry(), fetchLatestColumns()]);
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <ProcessStepper :current-step="3" />
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Configure Metrics</h1>
        <p class="description">
          Some of the evaluation modules you selected require specific parameters to run correctly. Define them below based on your dataset logic.
        </p>

        <div v-if="loading" class="state-msg">Loading configuration...</div>
        <div v-else-if="error" class="error-banner">{{ error }}</div>

        <div v-else-if="metricCards.length === 0" class="empty-state-box">
          <div class="icon-wrap">✓</div>
          <h3>All set!</h3>
          <p>The metrics you selected do not require any additional configuration.</p>
        </div>

        <div v-else class="metrics-stack">
          <section v-for="card in metricCards" :key="card.id" class="metric-card">
            <div class="card-left">
              <div class="domain-badge">{{ card.right.replace(/_/g, ' ') }}</div>
              <h2 class="metric-name">{{ card.name }}</h2>
              <p class="metric-desc">{{ card.description }}</p>
            </div>

            <div class="card-right">
              <div v-for="p in card.params" :key="p.key" class="param-field">
                
                <div class="field-header">
                  <label class="field-label">
                    {{ p.label || p.key }}
                    <span v-if="p.required" class="required-star">*</span>
                  </label>
                  <span v-if="p.help" class="help-text" :title="p.help">ⓘ</span>
                </div>
                <p v-if="p.help" class="inline-help">{{ p.help }}</p>

                <select v-if="Array.isArray(p.enum) && p.enum.length" v-model="form[card.id][p.key]" class="modern-input select-icon">
                  <option value="" disabled>Select an option...</option>
                  <option v-for="opt in p.enum" :key="opt" :value="opt">{{ opt }}</option>
                </select>

                <div v-else-if="String(p.type).toLowerCase().startsWith('list')" class="options-box">
                  <label v-for="c in columns" :key="c" class="option-row">
                    <input type="checkbox" :value="c" v-model="form[card.id][p.key]" class="custom-checkbox" />
                    <span class="option-text">{{ c }}</span>
                  </label>
                </div>

                <div v-else-if="String(p.type).toLowerCase() === 'string' && (p.key.includes('attribute') || p.key.includes('variable'))" class="options-box">
                  <label v-for="c in columns" :key="c" class="option-row">
                    <input type="radio" :name="`${card.id}__${p.key}`" :value="c" v-model="form[card.id][p.key]" class="custom-radio" />
                    <span class="option-text">{{ c }}</span>
                  </label>
                </div>

                <input v-else-if="['int','integer','float','number'].includes(String(p.type).toLowerCase())" type="number" v-model.number="form[card.id][p.key]" class="modern-input" placeholder="0" />

                <input v-else type="text" v-model="form[card.id][p.key]" class="modern-input" placeholder="Type here..." />

              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <span v-if="!canGoNext" class="hint">Fill all required fields</span>
        <button class="nav-btn primary" :disabled="!canGoNext" @click="goNext">Next step →</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-layout { min-height: 100vh; background-color: #faf9f8; display: flex; flex-direction: column; padding-bottom: 120px; }
.top-nav { height: 50px; background-color: #1a1a1a; display: flex; align-items: center; padding: 0 2rem; }
.nav-brand { color: #fff; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.9rem; }
.hero-container { flex: 1; display: flex; justify-content: center; padding-top: 4vh; }
.hero-content { max-width: 1000px; width: 100%; padding: 0 2rem; }
.back-button { background: none; border: none; color: #888; cursor: pointer; margin-bottom: 1.5rem; transition: 0.2s; font-family: 'Inter', sans-serif; }
.back-button:hover { color: #111; transform: translateX(-4px); }

.main-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; color: #1243e3; margin-bottom: 0.5rem; }
.description { font-family: 'Inter', sans-serif; font-size: 1.1rem; color: #555; line-height: 1.6; margin-bottom: 3rem; max-width: 800px; }

.state-msg { color: #666; font-family: 'Inter', sans-serif; }
.error-banner { background: #fff1f2; color: #e11d48; padding: 1rem 1.5rem; border-radius: 8px; font-size: 0.95rem; border: 1px solid #fecdd3; font-weight: 500; margin-bottom: 2rem; }

/* Empty State */
.empty-state-box { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 4rem 2rem; text-align: center; display: flex; flex-direction: column; align-items: center; }
.empty-state-box .icon-wrap { width: 64px; height: 64px; background: #f0fdf4; color: #16a34a; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; margin-bottom: 1rem; }
.empty-state-box h3 { font-family: 'Instrument Serif', serif; font-size: 2rem; margin-bottom: 0.5rem; color: #111; }
.empty-state-box p { color: #666; font-family: 'Inter', sans-serif; }

/* Stacked Layout */
.metrics-stack { display: flex; flex-direction: column; gap: 2rem; }

.metric-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0,0,0,0.02);
}

.card-left { padding: 2rem; background: #fafafa; border-right: 1px solid #e5e5e5; }
.domain-badge { font-family: 'Inter', sans-serif; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; color: #1243e3; background: #f4f6fe; padding: 4px 10px; border-radius: 4px; display: inline-block; margin-bottom: 1rem; }
.metric-name { font-family: 'Instrument Serif', serif; font-size: 2rem; margin: 0 0 0.5rem 0; color: #111; line-height: 1.1; }
.metric-desc { font-family: 'Inter', sans-serif; font-size: 0.95rem; color: #666; line-height: 1.5; margin: 0; }

.card-right { padding: 2rem; display: flex; flex-direction: column; gap: 2rem; }

/* Form Fields */
.param-field { display: flex; flex-direction: column; }
.field-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.2rem; }
.field-label { font-family: 'Inter', sans-serif; font-size: 0.9rem; font-weight: 600; color: #111; }
.required-star { color: #e11d48; margin-left: 2px; }
.help-text { color: #999; cursor: help; font-size: 0.9rem; }
.inline-help { font-size: 0.8rem; color: #666; margin: 0 0 0.8rem 0; font-family: 'Inter', sans-serif; line-height: 1.4; }

.modern-input { width: 100%; padding: 0.8rem 1rem; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; font-family: 'Inter', sans-serif; background: #fff; transition: 0.2s; box-sizing: border-box; }
.modern-input:focus { outline: none; border-color: #1243e3; box-shadow: 0 0 0 3px rgba(18,67,227,0.1); }
.select-icon { appearance: none; background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23111%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E"); background-repeat: no-repeat; background-position: right 1rem top 50%; background-size: 0.65rem auto; padding-right: 2.5rem; }

/* Scrollable Options Box */
.options-box { border: 1px solid #d1d5db; border-radius: 8px; max-height: 200px; overflow-y: auto; background: #fff; display: flex; flex-direction: column; }
.option-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background 0.1s; }
.option-row:hover { background: #fafafa; }
.option-row:last-child { border-bottom: none; }
.custom-checkbox, .custom-radio { width: 16px; height: 16px; cursor: pointer; accent-color: #1243e3; }
.option-text { font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #333; }

/* Nav */
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 80px; background: #fff; border-top: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; z-index: 10; }
.nav-right { display: flex; align-items: center; gap: 2rem; }
.hint { font-family: 'Inter', sans-serif; font-size: 0.8rem; color: #999; }
.nav-btn { font-family: 'Inter', sans-serif; font-weight: 600; padding: 0.8rem 1.5rem; border-radius: 4px; cursor: pointer; transition: 0.2s; }
.ghost { background: transparent; color: #666; border: none; }
.primary { background: #111; color: #fff; border: 1px solid #111; }
.primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }

@media (max-width: 900px) {
  .metric-card { grid-template-columns: 1fr; }
  .card-left { border-right: none; border-bottom: 1px solid #e5e5e5; }
}
</style>