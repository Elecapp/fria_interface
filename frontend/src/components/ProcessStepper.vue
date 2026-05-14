<script setup>
const props = defineProps({
  currentStep: { type: Number, required: true }
});

const steps = [
  { id: 1, name: "Data" },
  { id: 2, name: "Mapping" },
  { id: 3, name: "Config" },
  { id: 4, name: "Eval" },
  { id: 5, name: "Results" },
  { id: 6, name: "Report" }
];
</script>

<template>
  <nav class="stepper-flat-integrated">
    <div class="stepper-wrapper">
      <div v-for="(step, index) in steps" :key="step.id" class="step-node" :class="{
        'is-complete': currentStep > step.id,
        'is-active': currentStep === step.id,
        'is-pending': currentStep < step.id
      }">
        
        <div class="marker">
          <span v-if="currentStep > step.id">ok</span>
          <span v-else>{{ step.id }}</span>
        </div>

        <div class="label">{{ step.name }}</div>

        <div v-if="index < steps.length - 1" class="connector"></div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');

.stepper-flat-integrated {
  width: 100%;
  padding: 30px 0;
  /* Rimossa background bianca: ora è trasparente e prende quella della pagina */
  background: transparent; 
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.stepper-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 20px;
}

.step-node {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.step-node:last-child {
  flex: none;
}

/* Marcatori Quadrati e Piatti */
.marker {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  border-radius: 0px; /* Rigorosamente Quadrato */
  border: 1.5px solid #e2e8f0;
  background: transparent;
  color: #94a3b8;
  transition: all 0.2s ease;
}

.label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #cbd5e1; /* Leggermente più chiaro per sfondi scuri */
  font-weight: 500;
}

.connector {
  flex: 1;
  height: 1.5px;
  background: #e2e8f0;
  margin: 0 12px;
  border-radius: 0px; /* Flat */
}

/* STATO: COMPLETATO */
.is-complete .marker {
  background: #1e293b; /* Slate scuro professionale */
  border-color: #1e293b;
  color: #fff;
}
.is-complete .label {
  color: #1e293b;
}
.is-complete .connector {
  background: #1e293b;
}

/* STATO: ATTIVO (Usa il tuo Blu #1243e3) */
.is-active .marker {
  background: #1243e3;
  border-color: #1243e3;
  color: #fff;
}
.is-active .label {
  color: #1243e3;
  font-weight: 700;
}

@media (max-width: 768px) {
  .label { display: none; }
  .connector { margin: 0 5px; }
}
</style>