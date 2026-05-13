<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loading = ref(true);
const error = ref("");

const columns = ref([]);               
const sensitiveMap = reactive({});    

function fillSensitiveFeatures() {
  const features = {};
  for (const col of columns.value) {
    if (sensitiveMap[col]) { 
      features[col] = { sensitive: true };
    }
  }
  return features;
}

const canGoNext = computed(() => {
  return columns.value.some((col) => sensitiveMap[col]);
});

async function fetchColumns() {
  try {
    loading.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/headers"); 
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    console.log("Dati ricevuti dal backend:", data); // Questo apparirà nei tuoi log

    // FIX: Se data.columns non esiste, prendiamo le chiavi dell'oggetto (age_cv, education, ecc.)
    if (data.columns) {
      columns.value = data.columns;
    } else {
      // Estraiamo i nomi delle chiavi dal JSON che mi hai postato
      columns.value = Object.keys(data).filter(key => key !== 'config_id'); 
    }

    // Inizializziamo i toggle
    for (const col of columns.value) {
      if (sensitiveMap[col] === undefined) sensitiveMap[col] = false;
    }

  } catch (e) {
    error.value = "Errore nel caricamento colonne: " + e.message;
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function toggleSensitive(col) {
  sensitiveMap[col] = !sensitiveMap[col];
}

function goBack() {
  router.back();
}

async function goNext() {
  try {
    error.value = "";
    const features = fillSensitiveFeatures();
    if (Object.keys(features).length === 0) {
      error.value = "Select at least one sensitive feature to continue.";
      return;
    }
    const res = await fetch("http://127.0.0.1:8000/configs/sensitive_features", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features }),
    });
    if (!res.ok) throw new Error("Failed to update config.");
    router.push("/em"); 
  } catch (e) {
    error.value = `Unexpected error: ${e?.message || e}`;
  }
}

onMounted(fetchColumns);
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Sensitive Features</h1>
        
        <p class="description">
          To assess <strong>fairness</strong>, we need to identify protected attributes (e.g., age, gender, ethnicity) in your dataset. This allows the evaluator to detect biased outcomes across different demographic groups.
        </p>

        <div class="main-grid">
          <!-- Colonna Sinistra: Selezione -->
          <section class="selection-area">
            <h2 class="section-label">Available features</h2>
            
            <div v-if="loading" class="loading-state">Analyzing dataset headers...</div>
            <div v-else-if="error" class="error-msg">{{ error }}</div>
            
            <div v-else class="features-grid">
              <button 
                v-for="col in columns" 
                :key="col"
                class="feature-pill"
                :class="{ 'is-active': sensitiveMap[col] }"
                @click="toggleSensitive(col)"
              >
                <span class="pill-label">{{ col }}</span>
                <span class="pill-status">{{ sensitiveMap[col] ? 'Sensitive' : 'Neutral' }}</span>
              </button>
            </div>
          </section>

          <!-- Colonna Destra: Guida -->
          <aside class="guidance-panel">
            <div class="guidance-card">
              <div class="icon-wrap">i</div>
              <h3>Legal Guidance</h3>
              <p>According to the EU Non-discrimination principles, sensitive characteristics typically include:</p>
              <ul class="legal-list">
                <li>Ethnic or social origin</li>
                <li>Religion or belief</li>
                <li>Gender & Sexual orientation</li>
                <li>Age</li>
                <li>Disability</li>
              </ul>
              <a href="https://commission.europa.eu/aid-development-cooperation-fundamental-rights/your-fundamental-rights-eu/know-your-rights/equality/non-discrimination_en" 
                 target="_blank" class="legal-link">Read EU Commission guidelines ↗</a>
            </div>
          </aside>
        </div>
      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <span v-if="!canGoNext" class="hint">Select at least one feature</span>
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
}

.hero-container {
  flex: 1;
  display: flex;
  justify-content: center;
  padding-top: 5vh;
}

.hero-content {
  max-width: 1000px;
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

/* Layout Grid */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 4rem;
  align-items: start;
}

.section-label {
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #999;
  margin-bottom: 1.5rem;
}

/* Features Selection */
.features-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.feature-pill {
  background: #fff;
  border: 1px solid #e5e5e5;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 160px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.feature-pill:hover {
  border-color: #111;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.feature-pill.is-active {
  background: #1243e3;
  border-color: #1243e3;
  color: white;
}

.pill-label {
  font-family: 'Instrument Serif', serif;
  font-size: 1.5rem;
  margin-bottom: 0.2rem;
}

.pill-status {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  text-transform: uppercase;
  opacity: 0.6;
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
  margin-bottom: 1rem;
}

.legal-list {
  list-style: none;
  padding: 0;
  margin-bottom: 1.5rem;
}

.legal-list li {
  font-size: 0.9rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.legal-link {
  font-size: 0.8rem;
  color: #1243e3;
  text-decoration: underline;
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

@media (max-width: 900px) {
  .main-grid { grid-template-columns: 1fr; }
  .guidance-panel { display: none; }
}
</style>