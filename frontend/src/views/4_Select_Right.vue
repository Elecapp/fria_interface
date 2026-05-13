<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");
const registry = ref({});
const rights = ref([]); 
const selectedRights = ref({}); 

// Formatta il nome del diritto in modo leggibile
function titleizeRight(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Estrae i diritti dal registro del backend
function buildRightsFromRegistry(reg) {
  const set = new Set();

  Object.values(reg || {}).forEach((spec) => {
    if (spec?.right) set.add(spec.right); 
  });

  const out = [...set].map((rightId) => ({
      id: rightId,
      label: titleizeRight(rightId),
      description: `Evaluate metrics available for the "${titleizeRight(rightId)}"`,
  }));

  const toggles = {};
  out.forEach((r) => (toggles[r.id] = false));
  selectedRights.value = toggles;

  return out;
}

// Carica il registro dal backend all'avvio
async function fetchRegistry() {
  error.value = "";
  try {
    const res = await fetch("http://127.0.0.1:8000/plugin-registry");
    if (!res.ok) {
      error.value = `Failed to load plugin registry (HTTP ${res.status}).`;
      return;
    }
    const data = await res.json();

    registry.value = data;
    rights.value = buildRightsFromRegistry(data);
  } catch (e) {
    error.value = `Backend not reachable / CORS / network error: ${e?.message || e}`;
  }
}

onMounted(fetchRegistry);

// Diritti selezionati pronti per essere inviati
const rights_to_evaluate = computed(() =>
  Object.entries(selectedRights.value)
    .filter(([_, v]) => v)
    .map(([k]) => k)
);

// Controllo per il bottone Next
const canGoNext = computed(() => {
  return rights_to_evaluate.value.length > 0;
});

// Funzione di selezione interattiva per il design
function toggleRight(id) {
  selectedRights.value[id] = !selectedRights.value[id];
}

function goBack() {
  router.back();
}

// Invia al backend e procede
async function goNext() {
  error.value = "";

  if (rights_to_evaluate.value.length === 0) {
    error.value = "At least one evaluation criteria must be selected.";
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

    if (!res.ok) {
      const txt = await res.text();
      error.value = txt || `Failed to save config (HTTP ${res.status}).`;
      return;
    }

    const data = await res.json(); 
    localStorage.setItem("config_id", data.config_id);

    function normalizeRightId(s) {
      return (s || "").trim().toLowerCase().replace(/\s+/g, "_");
    }

    const normalizedRights = rights_to_evaluate.value.map(normalizeRightId);

    // Smistamento intelligente della rotta
    if (
      normalizedRights.includes("fairness") || 
      normalizedRights.includes("non_discrimination")
    ) {
      router.push("/isf");
    } else {
      router.push("/em");
    }
  } catch (e) {
    error.value = `Backend not reachable / CORS / network error: ${e?.message || e}`;
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
        
        <button class="back-button" @click="goBack" aria-label="Go back">
          ← Back
        </button>

        <h1 class="main-title">Evaluation Criteria</h1>
        
        <p class="description">
          AI systems can impact different fundamental rights. Select the principles that are relevant to your specific context of use. You can select more than one.
        </p>

        <!-- Lista di Selezione Diritti -->
        <div class="rights-list">
          
          <div v-if="rights.length === 0 && !error" class="loading-state">
            Loading available criteria from system...
          </div>

          <button 
            v-for="r in rights" 
            :key="r.id" 
            class="right-card"
            :class="{ 'is-selected': selectedRights[r.id] }"
            @click="toggleRight(r.id)"
            type="button"
          >
            <!-- Checkbox Visuale Custom -->
            <div class="custom-checkbox">
              <svg v-if="selectedRights[r.id]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            
            <div class="right-text">
              <h3 class="right-name">{{ r.label }}</h3>
              <p class="right-desc">{{ r.description }}</p>
            </div>
          </button>

        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

      </div>
    </main>

    <!-- Bottom Navigation -->
    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <button class="nav-btn primary" :disabled="!canGoNext" @click="goNext">
        Next step →
      </button>
    </div>
  </div>
</template>

<style scoped>
.page-layout {
  min-height: 100vh;
  background-color: #faf9f8;
  display: flex;
  flex-direction: column;
  padding-bottom: 80px;
}

.top-nav {
  height: 50px;
  background-color: #1a1a1a;
  display: flex;
  align-items: center;
  padding: 0 2rem;
}

.nav-brand {
  color: #ffffff;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  letter-spacing: 0.5px;
}

.hero-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 5vh;
}

.hero-content {
  max-width: 800px;
  width: 100%;
  padding: 0 2rem;
}

.back-button {
  background: none;
  border: none;
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  font-weight: 500;
  color: #888888;
  cursor: pointer;
  padding: 0;
  margin-bottom: 2rem;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s ease;
}

.back-button:hover {
  color: #111111;
  transform: translateX(-4px);
}

.main-title {
  font-family: 'Instrument Serif', serif;
  font-size: 4rem;
  color: #1243e3;
  font-weight: 400;
  margin-bottom: 1rem;
  line-height: 1.1;
}

.description {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #555555;
  line-height: 1.6;
  margin-bottom: 3rem;
  max-width: 700px;
}

/* =========================================
   LISTA DEI DIRITTI (SELEZIONE)
   ========================================= */
.rights-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.loading-state {
  font-family: 'Inter', sans-serif;
  color: #888;
  font-style: italic;
}

.right-card {
  background: #ffffff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
  transition: all 0.2s ease;
}

.right-card:hover {
  border-color: #111111;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

/* Stato Attivo (Selezionato) */
.right-card.is-selected {
  border-color: #1243e3;
  background: #f4f6fe;
}

/* Checkbox Custom */
.custom-checkbox {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  margin-top: 0.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  background: #fff;
}

.right-card.is-selected .custom-checkbox {
  background: #1243e3;
  border-color: #1243e3;
}

.custom-checkbox svg {
  width: 14px;
  height: 14px;
  color: #fff;
}

.right-text {
  flex: 1;
}

.right-name {
  font-family: 'Instrument Serif', serif;
  font-size: 2rem;
  color: #111111;
  margin: 0 0 0.4rem 0;
  font-weight: 400;
}

.right-desc {
  font-family: 'Inter', sans-serif;
  font-size: 1rem;
  color: #666666;
  line-height: 1.5;
  margin: 0;
}

/* =========================================
   BOTTOM NAV
   ========================================= */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: #ffffff;
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
  font-size: 0.95rem;
  padding: 0.8rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ghost {
  background: transparent;
  color: #666666;
  border: 1px solid transparent;
}

.ghost:hover {
  color: #111111;
}

.primary {
  background: #111111;
  color: #ffffff;
  border: 1px solid #111111;
}

.primary:hover:not(:disabled) {
  background: #1243e3;
  border-color: #1243e3;
}

.primary:disabled {
  background: #e5e5e5;
  color: #a0a0a0;
  border-color: #e5e5e5;
  cursor: not-allowed;
}

.error-msg {
  color: #d32f2f;
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  margin-top: 1rem;
}
</style>