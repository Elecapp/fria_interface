<script setup>
import { computed, onMounted, ref, shallowRef} from "vue";
import { useRoute, useRouter} from "vue-router";

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

    <component
      v-else-if="renderer && metricObj"
      :is="renderer"
      :metric-key="metricKey"
      ref="metricViewRef"
      :metric-obj="metricObj"
      :schema-type="metricSchemaFromBackend"
      :run-id="runId"                 
      @go-back-safe="handleChildSafeBack"
    />

    <div v-else class="fullscreen-msg">
      <button class="btn-ghost" @click="handleBack" style="margin-bottom: 2rem;">← Back to Dashboard</button>
      <div class="card">
        <h3>Raw output</h3>
        <p class="muted">(No renderer for schema: <strong>{{ metricSchemaFromBackend }}</strong>)</p>
        <pre class="pre">{{ JSON.stringify(metricObj, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrapper {
  min-height: 100vh;
  background-color: #faf9f8;
  font-family: 'Inter', sans-serif;
}

.fullscreen-msg {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
}

.error-msg { color: #e11d48; }

.spinner {
  width: 40px; height: 40px; margin-bottom: 1rem;
  border: 3px solid #e5e5e5; border-top: 3px solid #1243e3; border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

.card { background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 2rem; max-width: 800px; width: 90%; text-align: left; }
.pre { background: #f8fafc; padding: 1rem; border-radius: 8px; font-size: 0.85rem; overflow-x: auto; font-family: 'JetBrains Mono', monospace; }
.muted { color: #888; font-size: 0.9rem; }
.btn-ghost { background: transparent; border: none; font-weight: 600; cursor: pointer; color: #111; font-family: 'Inter', sans-serif; }
</style>