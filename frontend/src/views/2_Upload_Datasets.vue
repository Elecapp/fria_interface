<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const selectedDataset = ref(null);

// Definiamo i 4 dataset dell'esperimento
const experimentDatasets = [
  {
    id: "mutui_standard",
    name: "Bank Loans AI",
    file: "dataset_mutui_banca_ai.csv",
    description: "Standard dataset for mortgage approvals. Contains financial and demographic data.",
    type: "Financial"
  },
  {
    id: "mutui_bias",
    name: "Bank Loans AI (Biased)",
    file: "dataset_mutui_banca_ai_BIAS.csv",
    description: "Modified version of the mortgage dataset with intentional demographic bias.",
    type: "Financial / Bias Test"
  },
  {
    id: "hiring_standard",
    name: "Hiring AI Synthetic",
    file: "hiring_ai_synthetic_dataset.csv",
    description: "Synthetic dataset for recruitment screening. Evaluates candidate skills and background.",
    type: "HR / Recruitment"
  },
  {
    id: "hiring_bias",
    name: "Hiring AI Synthetic (Biased)",
    file: "hiring_ai_synthetic_dataset_BIAS.csv",
    description: "Recruitment dataset with historical bias patterns for fairness testing.",
    type: "HR / Bias Test"
  }
];

const canGoNext = computed(() => selectedDataset.value !== null);

function selectDataset(ds) {
  selectedDataset.value = ds;
  error.value = "";
}

async function goNext() {
  if (!selectedDataset.value) return;

  loading.value = true;
  error.value = "";

  try {
    // Nota: In un esperimento reale, qui inviamo al backend il nome del file 
    // o simuliamo l'upload. Assumiamo che i file siano già nella cartella 'data' del backend.
    const formData = new FormData();
    // Qui andrebbe la logica per "caricare" il file selezionato. 
    // Se i file sono locali, dovresti comunque averli caricati una volta o usare un endpoint dedicato.
    
    // Per ora simuliamo la conferma al backend
    const res = await fetch("http://127.0.0.1:8000/upload-experiment-dataset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: selectedDataset.value.file })
    });

    if (!res.ok) throw new Error("Failed to initialize dataset.");

    router.push("/bohe"); // Prossimo step: One-Hot Encoding / Post-processing
  } catch (e) {
    // Se l'endpoint dedicato non esiste ancora, usiamo il log per debug
    console.log("Simulazione: dataset selezionato ->", selectedDataset.value.file);
    router.push("/bohe"); 
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push("/su");
}
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project | Experiment Mode</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <ProcessStepper :current-step="1" />
        
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Select Dataset</h1>
        
        <p class="description">
          Choose one of the <strong>four experimental datasets</strong> provided for this study. 
          Each dataset contains different scenarios to test AI fairness and performance.
        </p>

        <div class="datasets-grid">
          <div 
            v-for="ds in experimentDatasets" 
            :key="ds.id"
            class="dataset-card"
            :class="{ 'is-selected': selectedDataset?.id === ds.id }"
            @click="selectDataset(ds)"
          >
            <div class="card-badge">{{ ds.type }}</div>
            <h3 class="dataset-name">{{ ds.name }}</h3>
            <p class="dataset-file"><code>{{ ds.file }}</code></p>
            <p class="dataset-desc">{{ ds.description }}</p>
            
            <div class="selection-indicator">
              <span v-if="selectedDataset?.id === ds.id">Selected ✓</span>
              <span v-else>Click to select</span>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <span v-if="!canGoNext" class="hint">Please select a dataset to proceed</span>
        <button 
          class="nav-btn primary" 
          :disabled="!canGoNext || loading" 
          @click="goNext"
        >
          {{ loading ? 'Loading...' : 'Next step →' }}
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
  max-width: 1200px;
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
  max-width: 800px;
}

/* Grid */
.datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.dataset-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.dataset-card:hover {
  transform: translateY(-5px);
  border-color: #111;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}

.dataset-card.is-selected {
  border-color: #1243e3;
  background: #f4f6fe;
  box-shadow: 0 0 0 2px #1243e3;
}

.card-badge {
  font-family: 'Inter', sans-serif;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  width: fit-content;
  margin-bottom: 1.5rem;
}

.dataset-name {
  font-family: 'Instrument Serif', serif;
  font-size: 2rem;
  color: #111;
  margin: 0 0 0.5rem 0;
}

.dataset-file {
  font-size: 0.8rem;
  color: #888;
  margin-bottom: 1rem;
}

.dataset-desc {
  font-size: 0.95rem;
  color: #666;
  line-height: 1.5;
  margin-bottom: 2rem;
  flex: 1;
}

.selection-indicator {
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  color: #999;
}

.is-selected .selection-indicator {
  color: #1243e3;
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
.primary:not(:disabled):hover { background: #1243e3; border-color: #1243e3; }
.primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }

.error-msg {
  color: #e63946;
  margin-top: 1rem;
  font-size: 0.9rem;
}
</style>