<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();

const running = ref(false);
const error = ref("");

function goBack() {
  if (!running.value) {
    router.back();
  }
}

async function startEvaluation() {
  try {
    running.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/run-evaluation", {
      method: "POST",
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const data = await res.json();
    
    // Se completato con successo, vai alla pagina dei risultati
    if (data.status === "completed") {
      router.push("/r"); 
    }
  } catch (e) {
    error.value = e?.message || "Failed to start evaluation. Please check the backend connection.";
    running.value = false;
  }
}
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project | Evaluation Phase</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        
        <ProcessStepper :current-step="4" />
        
        <div class="centered-layout">
          <button class="back-button" @click="goBack" :class="{ 'is-hidden': running }">
            ← Back to Settings
          </button>

          <div class="launch-card">
            <div v-if="!running" class="state-ready">
              <div class="icon-circle">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
              </div>
              
              <h1 class="main-title">Ready to Evaluate</h1>
              
              <p class="description">
                Your configuration is complete. The system will now analyze your dataset, calculate the selected metrics, and compile the final capability report.
              </p>

              <button class="launch-btn" @click="startEvaluation">
                Start Analysis
              </button>
              
              <div v-if="error" class="error-banner">{{ error }}</div>
            </div>

            <div v-else class="state-running">
              <div class="spinner-wrap">
                <div class="modern-spinner"></div>
              </div>
              
              <h2 class="running-title">Processing Data...</h2>
              
              <p class="running-desc">
                Please wait while the evaluator calculates metrics across the specified domains. This might take a few moments depending on the dataset size.
              </p>
            </div>
          </div>
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
  max-width: 1000px;
  width: 100%;
  padding: 0 2rem;
}

.centered-layout {
  max-width: 600px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 2rem;
}

.back-button {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  margin-bottom: 2rem;
  transition: 0.3s;
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  align-self: flex-start;
}

.back-button:hover { color: #111; transform: translateX(-4px); }
.back-button.is-hidden { opacity: 0; pointer-events: none; }

/* Launch Card */
.launch-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 24px;
  padding: 4rem 3rem;
  width: 100%;
  box-shadow: 0 20px 40px rgba(0,0,0,0.04);
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* State: Ready */
.state-ready {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.icon-circle {
  width: 64px;
  height: 64px;
  background: #f4f6fe;
  color: #1243e3;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
}

.main-title {
  font-family: 'Instrument Serif', serif;
  font-size: 3.5rem;
  color: #1243e3;
  margin: 0 0 1rem 0;
  line-height: 1.1;
}

.description {
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  color: #666;
  line-height: 1.6;
  margin-bottom: 3rem;
}

.launch-btn {
  background: #111;
  color: #fff;
  border: 1px solid #111;
  padding: 1.2rem 3.5rem;
  border-radius: 4px; /* <--- Questo lo rende squadrato! */
  font-family: 'Inter', sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 10px rgba(0,0,0,0.08); /* Ombra più delicata */
}

.launch-btn:hover {
  background: #1243e3;
  border-color: #1243e3;
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(18, 67, 227, 0.2);
}

.error-banner {
  margin-top: 1.5rem;
  color: #e11d48;
  background: #fff1f2;
  padding: 0.8rem 1rem;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  border: 1px solid #fecdd3;
}

/* State: Running */
.state-running {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 0;
  animation: fadeIn 0.5s ease forwards;
}

.spinner-wrap {
  margin-bottom: 2rem;
}

.modern-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f0f0f0;
  border-top: 4px solid #1243e3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.running-title {
  font-family: 'Instrument Serif', serif;
  font-size: 2.5rem;
  color: #111;
  margin: 0 0 1rem 0;
}

.running-desc {
  font-family: 'Inter', sans-serif;
  font-size: 1.05rem;
  color: #666;
  line-height: 1.5;
  max-width: 400px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 600px) {
  .launch-card { padding: 3rem 2rem; }
  .main-title { font-size: 2.8rem; }
}
</style>