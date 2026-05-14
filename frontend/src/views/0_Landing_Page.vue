<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

onMounted(() => console.log("HOME MOUNTED"));

const router = useRouter();
const error = ref("");

async function start() {
  try {
    error.value = "";
    const payload = {};

    const res = await fetch("http://127.0.0.1:8000/first_config", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const data = await res.json();
    localStorage.setItem("config_id", data.config_id);
    router.push("/su");
    
  } catch (e) {
    error.value = e?.message || String(e);
    console.error("Failed to create first config:", e);
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
        <h1 class="main-title">FRIA Support System</h1>

        <!-- Nuova lista in stile "Editorial" -->
        <div class="editorial-list">
          <!-- Step 1 -->
          <div class="step-row">
            <div class="step-number">01</div>
            <div class="step-text">
              <h3 class="step-title">Data Selection</h3>
              <p class="step-desc">Select the dataset for your evaluation.</p>
            </div>
          </div>

          <!-- Step 2 -->
          <div class="step-row">
            <div class="step-number">02</div>
            <div class="step-text">
              <h3 class="step-title">Feature Mapping</h3>
              <p class="step-desc">Map target variables and configure sensitive features.</p>
            </div>
          </div>

          <!-- Step 3 -->
          <div class="step-row">
            <div class="step-number">03</div>
            <div class="step-text">
              <h3 class="step-title">Metric Configuration</h3>
              <p class="step-desc">Choose the fundamental rights domains and select metrics to evaluate.</p>
            </div>
          </div>

          <!-- Step 4 -->
          <div class="step-row">
            <div class="step-number">04</div>
            <div class="step-text">
              <h3 class="step-title">Algorithmic Evaluation</h3>
              <p class="step-desc">Run the automated fairness and privacy analysis.</p>
            </div>
          </div>

          <!-- Step 5 -->
          <div class="step-row">
            <div class="step-number">05</div>
            <div class="step-text">
              <h3 class="step-title">Results Dashboard</h3>
              <p class="step-desc">Review algorithmic results, interact with metrics, and assign human weights.</p>
            </div>
          </div>

          <!-- Step 6 -->
          <div class="step-row">
            <div class="step-number">06</div>
            <div class="step-text">
              <h3 class="step-title">Executive Report</h3>
              <p class="step-desc">Provide your contextual justifications and export the final capability report.</p>
            </div>
          </div>
        </div>

        <div class="action-area">
          <button class="cta-button" @click="start">
            START A NEW EVALUATION
          </button>
          
          <p class="note-text">
            This tool guides you step by step. You don't need<br>
            to write code or understand AI systems.
          </p>
          
          <p v-if="error" class="error-msg">{{ error }}</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Il layout di base rimane lo stesso minimale */
.page-layout {
  min-height: 100vh;
  background-color: #faf9f8; /* Sfondo leggermente caldo come nel tuo screenshot */
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
  padding-top: 6vh; 
  padding-bottom: 4rem;
}

.hero-content {
  max-width: 800px; /* Allargato leggermente per far respirare la lista */
  width: 100%;
  padding: 0 2rem;
}

.main-title {
  font-family: 'Instrument Serif', serif;
  font-size: 6rem;
  color: #1243e3; /* blu navy */
  font-weight: 500;
  margin-bottom: 2rem;
  line-height: 1;
  text-align: center;
}

/* =========================================
   STILI PER LA LISTA EDITORIALE (Screenshot)
   ========================================= */
.editorial-list {
  margin-bottom: 3rem;
  border-bottom: 1px solid #e5e5e5; /* La linea di chiusura dell'ultimo elemento */
}

.step-row {
  display: flex;
  align-items: flex-start;
  padding: 1rem 0;
  border-top: 1px solid #e5e5e5; /* La linea sottile che separa gli elementi */
}

.step-number {
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
  color: #888888; /* Grigio tenue per i numeri */
  width: 80px; /* Mantiene i titoli allineati a destra del numero */
  padding-top: 0.5rem; /* Allinea il numero al titolo */
}

.step-text {
  flex: 1;
}

.step-title {
  font-family: 'Instrument Serif', serif;
  font-size: 2.1rem;
  color: #111111; /* Quasi nero */
  font-weight: 400;
  margin: 0 0 0.3rem 0;
  letter-spacing: 0.3px;
}

.step-desc {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #444444;
  line-height: 1.6;
  margin: 0;
}

/* =========================================
   BOTTONE E FOOTER
   ========================================= */
.action-area {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cta-button {
  background-color: #ffffff;
  color: #111111;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 1rem;
  letter-spacing: 1px;
  padding: 1.2rem 3rem;
  border: 1px solid #111111;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 1rem;
}

.cta-button:hover {
  background-color: #1243e3;
  color: #ffffff;
}

.note-text {
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  color: #777777;
  line-height: 1.5;
  text-align: center;
}

.error-msg {
  margin-top: 1rem;
  color: #d32f2f;
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
}
</style>