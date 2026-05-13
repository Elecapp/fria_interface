<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const role = ref("");

function goBack() {
  router.back();
}

function goToEvaluation(selectedRole) {
  role.value = selectedRole;
  router.push({
    path: "/ud",
    query: { role: selectedRole },
  });
}
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        
        <!-- Pulsante Indietro minimalista -->
        <button class="back-button" @click="goBack" aria-label="Go back">
          ← Back
        </button>

        <!-- Titolo principale della pagina -->
        <h1 class="main-title">Choose the evaluator profile</h1>
        
        <p class="description">
          Select the type of user who will run the evaluation. The system can then
          adapt the flow, guidance, and level of technical detail.
        </p>

        <!-- Lista in stile "Editorial" -->
        <div class="editorial-list">
          
          <button class="step-row" @click="goToEvaluation('expert')" type="button">
            <div class="step-number">01</div>
            <div class="step-text">
              <h3 class="step-title">Expert</h3>
              <p class="step-desc">
                For users familiar with AI systems, model evaluation, and compliance concepts.
              </p>
            </div>
          </button>

          <button class="step-row" @click="goToEvaluation('non_expert')" type="button">
            <div class="step-number">02</div>
            <div class="step-text">
              <h3 class="step-title">Non-expert</h3>
              <p class="step-desc">
                For users who need a guided workflow with simpler explanations and less jargon.
              </p>
            </div>
          </button>

          <button class="step-row" @click="goToEvaluation('technical_auditor')" type="button">
            <div class="step-number">03</div>
            <div class="step-text">
              <h3 class="step-title">Technical auditor</h3>
              <p class="step-desc">
                For auditors who need structured evidence, metrics inspection, and reporting support.
              </p>
            </div>
          </button>

        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page-layout {
  min-height: 100vh;
  background-color: #faf9f8;
  display: flex;
  flex-direction: column;
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
  padding-top: 5vh; /* Leggermente ridotto per far spazio al bottone back */
  padding-bottom: 4rem;
}

.hero-content {
  max-width: 800px;
  width: 100%;
  padding: 0 2rem;
}

/* =========================================
   STILE PULSANTE INDIETRO
   ========================================= */
.back-button {
  background: none;
  border: none;
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  font-weight: 500;
  color: #888888;
  cursor: pointer;
  padding: 0;
  margin-bottom: 2rem; /* Distanza dal titolo principale */
  display: inline-flex;
  align-items: center;
  transition: color 0.2s ease, transform 0.2s ease;
}

.back-button:hover {
  color: #111111; /* Diventa scuro al passaggio del mouse */
  transform: translateX(-4px); /* Si sposta leggermente verso sinistra per indicare l'azione indietro */
}

/* Tipografia Intestazione */
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
  font-size: 1.2rem;
  color: #555555;
  line-height: 1.6;
  margin-bottom: 4rem;
  max-width: 700px;
}

/* Lista Editoriale Interattiva */
.editorial-list {
  border-bottom: 1px solid #e5e5e5;
}

.step-row {
  display: flex;
  align-items: flex-start;
  width: 100%;
  padding: 2.5rem 0;
  background: transparent;
  border: none;
  border-top: 1px solid #e5e5e5;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s ease;
}

.step-number {
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
  color: #888888;
  width: 80px;
  padding-top: 0.5rem;
  transition: color 0.3s ease;
}

.step-text {
  flex: 1;
  transition: transform 0.3s ease;
}

.step-title {
  font-family: 'Instrument Serif', serif;
  font-size: 2.2rem;
  color: #111111;
  font-weight: 400;
  margin: 0 0 0.8rem 0;
  letter-spacing: 0.5px;
  transition: color 0.3s ease;
}

.step-desc {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #444444;
  line-height: 1.6;
  margin: 0;
}

.step-row:hover .step-title,
.step-row:hover .step-number {
  color: #1243e3;
}

.step-row:hover .step-text {
  transform: translateX(10px);
}
</style>