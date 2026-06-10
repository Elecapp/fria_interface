<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

function startExperiment() {
  router.push("/su");
}
</script>

<template>
  <div class="landing-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <span class="badge">Experiment Mode</span>
        <h1 class="main-title">FRIA Support System</h1>
        <p class="subtitle">
          Welcome to the simulated impact assessment for Artificial Intelligence systems. 
          In this guided user testing session, the calculation phase is automated so you can focus entirely on reviewing results.
        </p>

        <div class="steps-container">
          <div class="step-card">
            <div class="step-number">1</div>
            <h3>Select Profile</h3>
            <p>Assume the role of an AI Expert / Auditor to begin the assessment.</p>
          </div>
          <div class="step-card">
            <div class="step-number">2</div>
            <h3>Choose Case Study</h3>
            <p>Select one of the pre-calculated evaluation scenarios to audit.</p>
          </div>
          <div class="step-card">
            <div class="step-number">3</div>
            <h3>Dashboard Review</h3>
            <p>Analyze statistical metrics, assign Gravity weights, and define Reversibility.</p>
          </div>
          <div class="step-card">
            <div class="step-number">4</div>
            <h3>Generate PDF</h3>
            <p>Export the final FRIA report containing all consolidated risk evaluations.</p>
          </div>
        </div>

        <button class="primary-btn" @click="startExperiment">
          Start Simulation →
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.landing-layout { min-height: 100vh; background-color: #faf9f8; display: flex; flex-direction: column; font-family: 'Inter', sans-serif; }
.top-nav { height: 50px; background-color: #1a1a1a; display: flex; align-items: center; padding: 0 2rem; }
.nav-brand { color: #fff; font-weight: 600; font-size: 0.9rem; }

.hero-container { flex: 1; display: flex; justify-content: center; align-items: center; padding: 4rem 2rem; }
.hero-content { max-width: 1000px; width: 100%; text-align: center; }

.badge { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #1243e3; background: #e0e7ff; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-bottom: 1.5rem; }
.main-title { font-family: 'Instrument Serif', serif; font-size: 5rem; color: #111; margin: 0 0 1.5rem 0; line-height: 1.1; }
.subtitle { font-size: 1.2rem; color: #555; max-width: 700px; margin: 0 auto 4rem auto; line-height: 1.6; }

.steps-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 4rem; text-align: left; }
.step-card { background: #fff; border: 1px solid #e5e5e5; padding: 2rem; border-radius: 12px; position: relative; transition: transform 0.2s; }
.step-card:hover { transform: translateY(-5px); border-color: #1243e3; box-shadow: 0 10px 25px rgba(18, 67, 227, 0.08); }
.step-number { width: 32px; height: 32px; background: #1243e3; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-family: 'JetBrains Mono', monospace; margin-bottom: 1rem; }
.step-card h3 { font-size: 1.1rem; color: #111; margin: 0 0 0.5rem 0; }
.step-card p { font-size: 0.9rem; color: #666; margin: 0; line-height: 1.5; }

.primary-btn { font-size: 1.1rem; font-weight: 600; background: #1243e3; color: #fff; border: none; padding: 1rem 2.5rem; border-radius: 8px; cursor: pointer; transition: 0.2s; }
.primary-btn:hover { background: #0f36b3; transform: scale(1.02); }
</style>