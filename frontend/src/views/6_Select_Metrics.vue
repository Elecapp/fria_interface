<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const error = ref("");
const loading = ref(true);

const cfg = ref({});
const metricsByRight = ref({});        
const metricRequirements = ref({});     
const pluginRegistry = ref({});         
const selected = ref({});               

function titleize(metricId) {
  return (metricId || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const canGoNext = computed(() => {
  return sections.value.some((section) =>
    section.cards.some(
      (card) => card.selectable && selected.value?.[section.rightId]?.[card.id]
    )
  );
});

function reqFor(metricId) {
  return metricRequirements.value?.[metricId] || null;
}

function isComputable(metricId) {
  return !!reqFor(metricId)?.computable;
}

function getMissingInputs(metricId) {
  const r = reqFor(metricId);
  return Array.isArray(r?.missing_inputs) ? r.missing_inputs : [];
}

function getMetricDescription(metricId) {
  const desc = pluginRegistry.value?.[metricId]?.description;
  return desc || "Assess this specific dimension of the AI system performance.";
}

const sections = computed(() => {
  const out = [];
  const mb = metricsByRight.value || {};
  
  for (const rightId of Object.keys(mb)) {
    const metricIds = Array.isArray(mb[rightId]) ? mb[rightId] : [];

    if (!selected.value[rightId]) selected.value[rightId] = {};
    
    const cards = metricIds.map((metricId) => {
      const isAvailable = isComputable(metricId);
      const label = pluginRegistry.value?.[metricId]?.name || titleize(metricId);

      return {
        id: metricId,
        label,
        selectable: isAvailable,
        description: getMetricDescription(metricId),
        missing: getMissingInputs(metricId)
      };
    });

    out.push({
      rightId,
      title: titleize(rightId),
      cards,
    });
  }
  return out;
});

async function buildUI() {
  try {
    loading.value = true;
    error.value = "";
    const res = await fetch("http://localhost:8000/configs/latest");

    if (res.status === 404) {
      error.value = "Configuration not found. Please restart the process.";
      return;
    }
    const data = await res.json();
    cfg.value = data.config || {};
    metricsByRight.value = cfg.value.metrics_by_right || {};
    metricRequirements.value = cfg.value.metric_requirements || {};

    const reg = await fetch("http://127.0.0.1:8000/plugin-registry");
    if (reg.ok) pluginRegistry.value = await reg.json();
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

function toggleMetric(rightId, metricId, selectable) {
  if (!selectable) return;
  selected.value[rightId][metricId] = !selected.value[rightId][metricId];
}

function goBack() { router.back(); }

async function goNext() {
  const metricsPayload = {};
  const plugins = [];

  for (const section of sections.value) {
    const rightId = section.rightId;
    const chosen = section.cards
      .filter((m) => m.selectable && selected.value?.[rightId]?.[m.id])
      .map((m) => m.id);

    metricsPayload[rightId] = chosen;

    for (const metricId of chosen) {
      const pluginPath = pluginRegistry.value?.[metricId]?.plugin_path;
      if (pluginPath) plugins.push(pluginPath);
    }
  }

  try {
    const res = await fetch("http://localhost:8000/configs/metrics_to_compute", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metrics: metricsPayload, plugins }),
    });
    if (!res.ok) throw new Error("Update failed");
    router.push("/rm");
  } catch (e) {
    error.value = e.message;
  }
}

onMounted(buildUI);
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Metric Selection</h1>
        
        <p class="description">
          This <strong>Capability Report</strong> shows which metrics can be calculated based on the data you provided. Select the indicators you wish to include in the final evaluation.
        </p>

        <div v-if="loading" class="state-msg">Analyzing available metrics...</div>
        <div v-else-if="error" class="error-msg">{{ error }}</div>

        <div v-else class="sections-stack">
          <section v-for="section in sections" :key="section.rightId" class="right-section">
            <h2 class="section-title">{{ section.title }}</h2>
            
            <div class="metrics-grid">
              <div 
                v-for="m in section.cards" 
                :key="m.id"
                class="metric-card"
                :class="{ 
                  'is-selected': selected[section.rightId][m.id],
                  'is-disabled': !m.selectable 
                }"
                @click="toggleMetric(section.rightId, m.id, m.selectable)"
              >
                <div class="card-top">
                  <div class="check-box" v-if="m.selectable">
                    <div class="check-inner" v-if="selected[section.rightId][m.id]"></div>
                  </div>
                  <div class="status-badge" v-else>Locked</div>
                  <h3 class="metric-label">{{ m.label }}</h3>
                </div>

                <p class="metric-desc">{{ m.description }}</p>

                <div v-if="!m.selectable" class="requirements-box">
                  <span class="req-label">Missing Data:</span>
                  <div class="req-tags">
                    <span v-for="req in m.missing" :key="req" class="req-tag">
                      {{ req }}
                    </span>
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
        <span v-if="!canGoNext" class="hint">Select at least one metric</span>
        <button class="nav-btn primary" :disabled="!canGoNext" @click="goNext">
          Configure Parameters →
        </button>
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
  color: #1243e3;
  margin-bottom: 1rem;
}

.description {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #555;
  line-height: 1.6;
  margin-bottom: 4rem;
  max-width: 800px;
}

/* Sections */
.right-section {
  margin-bottom: 4rem;
}

.section-title {
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #999;
  margin-bottom: 2rem;
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 0.5rem;
}

/* Grid & Cards */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.metric-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.metric-card:hover:not(.is-disabled) {
  border-color: #111;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.metric-card.is-selected {
  border-color: #1243e3;
  background: #f4f6fe;
}

.metric-card.is-disabled {
  opacity: 0.6;
  background: #f0f0f0;
  cursor: not-allowed;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.check-box {
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.is-selected .check-box {
  background: #1243e3;
  border-color: #1243e3;
}

.check-inner {
  width: 8px;
  height: 8px;
  background: #fff;
  border-radius: 1px;
}

.status-badge {
  font-family: 'Inter', sans-serif;
  font-size: 0.65rem;
  background: #999;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.metric-label {
  font-family: 'Instrument Serif', serif;
  font-size: 1.6rem;
  color: #111;
  margin: 0;
}

.metric-desc {
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  color: #666;
  line-height: 1.5;
  margin-bottom: 1.5rem;
  flex: 1;
}

/* Requirements Box */
.requirements-box {
  background: #fff;
  padding: 0.8rem;
  border-radius: 6px;
  border: 1px dashed #ccc;
}

.req-label {
  font-family: 'Inter', sans-serif;
  font-size: 0.7rem;
  color: #888;
  display: block;
  margin-bottom: 0.4rem;
}

.req-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.req-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  background: #eee;
  padding: 2px 6px;
  border-radius: 3px;
  color: #444;
}

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

.nav-right { display: flex; align-items: center; gap: 2rem; }
.hint { font-size: 0.8rem; color: #999; }

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
.primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }

.error-msg, .state-msg {
  padding: 2rem;
  text-align: center;
  font-family: 'Inter', sans-serif;
  color: #666;
}
</style>