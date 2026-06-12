<script setup>
import { API_HOST } from "../utils/config";
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();
const selectedDataset = ref(null);

// I due scenari esatti per l'esperimento controllato (Toy Branch)
const toyScenarios = [

  {
    id: "credit_score_case2_pre", // Deve combaciare ESATTAMENTE col nome del file JSON
    name: "FRIA for AI system X",
    description: "A credit scoring system that has been evaluated and shows significant disparities in approval rates for different demographic groups. It may indicate potential bias or unfairness in the algorithm's decision-making process.",
    type: "Credit Scoring"
  },
  //{
  //  id: "credit_score_case2",
  //  name: "Bank Case 3",
  //  description: " A credit scoring system that needs to be evaluated by domain experts",
  //  type: "Credit Scoring"
  //}
];

const canGoNext = computed(() => selectedDataset.value !== null);

function selectDataset(ds) {
  selectedDataset.value = ds;
}

function goNext() {
  if (!selectedDataset.value) return;

  // IL TRUCCO È QUI: Nessun caricamento API, saltiamo diretti alla vista 8 (Dashboard)
  // passando l'ID (Hiring_good o Hiring_bad) al router.
  router.push({ 
    name: "Dashboard", 
    params: { runId: selectedDataset.value.id } 
  });
}

function goBack() {
  router.push("/"); // Modifica a piacimento se hai una home page diversa
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

        <h1 class="main-title">Select AI System to Evaluate </h1>
        
        <p class="description">
          The evaluator has computed a set of metrics to help assess the potential impact of the AI system on fundamental rights. Before continuing, please review these results carefully and provide your feedback on two aspects: <b>reversibility</b> and <b>gravity</b>.<br><br>
          <b>Reversibility</b>: <br><br>For each fundamental right, indicate if a damage can be repaired or not. In this context, reversibility means how easily an action, decision, or effect caused by the system can be undone, corrected, or transferred away from the current provider or technical setup. A "YES" in reversibility means that the problem can be corrected without major consequences. A "NO" in reversibility means that the problem may create long-term dependency, loss of control, or harm that is difficult to repair.
          <br><br>
          <b>Gravity</b>: <br><br> For each metric, indicate the <b>gravity</b> of the potential risk. In this context, gravity means how serious the impact on a fundamental right could be if the risk occurs. This is especially important in a Fundamental Rights Impact Assessment, where high-risk AI systems must be assessed according to the severity of possible harm. When assigning gravity, consider the <b>scale, nature, and intensity</b> of the impact. A low-gravity risk may cause limited inconvenience or temporary disadvantage. A high-gravity risk may seriously affect the fundamental right of a person. For example, an incorrect recommendation in a low-impact administrative process may have limited gravity. However, an AI error that affects access to healthcare, justice, education, social benefits, or employment may have high gravity because it can significantly affect a person’s rights and life opportunities.
          
        </p>

        <div class="datasets-grid">
          <div 
            v-for="ds in toyScenarios" 
            :key="ds.id"
            class="dataset-card"
            :class="{ 'is-selected': selectedDataset?.id === ds.id }"
            @click="selectDataset(ds)"
          >
            <div class="card-badge">{{ ds.type }}</div>
            <h3 class="dataset-name">{{ ds.name }}</h3>
            <p class="dataset-desc">{{ ds.description }}</p>
            
            <div class="selection-indicator">
              <span v-if="selectedDataset?.id === ds.id">Selected ✓</span>
              <span v-else>Click to select</span>
            </div>
          </div>
        </div>

      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      <div class="nav-right">
        <span v-if="!canGoNext" class="hint">Please select a scenario to proceed</span>
        <button 
          class="nav-btn primary" 
          :disabled="!canGoNext" 
          @click="goNext"
        >
          Load Dashboard →
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
</style>