<script setup>
import { ref, onMounted, watch, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const toggleRecombine = ref(false);
const toggleBinning = ref(false);

const prefixes = ref([]);                
const selectedPrefixes = ref([]);        
const error = ref(null);
const normalBinning = ref({}); 
const normalBinningError = ref(null);
const binLabelsText = ref("");
const binsByFeature = ref({});  
const binEdgesError = ref("");
const touchedFeatures = ref(new Set());

const binningFeatures = computed(() => Object.keys(normalBinning.value || {}));
const selectedBinningFeature = ref(""); 
const binEdgesText = ref("");           
let syncing = false;

watch(binningFeatures, (list) => {
  if (!selectedBinningFeature.value && list.length > 0) {
    selectedBinningFeature.value = list[0];
  }
});

const allowedMin = computed(() => {
  const feat = selectedBinningFeature.value;
  const arr = feat ? normalBinning.value?.[feat] : null;
  return Array.isArray(arr) && arr.length ? arr[0] : null;
});

const allowedMax = computed(() => {
  const feat = selectedBinningFeature.value;
  const arr = feat ? normalBinning.value?.[feat] : null;
  return Array.isArray(arr) && arr.length ? arr[arr.length - 1] : null;
});

watch(selectedBinningFeature, (feat) => {
  syncing = true;                 
  try {
    binEdgesError.value = "";
    const edges = (normalBinning.value && feat) ? normalBinning.value[feat] : null;
    const arr = Array.isArray(edges) ? edges : [];
    binEdgesText.value = arr.length ? arr.join(", ") : "";
    binLabelsText.value = arr.length ? edgesToLabels(arr).map(l => `"${l}"`).join(", ") : "";

    if (feat && !binsByFeature.value[feat] && arr.length) {
      binsByFeature.value[feat] = arr;
    }
  } finally {
    syncing = false;
  }
});

watch(normalBinning, (nb) => {
  if (!nb || typeof nb !== "object") return;
  const next = { ...(binsByFeature.value || {}) };
  for (const [feat, edges] of Object.entries(nb)) {
    const isNormalSuggested = Array.isArray(edges) && edges.length > 2;
    if (isNormalSuggested && !touchedFeatures.value.has(feat)) {
      next[feat] = [...edges];
    }
  }
  binsByFeature.value = next;
}, { deep: true, immediate: true });

function validateEdgesWithinRange(edges) {
  binEdgesError.value = "";
  const minV = allowedMin.value;
  const maxV = allowedMax.value;
  if (!Number.isFinite(minV) || !Number.isFinite(maxV)) return true;
  const tooLow = edges.some(e => e < minV);
  const tooHigh = edges.some(e => e > maxV);
  if (tooLow || tooHigh) {
    binEdgesError.value = `Values must be within [${minV} - ${maxV}].`;
    return false;
  }
  return true;
}

watch(binEdgesText, (txt) => {
  if (syncing) return;
  syncing = true;
  try {
    const feat = selectedBinningFeature.value;
    if (!feat) return;
    const edges = parseNumberList(txt).map(n => Math.ceil(n));
    if (!validateEdgesWithinRange(edges)) return;

    binLabelsText.value = edges.length >= 2 ? edgesToLabels(edges).map(l => `"${l}"`).join(", ") : "";
    touchedFeatures.value.add(feat);
    const suggested = normalBinning.value?.[feat];
    const suggestedIsNormal = Array.isArray(suggested) && suggested.length > 2;

    if (suggestedIsNormal) {
      if (edges.length >= 2) binsByFeature.value[feat] = [...edges];
      else delete binsByFeature.value[feat];
    } else {
      if (edges.length > 2) binsByFeature.value[feat] = [...edges];
      else delete binsByFeature.value[feat]; 
    }
  } finally { syncing = false; }
});

watch(binLabelsText, (txt) => {
  if (syncing) return;
  syncing = true;
  try {
    const labels = (txt || "").split(",").map((x) => x.trim()).filter(Boolean);
    const inferredEdges = labelsToEdges(labels);
    const currentEdges = parseNumberList(binEdgesText.value).map((n) => Math.ceil(n));
    const lastCurrent = currentEdges.length ? currentEdges[currentEdges.length - 1] : null;
    const hasPlus = labels.some((l) => /\+\s*"?$/.test(l));
    const finalEdges = hasPlus && Number.isFinite(lastCurrent)
        ? Array.from(new Set([...inferredEdges, lastCurrent])).sort((a, b) => a - b)
        : inferredEdges;

    if (!validateEdgesWithinRange(finalEdges)) return;
    binEdgesText.value = finalEdges.length ? finalEdges.join(", ") : "";
  } finally { syncing = false; }
});

function parseNumberList(text) {
  return (text || "").split(/[\s,]+/).map((t) => t.trim()).filter(Boolean).map((t) => Number(t)).filter((n) => Number.isFinite(n));
}

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

function labelsToEdges(labels) {
  const edges = [];
  for (const raw of labels) {
    const s = (raw || "").trim().replace(/^"+|"+$/g, "");
    if (!s) continue;
    const plusMatch = s.match(/^(\d+)\s*\+$/);
    if (plusMatch) {
      const start = Number(plusMatch[1]);
      if (Number.isFinite(start) && edges.length === 0) edges.push(start);
      continue;
    }
    const rangeMatch = s.match(/^(\d+)\s*-\s*(\d+)$/);
    if (rangeMatch) {
      const a = Number(rangeMatch[1]);
      const b = Number(rangeMatch[2]);
      if (Number.isFinite(a) && Number.isFinite(b)) {
        if (edges.length === 0) edges.push(a);
        edges.push(b);
      }
    }
  }
  return Array.from(new Set(edges)).sort((a, b) => a - b);
}

onMounted(async () => {
  try {
    const res = await fetch("http://127.0.0.1:8000/headers");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    prefixes.value = Array.isArray(data.columns) ? data.columns : [];
  } catch (e) {
    error.value = e?.message ?? String(e);
  }

  try {
    const res2 = await fetch("http://127.0.0.1:8000/n-distrib");
    if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
    const data = await res2.json();
    normalBinning.value = data;
  } catch (e) {
    normalBinningError.value = e?.message ?? String(e);
    normalBinning.value = {};
  }
});

function goBack() { router.back(); }

async function goNext() {
  try {
    await fetch("http://127.0.0.1:8000/config/inverse-encoding-prefixes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_prefixes: selectedPrefixes.value,
        recombine: toggleRecombine.value,
        binning: toggleBinning.value,
      }),
    });

    if (toggleBinning.value) {
      const filteredBins = Object.fromEntries(
        Object.entries(binsByFeature.value || {})
          .filter(([_, edges]) => Array.isArray(edges) && edges.length > 2)
          .map(([feat, edges]) => [feat, [...edges]])
      );
      await fetch("http://127.0.0.1:8000/config/binning", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          use_binning: true,
          bins: filteredBins,
        }),
      });
    }
  } catch (e) {
    console.error("Saving config failed:", e);
  }
  router.push("/cr");
}

watch(toggleRecombine, (enabled) => {
  if (!enabled) selectedPrefixes.value = [];
});
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Post-Processing</h1>
        
        <p class="description">
          Help the evaluator understand how to treat your dataset features so that fairness and privacy metrics are calculated correctly.
        </p>

        <div class="main-grid">
          <aside class="guidance-panel">
            <div class="guidance-card">
              <div class="icon-wrap">i</div>
              <h3>Why do this?</h3>
              <p>Some features may have been preprocessed for model compatibility (like One-Hot Encoding) or need to be grouped (Binning) to be evaluated properly.</p>
            </div>
          </aside>

          <div class="config-panels">
            
            <section class="config-card" :class="{ 'is-active': toggleRecombine }">
              <div class="card-header">
                <div class="header-text">
                  <h2>Recombine Features</h2>
                  <p>Select prefixes to recombine columns that were previously split.</p>
                </div>
                <label class="switch">
                  <input type="checkbox" v-model="toggleRecombine" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="card-body" v-if="toggleRecombine">
                <div class="chips-container">
                  <label v-for="p in prefixes" :key="p" class="feature-chip" :class="{ 'is-selected': selectedPrefixes.includes(p) }">
                    <input type="checkbox" :value="p" v-model="selectedPrefixes" class="hidden-check" />
                    {{ p }}
                  </label>
                  <span v-if="prefixes.length === 0" class="empty-msg">No prefixes detected in the dataset.</span>
                </div>
              </div>
            </section>

            <section class="config-card" :class="{ 'is-active': toggleBinning }">
              <div class="card-header">
                <div class="header-text">
                  <h2>Numerical Binning</h2>
                  <p>Define bins for numerical features. Normally distributed features have auto-suggestions.</p>
                </div>
                <label class="switch">
                  <input type="checkbox" v-model="toggleBinning" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="card-body" v-if="toggleBinning">
                <div class="input-group">
                  <label>Select Feature</label>
                  <select v-model="selectedBinningFeature" :disabled="binningFeatures.length === 0" class="modern-select">
                    <option value="" disabled>{{ binningFeatures.length ? "Choose a feature..." : "No numerical features detected" }}</option>
                    <option v-for="f in binningFeatures" :key="f" :value="f">{{ f }}</option>
                  </select>
                </div>

                <div class="input-row" v-if="selectedBinningFeature">
                  <div class="input-group">
                    <label>Bin Edges</label>
                    <input type="text" v-model="binEdgesText" class="modern-input" placeholder='e.g. 16, 25, 35' />
                    <span v-if="binEdgesError" class="error-text">{{ binEdgesError }}</span>
                    <span v-else-if="allowedMin !== null" class="hint-text">Range: {{ allowedMin }} – {{ allowedMax }}</span>
                  </div>

                  <div class="input-group">
                    <label>Bin Labels</label>
                    <input type="text" v-model="binLabelsText" class="modern-input" placeholder='e.g. "16-25", "26-35"' />
                  </div>
                </div>
              </div>
            </section>

          </div>
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
.page-layout {
  min-height: 100vh;
  background-color: #faf9f8;
  display: flex;
  flex-direction: column;
  padding-bottom: 100px;
}

.top-nav {
  height: 50px;
  background-color: #1a1a1a;
  display: flex;
  align-items: center;
  padding: 0 2rem;
}

.nav-brand {
  color: #fff;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
}

.hero-container {
  flex: 1;
  display: flex;
  justify-content: center;
  padding-top: 5vh;
}

.hero-content {
  max-width: 1100px;
  width: 100%;
  padding: 0 2rem;
}

.back-button {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  margin-bottom: 1.5rem;
  transition: 0.2s;
}

.back-button:hover { color: #111; transform: translateX(-4px); }

.main-title {
  font-family: 'Instrument Serif', serif;
  font-size: 4rem;
  color: #1A365D;
  margin-bottom: 1rem;
}

.description {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #555;
  line-height: 1.6;
  margin-bottom: 3rem;
  max-width: 750px;
}

.main-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 3rem;
  align-items: start;
}

/* Guidance Panel */
.guidance-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  padding: 2rem;
  border-radius: 16px;
}

.icon-wrap {
  width: 32px;
  height: 32px;
  border: 1px solid #1A365D;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: serif;
  font-weight: bold;
  margin-bottom: 1rem;
}

.guidance-card h3 {
  font-family: 'Instrument Serif', serif;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.guidance-card p {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.5;
}

/* Config Panels */
.config-panels {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.config-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  padding: 2rem;
  transition: all 0.3s ease;
}

.config-card.is-active {
  border-color: #1243e3;
  box-shadow: 0 4px 20px rgba(18, 67, 227, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.header-text h2 {
  font-family: 'Instrument Serif', serif;
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: #111;
}

.header-text p {
  font-size: 0.95rem;
  color: #666;
}

.card-body {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #f0f0f0;
}

/* Toggle Switch */
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 28px;
  flex-shrink: 0;
}

.switch input { opacity: 0; width: 0; height: 0; }

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #d1d5db;
  transition: .3s;
  border-radius: 34px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
}

input:checked + .slider { background-color: #1243e3; }
input:checked + .slider:before { transform: translateX(22px); }

/* Chips */
.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
}

.feature-chip {
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  border: 1px solid #e5e5e5;
  background: #f9f9f9;
  font-size: 0.9rem;
  cursor: pointer;
  transition: 0.2s;
  user-select: none;
}

.hidden-check { display: none; }

.feature-chip:hover { border-color: #111; }
.feature-chip.is-selected { background: #1243e3; color: white; border-color: #1243e3; }

.empty-msg { font-size: 0.9rem; color: #999; font-style: italic; }

/* Inputs */
.input-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.input-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modern-select, .modern-input {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 1rem;
  background: #fff;
  transition: border-color 0.2s;
}

.modern-select:focus, .modern-input:focus {
  outline: none;
  border-color: #1243e3;
}

.error-text { color: #e63946; font-size: 0.8rem; display: block; margin-top: 0.4rem; }
.hint-text { color: #888; font-size: 0.8rem; display: block; margin-top: 0.4rem; }

/* Nav */
.bottom-nav {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 80px;
  background: #fff;
  border-top: 1px solid #e5e5e5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  z-index: 10;
}

.nav-btn {
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  padding: 0.8rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: 0.2s;
}

.ghost { background: transparent; color: #666; border: none; }
.primary { background: #111; color: #fff; border: 1px solid #111; }
.primary:hover { background: #1243e3; border-color: #1243e3; }

@media (max-width: 900px) {
  .main-grid { grid-template-columns: 1fr; }
  .input-row { grid-template-columns: 1fr; }
  .guidance-panel { display: none; }
}
</style>