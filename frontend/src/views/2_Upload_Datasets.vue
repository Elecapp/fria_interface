<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

// Stato per tenere traccia del dataset selezionato
const selectedDataset = ref(null);
const errorMsg = ref("");
const configId = ref(null);

// Definiamo i nostri dataset "finti" per l'esperimento
const datasets = [
  {
    id: "healthcare",
    title: "Healthcare Readmission",
    description: "Predicts the likelihood of a patient being readmitted to the hospital within 30 days.",
    rows: "10,000",
    features: "14",
    sensitive: "Age, Race"
  },
  {
    id: "finance",
    title: "Credit Risk Scoring",
    description: "Evaluates loan applications to predict the probability of default.",
    rows: "45,000",
    features: "21",
    sensitive: " Gender, Marital Status"
  },
  {
    id: "hr",
    title: "HR Candidate Screening",
    description: "Automated screening of resumes to predict candidate suitability for technical roles.",
    rows: "8,500",
    features: "11",
    sensitive: "Gender, Age"
  }
];

function selectDataset(id) {
  selectedDataset.value = id;
  errorMsg.value = "";
}

function goBack() {
  router.back();
}

// Si può procedere solo se un dataset è stato selezionato
const canGoNext = computed(() => selectedDataset.value !== null);

async function goNext() {
  if (!canGoNext.value) {
    errorMsg.value = "Please select a dataset to continue.";
    return;
  }

  try {
    // Creiamo la configurazione nel backend come faceva il codice originale
    if (!configId.value) {
      const res = await fetch("http://localhost:8000/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: selectedDataset.value }), 
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data?.detail || `Server error (${res.status})`);
      }
      configId.value = data.config_id;
    }

    // Passiamo allo step successivo
    router.push({ path: "/bohe", query: { config_id: configId.value } });
  } catch (e) {
    errorMsg.value = e?.message ?? String(e);
    console.error("Failed to proceed:", e);
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

        <h1 class="main-title">Select a Dataset</h1>
        
        <p class="description">
          Choose one of the pre-configured datasets to run the evaluation. 
          The required data and AI models are already linked.
        </p>

        <!-- Griglia dei Dataset -->
        <div class="dataset-grid">
          <button 
            v-for="ds in datasets" 
            :key="ds.id"
            class="dataset-card"
            :class="{ 'is-selected': selectedDataset === ds.id }"
            @click="selectDataset(ds.id)"
            type="button"
          >
            <div class="card-header">
              <h3 class="card-title">{{ ds.title }}</h3>
            </div>
            
            <p class="card-desc">{{ ds.description }}</p>
            
            <!-- Qui entra in gioco JetBrains Mono per i dati tecnici -->
            <div class="card-meta">
              <div class="meta-item">
                <span class="meta-label">ROWS</span>
                <span class="meta-value">{{ ds.rows }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">FEATURES</span>
                <span class="meta-value">{{ ds.features }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">SENSITIVE</span>
                <span class="meta-value">{{ ds.sensitive }}</span>
              </div>
            </div>
          </button>
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

      </div>
    </main>

    <!-- Barra di navigazione fissa in basso per i bottoni Back / Next -->
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
  padding-bottom: 80px; /* Spazio per la nav bar in basso */
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
  max-width: 900px; /* Un po' più largo per ospitare le card in orizzontale */
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
   GRIGLIA DATASET (CARD)
   ========================================= */
.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.dataset-card {
  background: #ffffff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.dataset-card:hover {
  border-color: #111111;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  transform: translateY(-2px);
}

/* Stato Attivo (Selezionato) */
.dataset-card.is-selected {
  border-color: #1243e3; /* Il tuo blu */
  background: #f4f6fe; /* Sfondo azzurrino leggerissimo */
  box-shadow: 0 0 0 1px #1243e3; /* Bordo più spesso visivamente */
}

.card-title {
  font-family: 'Instrument Serif', serif;
  font-size: 1.8rem;
  color: #111111;
  margin: 0 0 0.8rem 0;
  font-weight: 400;
}

.card-desc {
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  color: #666666;
  line-height: 1.5;
  margin: 0 0 1.5rem 0;
  flex: 1; /* Spinge i metadati in basso */
}

/* Qui usiamo JetBrains Mono! */
.card-meta {
  background: #faf9f8;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.dataset-card.is-selected .card-meta {
  background: #ffffff; /* Fa risaltare il box interno se la card è azzurrina */
}

.meta-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
}

.meta-item:last-child {
  margin-bottom: 0;
}

.meta-label {
  color: #888888;
  letter-spacing: 0.5px;
}

.meta-value {
  color: #111111;
  font-weight: 600;
}

/* =========================================
   BOTTOM NAV E BOTTONI
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
  background: #1243e3; /* Passa al tuo blu al click */
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