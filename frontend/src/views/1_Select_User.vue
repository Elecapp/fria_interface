<script setup>
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

const router = useRouter();

const userProfiles = [
  {
    id: "expert",
    title: "AI Deployer / Auditor",
    description: "Technical evaluator profile. You will review statistical and deep data metrics to establish the formal mathematical algorithmic impact.",
    available: true
  },
  {
    id: "policymaker",
    title: "Policy Maker",
    description: "High-level regulatory profile. Focused primarily on institutional legal compliance, standard governance framework, and social impact.",
    available: false
  },
  {
    id: "citizen",
    title: "Affected Citizen",
    description: "End-user perspective profile. Evaluates algorithmic impact based on human rights perceptions and direct automated decisions.",
    available: false
  }
];

function selectProfile(profile) {
  if (profile.available) {
    router.push("/ud");
  }
}

function goBack() {
  router.push("/");
}
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project | Profile Selection</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        <ProcessStepper :current-step="0" />
        
        <button class="back-button" @click="goBack">← Back</button>

        <h1 class="main-title">Choose your Evaluator Profile</h1>
        <p class="description">
          For this usability testing session, you are required to audit the system assuming a technical role. 
          Other stakeholder profiles are locked in this experimental build.
        </p>

        <div class="profiles-grid">
          <div 
            v-for="profile in userProfiles" 
            :key="profile.id"
            class="profile-card"
            :class="{ 'is-disabled': !profile.available }"
            @click="selectProfile(profile)"
          >
            <h3>{{ profile.title }}</h3>
            <p>{{ profile.description }}</p>
            
            <div class="status-badge">
              <span v-if="profile.available" class="badge-active">Click to select →</span>
              <span v-else class="badge-locked">Locked for this test</span>
            </div>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<style scoped>
.page-layout { min-height: 100vh; background-color: #faf9f8; display: flex; flex-direction: column; font-family: 'Inter', sans-serif; }
.top-nav { height: 50px; background-color: #1a1a1a; display: flex; align-items: center; padding: 0 2rem; }
.nav-brand { color: #fff; font-weight: 600; font-size: 0.9rem; }

.hero-container { flex: 1; display: flex; justify-content: center; padding-top: 5vh; }
.hero-content { max-width: 1000px; width: 100%; padding: 0 2rem; }

.back-button { background: none; border: none; color: #888; cursor: pointer; margin-bottom: 1.5rem; font-weight: 600; }
.back-button:hover { color: #111; }

.main-title { font-family: 'Instrument Serif', serif; font-size: 4rem; color: #1A365D; margin-bottom: 1rem; }
.description { font-size: 1.1rem; color: #555; max-width: 700px; margin-bottom: 3rem; line-height: 1.6; }

.profiles-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; }

.profile-card { background: #fff; border: 2px solid #e5e5e5; padding: 2.5rem 2rem; border-radius: 12px; cursor: pointer; transition: all 0.2s ease; display: flex; flex-direction: column; }
.profile-card:not(.is-disabled):hover { border-color: #1243e3; transform: translateY(-4px); box-shadow: 0 12px 24px rgba(18, 67, 227, 0.1); }

.is-disabled { opacity: 0.5; cursor: not-allowed; background: #f3f4f6; border-color: #e5e7eb; }
.is-disabled:hover { transform: none; box-shadow: none; }

.profile-card h3 { font-size: 1.4rem; color: #111; margin: 0 0 1rem 0; }
.profile-card p { font-size: 0.95rem; color: #666; margin: 0 0 2rem 0; line-height: 1.5; flex-grow: 1; }

.status-badge { margin-top: auto; border-top: 1px solid #f0f0f0; padding-top: 1rem; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.badge-active { color: #1243e3; }
.badge-locked { color: #9ca3af; }
</style>