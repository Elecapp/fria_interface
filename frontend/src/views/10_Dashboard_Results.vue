<script setup>
import { computed, onMounted, ref, shallowRef } from "vue";
import { useRoute, useRouter } from "vue-router";

import ConditionalNestedView2 from "../components/metrics/ConditionalNestedView2.vue";
import ScalarMapView from "../components/metrics/ScalarMapView.vue";
import GroupMetricMapView2 from "../components/metrics/GroupMetricMapView2.vue";
import RecordWithTableView from "../components/metrics/RecordWithTableView.vue";
import CardMap from "../components/metrics/CardMap.vue";

const route = useRoute();
const router = useRouter();

const group = computed(() => String(route.params.group || "")); 
const metricKey = computed(() => String(route.params.metric || "")); 

const loading = ref(false);
const error = ref("");

const runId = ref("");   
const allResults = ref({}); 
const allSchemas = ref({}); 

const metricViewRef = shallowRef(null);

async function handleBack() {
  const view = metricViewRef.value;
  if (view && typeof view.goBackSafely === "function") {
    await view.goBackSafely();
    return;
  }
  router.back();
}

function handleChildSafeBack() {
  router.back();
}

const metricObj = computed(() => allResults.value?.[metricKey.value] ?? null);
const metricSchemaFromBackend = computed(() => allSchemas.value?.[metricKey.value]?.schema ?? "unknown");

const likelihoodScore = computed(() => {
  if (!metricObj.value) return "N/A";
  if (metricObj.value.final_score !== undefined) {
    return typeof metricObj.value.final_score === 'number' 
      ? metricObj.value.final_score.toFixed(3) 
      : metricObj.value.final_score;
  }
  return "N/A";
});

const renderer = computed(() => {
  switch (metricSchemaFromBackend.value) {
    case "card_map": return CardMap;
    case "scalar_map": return ScalarMapView;
    case "conditional_nested": return ConditionalNestedView2;
    case "group_metric_map": return GroupMetricMapView2; 
    case "record_with_table": return RecordWithTableView;
    default: return null;
  }
});

onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    runId.value = String(data?.run_id || "");  
    allResults.value = data?.results ?? {};

    if (data?.schemas) {
      allSchemas.value = data.schemas;
    } else {
      const sres = await fetch("http://127.0.0.1:8000/results/result_schemas");
      if (sres.ok) {
        allSchemas.value = await sres.json();
      } else {
        allSchemas.value = {};
      }
    }

    if (!allResults.value?.[metricKey.value]) {
      error.value = `Metric "${metricKey.value}" not found in results.`;
    }
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="wrapper">
    <div v-if="loading" class="fullscreen-msg">
      <div class="spinner"></div>
      <p>Loading metric data...</p>
    </div>
    
    <div v-else-if="error" class="fullscreen-msg error-msg">
      <p>{{ error }}</p>
      <button class="btn-ghost" @click="handleBack">← Go Back</button>
    </div>

    <div v-else-if="metricObj" class="content-container">
      <div class="top-navigation">
        <button class="btn-ghost btn-back" @click="handleBack">← Back to Dashboard</button>
      </div>
      
      <div class="executive-header">
        <h1 class="metric-title">{{ metricKey.replace(/_/g, ' ') }}</h1>
        <div class="badge-likelihood">
          <span class="badge-label">Likelihood</span>
          <span class="badge-value">{{ likelihoodScore }}</span>
        </div>
      </div>

      <component
        v-if="renderer"
        :is="renderer"
        :metric-key="metricKey"
        ref="metricViewRef"
        :metric-obj="metricObj"
        :schema-type="metricSchemaFromBackend"
        :run-id="runId"                 
        @go-back-safe="handleChildSafeBack"
      />

      <div v-else class="fallback-card">
        <h3>Raw output</h3>
        <p class="muted">(No renderer for schema: <strong>{{ metricSchemaFromBackend }}</strong>)</p>
        <pre class="pre">{{ JSON.stringify(metricObj, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700&display=swap');

.wrapper {
  min-height: 100vh;
  background-color: #faf9f8;
  font-family: 'Inter', sans-serif;
  padding: 40px 20px;
}

.content-container {
  max-width: 1300px;
  margin: 0 auto;
}

.top-navigation { margin-bottom: 24px; }
.btn-ghost { background: transparent; border: none; font-weight: 600; cursor: pointer; color: #64748b; font-family: 'Inter', sans-serif; transition: 0.2s; }
.btn-ghost:hover { color: #1e293b; text-decoration: underline; }

/* EXECUTIVE HEADER - STILE MCKINSEY */
.executive-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 40px;
  border-bottom: 2px solid #1243e3;
  padding-bottom: 20px;
}

.metric-title {
  font-family: 'Instrument Serif', serif;
  font-size: 56px;
  font-weight: 600;
  color: #1243e3;
  margin: 0;
  text-transform: capitalize;
  line-height: 1;
}

.badge-likelihood {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  background: #1243e3;
  color: white;
  padding: 15px 30px;
}

.badge-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #cbd5e1;
  margin-bottom: 4px;
}

.badge-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

/* STATI DI CARICAMENTO E FALLBACK */
.fullscreen-msg { height: 80vh; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #666; }
.error-msg { color: #e11d48; }
.spinner { width: 40px; height: 40px; margin-bottom: 1rem; border: 3px solid #e5e5e5; border-top: 3px solid #1243e3; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
.fallback-card { background: #fff; border: 1px solid #e5e5e5; padding: 2rem; margin-top: 20px; }
.pre { background: #f8fafc; padding: 1rem; font-size: 0.85rem; overflow-x: auto; font-family: 'JetBrains Mono', monospace; }
.muted { color: #888; font-size: 0.9rem; }
</style>