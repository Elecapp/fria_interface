<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();

const loading = ref(true);
const error = ref("");
const allColumnsData = ref([]); // Lista di tutte le colonne per i menu a tendina

// --- STATO TARGET VARIABLES (NUOVO) ---
const targetColumn = ref("");
const predictionColumn = ref("");
const targetError = ref("");

// --- STATO OHE ---
const toggleRecombine = ref(false);
const oheGroups = ref({}); 
const selectedPrefixes = ref([]); 

// --- STATO BINNING ---
const toggleBinning = ref(false);
const binSettings = ref({}); 

// --- HELPERS OHE ---
function detectOHEGroups(columns) {
  const groups = {};
  columns.forEach(col => {
    const parts = col.split('_');
    if (parts.length > 1) {
      const prefix = col.substring(0, col.lastIndexOf('_') + 1);
      if (!groups[prefix]) groups[prefix] = [];
      groups[prefix].push(col);
    }
  });

  const validGroups = {};
  for (const p in groups) {
    if (groups[p].length > 1) validGroups[p] = groups[p];
  }
  return validGroups;
}

function togglePrefix(prefix) {
  if (!toggleRecombine.value) return;
  const idx = selectedPrefixes.value.indexOf(prefix);
  if (idx > -1) selectedPrefixes.value.splice(idx, 1);
  else selectedPrefixes.value.push(prefix);
}

// --- HELPERS BINNING ---
function edgesToLabels(edges) {
  if (!Array.isArray(edges) || edges.length < 2) return [];
  const labels = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const start = i === 0 ? edges[i] : (edges[i] + 1);
    const end = edges[i + 1];
    const last = i === edges.length - 2;
    labels.push(last ? `${start}+` : `${start}-${end}`);
  }
  return labels;
}

function validateFeatureBinning(feat) {
  const data = binSettings.value[feat];
  data.error = "";
  
  if (!data.enabled || !data.edgesText) return true;

  const edges = data.edgesText.split(/[\s,]+/).map(t => Number(t)).filter(n => Number.isFinite(n));
  
  if (edges.length < 3) {
    data.error = "Please provide at least 3 values (min, middle, max) to create bins.";
    return false;
  }

  const tooLow = edges.some(e => e < data.min);
  const tooHigh = edges.some(e => e > data.max);
  
  if (tooLow || tooHigh) {
    data.error = `Values must be within the allowed range [${data.min} - ${data.max}].`;
    return false;
  }

  if (!data.labelsText) {
    data.labelsText = edgesToLabels(edges).map(l => `"${l}"`).join(", ");
  }

  return true;
}

// --- INIZIALIZZAZIONE ---
onMounted(async () => {
  loading.value = true;
  error.value = "";

  try {
    const resHeaders = await fetch("http://127.0.0.1:8000/headers");
    if (!resHeaders.ok) throw new Error("Failed to fetch headers");
    const dataHeaders = await resHeaders.json();
    
    // Salviamo le colonne per i dropdown
    allColumnsData.value = Array.isArray(dataHeaders.columns) ? dataHeaders.columns : [];
    
    oheGroups.value = detectOHEGroups(allColumnsData.value);

    const resDistrib = await fetch("http://127.0.0.1:8000/n-distrib");
    if (resDistrib.ok) {
      const dataDistrib = await resDistrib.json();
      const settings = {};
      for (const [feat, edges] of Object.entries(dataDistrib)) {
        if (Array.isArray(edges) && edges.length > 0) {
          const isNormal = edges.length > 2; 
          settings[feat] = {
            enabled: isNormal, 
            edgesText: isNormal ? edges.join(", ") : "",
            labelsText: isNormal ? edgesToLabels(edges).map(l => `"${l}"`).join(", ") : "",
            min: edges[0],
            max: edges[edges.length - 1],
            error: ""
          };
        }
      }
      binSettings.value = settings;
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
});

function goBack() { router.back(); }

async function goNext() {
  targetError.value = "";
  let hasErrors = false;

  // 1. Validazione Target Columns (Obbligatori)
  if (!targetColumn.value || !predictionColumn.value) {
    targetError.value = "Please select both the Ground Truth and Model Prediction columns.";
    hasErrors = true;
  }

  // 2. Validazione Binning
  if (toggleBinning.value) {
    for (const feat in binSettings.value) {
      if (binSettings.value[feat].enabled) {
        if (!validateFeatureBinning(feat)) hasErrors = true;
      }
    }
  }
  
  if (hasErrors) {
    // Scrolla in alto se c'è un errore nei target
    if (targetError.value) window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }

  try {
    // 3A. Salva Target Columns nel config generico
    await fetch("http://127.0.0.1:8000/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_column: targetColumn.value,
        prediction_column: predictionColumn.value
      })
    });
    // tagliare i file in base alle colonne target selezionate, per ottimizzare i passaggi successivi
    await fetch("http://127.0.0.1:8000/slice-target-files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_column: targetColumn.value,
        prediction_column: predictionColumn.value
      })
    });

    // 3B. Salva OHE
    await fetch("http://127.0.0.1:8000/config/inverse-encoding-prefixes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_prefixes: toggleRecombine.value ? selectedPrefixes.value : [],
        recombine: toggleRecombine.value,
        binning: toggleBinning.value,
      }),
    });

    // 3C. Salva Binning
    if (toggleBinning.value) {
      const finalBins = {};
      for (const feat in binSettings.value) {
        const d = binSettings.value[feat];
        if (d.enabled && d.edgesText) {
          const edges = d.edgesText.split(/[\s,]+/).map(t => Math.ceil(Number(t))).filter(n => Number.isFinite(n));
          if (edges.length > 2) finalBins[feat] = edges;
        }
      }

      await fetch("http://127.0.0.1:8000/config/binning", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          use_binning: true,
          bins: finalBins,
        }),
      });
    }

    router.push("/cr");
  } catch (e) {
    console.error("Saving config failed:", e);
  }
}
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <ProcessStepper :current-step="2" />
        
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Data Mapping & Processing</h1>
        <p class="description">
          Define the key variables of your dataset and configure optional pre-processing steps like binning and recombination.
        </p>

        <div v-if="loading" class="state-msg">Analyzing dataset properties...</div>
        <div v-else-if="error" class="error-msg">{{ error }}</div>

        <div v-else class="config-stack">
          
          <section class="config-panel is-active essential-panel">
            <div class="panel-header">
              <div class="header-text">
                <h2>1. Map Key Variables</h2>
                <p>Select the columns that represent the historical truth and the AI's prediction. This is required to calculate fairness metrics.</p>
              </div>
              <div class="required-badge">Required</div>
            </div>

            <div class="panel-body">
              <div class="input-row">
                <div class="input-group">
                  <label>Ground Truth (y_true)</label>
                  <select v-model="targetColumn" class="modern-select" :class="{'has-error': targetError && !targetColumn}">
                    <option value="" disabled>Select actual outcome column...</option>
                    <option v-for="col in allColumnsData" :key="col" :value="col">{{ col }}</option>
                  </select>
                  <span class="hint-text">The historical, real-world outcome.</span>
                </div>

                <div class="input-group">
                  <label>Model Prediction (y_pred)</label>
                  <select v-model="predictionColumn" class="modern-select" :class="{'has-error': targetError && !predictionColumn}">
                    <option value="" disabled>Select predicted outcome column...</option>
                    <option v-for="col in allColumnsData" :key="col" :value="col">{{ col }}</option>
                  </select>
                  <span class="hint-text">The outcome predicted by the AI.</span>
                </div>
              </div>
              <div v-if="targetError" class="error-banner">{{ targetError }}</div>
            </div>
          </section>

          <section class="config-panel" :class="{ 'is-active': toggleRecombine }">
            <div class="panel-header">
              <div class="header-text">
                <h2>2. Recombine One-Hot Encoded Features</h2>
                <p>We detected groups of columns that share a prefix. Select which ones should be recombined into a single feature.</p>
              </div>
              <label class="master-switch">
                <input type="checkbox" v-model="toggleRecombine" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="panel-body" v-if="toggleRecombine">
              <div v-if="Object.keys(oheGroups).length === 0" class="empty-state">
                No One-Hot Encoded columns detected in this dataset.
              </div>
              
              <div class="cards-grid">
                <div 
                  v-for="(cols, prefix) in oheGroups" 
                  :key="prefix" 
                  class="feature-card"
                  :class="{ 'is-selected': selectedPrefixes.includes(prefix) }"
                  @click="togglePrefix(prefix)"
                >
                  <div class="card-top">
                    <div class="check-box">
                      <div class="check-inner" v-if="selectedPrefixes.includes(prefix)"></div>
                    </div>
                    <h3>{{ prefix.replace(/_$/, '') }}</h3>
                  </div>
                  <div class="card-content">
                    <span class="small-label">Combines these columns:</span>
                    <div class="tags-list">
                      <span v-for="col in cols" :key="col" class="mini-tag">{{ col }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="config-panel" :class="{ 'is-active': toggleBinning }">
            <div class="panel-header">
              <div class="header-text">
                <h2>3. Numerical Feature Binning</h2>
                <p>Convert continuous numerical variables into categorical ranges (bins). Normally distributed features have auto-suggestions.</p>
              </div>
              <label class="master-switch">
                <input type="checkbox" v-model="toggleBinning" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="panel-body" v-if="toggleBinning">
              <div v-if="Object.keys(binSettings).length === 0" class="empty-state">
                No numerical features suitable for binning detected.
              </div>

              <div class="cards-stack">
                <div 
                  v-for="(data, feat) in binSettings" 
                  :key="feat"
                  class="bin-card"
                  :class="{ 'is-active': data.enabled }"
                >
                  <div class="bin-header">
                    <h3>{{ feat }}</h3>
                    <label class="mini-switch">
                      <input type="checkbox" v-model="data.enabled" />
                      <span class="slider-round"></span>
                    </label>
                  </div>

                  <div class="bin-body" v-if="data.enabled">
                    <div class="input-row">
                      <div class="input-group">
                        <label>Bin Edges</label>
                        <input type="text" v-model="data.edgesText" class="modern-input" placeholder="e.g. 18, 25, 35, 60" @blur="validateFeatureBinning(feat)" />
                        <span v-if="data.error" class="error-text">{{ data.error }}</span>
                        <span v-else class="hint-text">Allowed range: {{ data.min }} – {{ data.max }}</span>
                      </div>
                      
                      <div class="input-group">
                        <label>Bin Labels (Optional)</label>
                        <input type="text" v-model="data.labelsText" class="modern-input" placeholder='e.g. "18-25", "26-35"' />
                        <span class="hint-text">Leave empty to auto-generate</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

        </div>
      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <button class="nav-btn primary" @click="goNext">Next step →</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* CSS precedente mantenuto */
.page-layout { min-height: 100vh; background-color: #faf9f8; display: flex; flex-direction: column; padding-bottom: 120px; }
.top-nav { height: 50px; background-color: #1a1a1a; display: flex; align-items: center; padding: 0 2rem; }
.nav-brand { color: #fff; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.9rem; }
.hero-container { flex: 1; display: flex; justify-content: center; padding-top: 4vh; }
.hero-content { max-width: 900px; width: 100%; padding: 0 2rem; }
.back-button { background: none; border: none; color: #888; cursor: pointer; margin-bottom: 1.5rem; transition: 0.2s; }
.back-button:hover { color: #111; transform: translateX(-4px); }
.main-title { font-family: 'Instrument Serif', serif; font-size: 3.5rem; color: #1243e3; margin-bottom: 0.5rem; }
.description { font-family: 'Inter', sans-serif; font-size: 1.1rem; color: #555; line-height: 1.6; margin-bottom: 3rem; }

.config-stack { display: flex; flex-direction: column; gap: 2.5rem; }
.config-panel { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; overflow: hidden; transition: all 0.3s ease; }
.config-panel.is-active { border-color: #1243e3; box-shadow: 0 4px 20px rgba(18, 67, 227, 0.08); }

/* Stile speciale per il pannello essenziale (Target) */
.essential-panel { border-color: #111; box-shadow: none; }
.required-badge { font-family: 'Inter', sans-serif; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; background: #111; color: #fff; padding: 4px 10px; border-radius: 4px; }
.error-banner { margin-top: 1.5rem; background: #fff1f2; color: #e11d48; padding: 1rem; border-radius: 8px; font-size: 0.9rem; border: 1px solid #fecdd3; font-weight: 600; }

.panel-header { padding: 2rem; display: flex; justify-content: space-between; align-items: center; background: #fafafa; border-bottom: 1px solid #e5e5e5; }
.is-active .panel-header { background: #fff; border-bottom-color: #f0f0f0; }
.header-text h2 { font-family: 'Instrument Serif', serif; font-size: 2rem; margin-bottom: 0.4rem; color: #111; }
.header-text p { font-size: 0.95rem; color: #666; margin: 0; max-width: 600px; line-height: 1.4; }
.panel-body { padding: 2rem; }

.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
.feature-card { border: 1px solid #e5e5e5; border-radius: 12px; padding: 1.5rem; cursor: pointer; transition: 0.2s; }
.feature-card:hover { border-color: #111; }
.feature-card.is-selected { background: #f4f6fe; border-color: #1243e3; }
.card-top { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem; }
.card-top h3 { font-family: 'Inter', sans-serif; font-size: 1.2rem; font-weight: 600; margin: 0; }
.check-box { width: 20px; height: 20px; border: 2px solid #d1d5db; border-radius: 4px; display: flex; align-items: center; justify-content: center; background: #fff; }
.is-selected .check-box { background: #1243e3; border-color: #1243e3; }
.check-inner { width: 8px; height: 8px; background: #fff; border-radius: 1px; }
.small-label { font-size: 0.75rem; text-transform: uppercase; color: #888; font-weight: 600; display: block; margin-bottom: 0.5rem; }
.tags-list { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.mini-tag { background: #fff; border: 1px solid #d1d5db; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; color: #444; }
.is-selected .mini-tag { background: #e0e7ff; border-color: #c7d2fe; color: #3730a3; }

.cards-stack { display: flex; flex-direction: column; gap: 1rem; }
.bin-card { border: 1px solid #e5e5e5; border-radius: 12px; overflow: hidden; transition: 0.2s; }
.bin-card.is-active { border-color: #111; }
.bin-header { padding: 1.2rem 1.5rem; display: flex; justify-content: space-between; align-items: center; background: #fafafa; }
.is-active .bin-header { background: #fff; border-bottom: 1px solid #e5e5e5; }
.bin-header h3 { font-family: 'Inter', sans-serif; font-size: 1.1rem; margin: 0; }
.bin-body { padding: 1.5rem; background: #fff; }

.input-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.input-group label { display: block; font-size: 0.85rem; font-weight: 600; color: #555; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px; }
.modern-input, .modern-select { width: 100%; padding: 0.8rem 1rem; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; font-family: 'Inter', sans-serif; background: #fff; transition: 0.2s; box-sizing: border-box; }
.modern-input:focus, .modern-select:focus { outline: none; border-color: #1243e3; box-shadow: 0 0 0 3px rgba(18,67,227,0.1); }
.modern-select.has-error { border-color: #e11d48; }

/* Custom arrow for select */
.modern-select { appearance: none; background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23111%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E"); background-repeat: no-repeat; background-position: right 1rem top 50%; background-size: 0.65rem auto; padding-right: 2.5rem; }

.error-text { color: #e63946; font-size: 0.8rem; display: block; margin-top: 0.4rem; }
.hint-text { color: #888; font-size: 0.8rem; display: block; margin-top: 0.4rem; }
.empty-state { padding: 2rem; text-align: center; color: #888; font-style: italic; }

.master-switch, .mini-switch { position: relative; display: inline-block; flex-shrink: 0; }
.master-switch { width: 52px; height: 30px; }
.mini-switch { width: 44px; height: 24px; }
.master-switch input, .mini-switch input { opacity: 0; width: 0; height: 0; }
.slider, .slider-round { position: absolute; cursor: pointer; inset: 0; background-color: #d1d5db; transition: .3s; border-radius: 34px; }
.master-switch .slider:before { position: absolute; content: ""; height: 22px; width: 22px; left: 4px; bottom: 4px; background-color: white; transition: .3s; border-radius: 50%; }
.mini-switch .slider-round:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
input:checked + .slider, input:checked + .slider-round { background-color: #1243e3; }
.master-switch input:checked + .slider:before { transform: translateX(22px); }
.mini-switch input:checked + .slider-round:before { transform: translateX(20px); }

.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 80px; background: #fff; border-top: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; z-index: 10; }
.nav-btn { font-family: 'Inter', sans-serif; font-weight: 600; padding: 0.8rem 1.5rem; border-radius: 4px; cursor: pointer; transition: 0.2s; }
.ghost { background: transparent; color: #666; border: none; }
.primary { background: #111; color: #fff; border: 1px solid #111; }
.primary:hover { background: #1243e3; border-color: #1243e3; }
</style>