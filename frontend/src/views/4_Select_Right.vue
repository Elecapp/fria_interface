<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");
const loading = ref(true);
const registry = ref({});
const rights = ref([]); 
const selectedRights = ref({}); 

function titleizeRight(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildRightsFromRegistry(reg) {
  const set = new Set();

  Object.values(reg || {}).forEach((spec) => {
    if (spec?.right) set.add(spec.right); 
  });

  const out = [...set].map((rightId) => ({
    id: rightId,
    label: titleizeRight(rightId),
    description: `Evaluate AI performance and metrics related to ${titleizeRight(rightId).toLowerCase()}.`,
  }));

  const toggles = {};
  out.forEach((r) => (toggles[r.id] = false));
  selectedRights.value = toggles;

  return out;
}

async function fetchRegistry() {
  error.value = "";
  loading.value = true;
  try {
    const res = await fetch("http://127.0.0.1:8000/plugin-registry");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    registry.value = data;
    rights.value = buildRightsFromRegistry(data);
  } catch (e) {
    error.value = `Backend not reachable: ${e?.message || e}`;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchRegistry);

const rights_to_evaluate = computed(() =>
  Object.entries(selectedRights.value)
    .filter(([_, v]) => v)
    .map(([k]) => k)
);

const canGoNext = computed(() => rights_to_evaluate.value.length > 0);

function toggleRight(id) {
  selectedRights.value[id] = !selectedRights.value[id];
}

function goBack() {
  router.back();
}

async function goNext() {
  error.value = "";

  if (rights_to_evaluate.value.length === 0) {
    error.value = "Select at least one fundamental right to continue.";
    return;
  }

  const cfg = {
    rights_to_evaluate: rights_to_evaluate.value,
    auto_simplify: false,
  };

  try {
    const res = await fetch("http://127.0.0.1:8000/rights/configs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });

    if (!res.ok) throw new Error(`Failed to save config (HTTP ${res.status}).`);

    const data = await res.json();
    localStorage.setItem("config_id", data.config_id);

    function normalizeRightId(s) {
      return (s || "").trim().toLowerCase().replace(/\s+/g, "_");
    }

    const normalizedRights = rights_to_evaluate.value.map(normalizeRightId);

    if (
      normalizedRights.includes("fairness") || 
      normalizedRights.includes("non_discrimination")
    ) {
      router.push("/isf");
    } else {
      router.push("/em");
    }
  } catch (e) {
    error.value = `Error communicating with backend: ${e?.message || e}`;
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
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Select Fundamental Rights</h1>
        
        <p class="description">
          AI systems can impact different types of fundamental rights. Select the domains that are relevant to your specific context of use.
        </p>

        <div class="main-grid">
          <aside class="guidance-panel">
            <div class="guidance-card">
              <div class="icon-wrap">i</div>
              <h3>Not sure which one?</h3>
              <p>You can select multiple rights. The evaluator will automatically adapt the next steps based on your input to ensure a comprehensive assessment.</p>
            </div>
          </aside>

          <section class="selection-area">
            <h2 class="section-label">Available Rights to Evaluate</h2>
            
            <div v-if="loading" class="state-msg">Loading available modules...</div>
            <div v-else-if="error" class="error-msg">{{ error }}</div>

            <div v-else class="rights-grid">
              <div 
                v-for="r in rights" 
                :key="r.id"
                class="right-card"
                :class="{ 'is-active': selectedRights[r.id] }"
                @click="toggleRight(r.id)"
              >
                <div class="card-header">
                  <h3 class="right-name">{{ r.label }}</h3>
                  <div class="check-circle">
                    <span v-if="selectedRights[r.id]">✓</span>
                  </div>
                </div>
                <p class="right-desc">{{ r.description }}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <span v-if="!canGoNext" class="hint">Select at least one right</span>
        <button class="nav-btn primary" :disabled="!canGoNext" @click="goNext">
          Next step →
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
  border: 1px solid #1243e3;
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

/* Selection Area */
.section-label {
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #999;
  margin-bottom: 1.5rem;
}

.rights-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.right-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.right-card:hover {
  border-color: #111;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.right-card.is-active {
  background: #f4f6fe;
  border-color: #1243e3;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.right-name {
  font-family: 'Instrument Serif', serif;
  font-size: 2.2rem;
  color: #111;
  margin: 0;
}

.is-active .right-name {
  color: #1243e3;
}

.check-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
  transition: 0.2s;
}

.is-active .check-circle {
  background: #1243e3;
  border-color: #1243e3;
}

.right-desc {
  font-family: 'Inter', sans-serif;
  font-size: 1rem;
  color: #555;
  line-height: 1.5;
  margin: 0;
}

/* Navigation */
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

.error-msg, .state-msg { color: #666; font-family: 'Inter', sans-serif; }
.error-msg { color: #e63946; }

@media (max-width: 900px) {
  .main-grid { grid-template-columns: 1fr; }
  .guidance-panel { display: none; }
}
</style>