<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

//for first report building
import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildConditionalNestedFeatureSavePayload,
  buildGroupMapFeatureSavePayload,
  buildScalarMapSavePayload,
  buildRecordWithTableSavePayload,
  buildCardMapSavePayload,
} from "../utils/report_builder_helper";

const router = useRouter();

const loadingMetrics = ref(true);
const metricsError = ref("");

const plugins = ref([]);         
const latestResults = ref(null); 

//schemas
const resultSchemas = ref({});

//preserve existingReport generated with weights assigned by user
const existingReport = ref({});

//evaluation run
const runId = ref("");
const pdfBusy = ref(false);
const pdfError = ref("");

// Accordion state
const expandedGroup = ref("");

function toggleGroup(groupName) {
  expandedGroup.value = expandedGroup.value === groupName ? "" : groupName;
}

//Prettify
function prettify(s) {
  return String(s || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//Generate report
async function generatePdf() {
  pdfError.value = "";
  pdfBusy.value = true;

  try {
    if (!runId.value) throw new Error("runId is missing");

    await buildReportPayloadWithDefaults();

    router.push({
      name: "Report",
      params: { runId: runId.value },
    });
  } catch (e) {
    pdfError.value = e?.message || String(e);
  } finally {
    pdfBusy.value = false;
  }
}

//Metrics grouped by right
const groupedMetrics = computed(() => {
  const out = {};
  for (const p of plugins.value || []) {
    const parts = String(p).split(".");
    if (parts.length < 3) continue;

    const group = parts[1];
    const metricKey = parts.at(-1); 

    if (!out[group]) out[group] = [];
    out[group].push({
      key: metricKey,
      label: prettify(metricKey),
    });
  }
  return out;
});

//sorted group names for display
const groupNames = computed(() => Object.keys(groupedMetrics.value).sort());

async function fetchData() {
  try {
    loadingMetrics.value = true;
    metricsError.value = "";

    const resPlugins = await fetch("http://127.0.0.1:8000/results/plugins");
    if (!resPlugins.ok) throw new Error(await resPlugins.text());
    const pluginsData = await resPlugins.json();
    plugins.value = pluginsData.plugins || [];

    const results = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!results.ok) throw new Error(await results.text());
    const valsData = await results.json();

    if (valsData?.results?.results) {
      latestResults.value = valsData.results;
    } else {
      latestResults.value = valsData;
    } 
    
    runId.value = latestResults.value?.run_id || latestResults.value?.results?.run_id || "";
    
    const schemasResp = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(runId.value)}`
    );
    if (!schemasResp.ok) throw new Error(await schemasResp.text());
    resultSchemas.value = await schemasResp.json();

    try {
      const reportResp = await fetch(`http://127.0.0.1:8000/results/${runId.value}_report`);
      if (reportResp.ok) {
        existingReport.value = await reportResp.json();
      } else {
        existingReport.value = {};
      }
    } catch {
      existingReport.value = {};
    }

    // Auto-expand first accordion group
    if (groupNames.value.length > 0) {
      expandedGroup.value = groupNames.value[0];
    }

  } catch (e) {
    metricsError.value = e?.message || String(e);
  } finally {
    loadingMetrics.value = false;
  }
}

function isMetricReviewed(metricKey) {
    const report = getReportRoot();
    const m = report[metricKey];
    if (!m || typeof m !== "object") return false;

    // Se è stato salvato un peso a livello della singola metrica
    if (m.user_weight_report !== undefined) return true;
    // Se è stato salvato un peso nel sottomodulo globale
    if (m["(global)"] && m["(global)"].user_weight_report !== undefined) return true;

    // Se è stato salvato un peso per almeno una delle feature sensibili
    for (const key in m) {
      if (m[key] && typeof m[key] === "object" && m[key].user_weight_report !== undefined) {
        return true;
      }
    }
    
    return false;
}


//Preserve user saved weights and justification
function getReportRoot() { return existingReport.value?.results ?? existingReport.value ?? {}; }
function getSavedGlobalWeight(metric) { return getReportRoot()?.[metric]?.["(global)"]?.user_weight_report ?? DEFAULT_WEIGHT; }
function getSavedGlobalJustification(metric) { return getReportRoot()?.[metric]?.["(global)"]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }
function getSavedMetricWeight(metric) { return getReportRoot()?.[metric]?.user_weight_report ?? DEFAULT_WEIGHT; }
function getSavedMetricJustification(metric) { return getReportRoot()?.[metric]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }
function getSavedFeatureWeight(metric, feature) { return getReportRoot()?.[metric]?.[feature]?.user_weight_report ?? DEFAULT_WEIGHT; }
function getSavedFeatureJustification(metric, feature) { return getReportRoot()?.[metric]?.[feature]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }

async function buildReportPayloadWithDefaults() {
  const all = latestResults.value?.results ?? latestResults.value ?? {};

  for (const [groupName, metrics] of Object.entries(groupedMetrics.value)) {
    for (const metricEntry of metrics) {
      const metric = metricEntry.key;
      const schemaType = resultSchemas.value?.[metric]?.schema ?? null;

      if (!["conditional_nested", "group_metric_map", "scalar_map", "record_with_table", "card_map"].includes(schemaType)) continue;

      const metricObj = all?.[metric];
      if (!metricObj || typeof metricObj !== "object") continue;

      if (schemaType === "card_map") {
        const payload = buildCardMapSavePayload({ runId: runId.value, group: groupName, metric, schemaType, metricObj, userWeight: getSavedGlobalWeight(metric), userJustification: getSavedGlobalJustification(metric) });
        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error(`Failed to save defaults for ${metric}`);
        continue;
      }

      if (schemaType === "record_with_table") {
        const payload = buildRecordWithTableSavePayload({ runId: runId.value, group: groupName, metric, metricObj, userWeight: getSavedMetricWeight(metric), userJustification: getSavedMetricJustification(metric) });
        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error(`Failed to save defaults for ${metric}`);
        continue;
      }

      if (schemaType === "scalar_map") {
        const rows = Object.entries(metricObj).map(([label, value]) => ({ label, value }));
        if (!rows.length) continue;
        const weightsByLabel = {}; const justificationsByLabel = {};
        for (const row of rows) { weightsByLabel[row.label] = getSavedFeatureWeight(metric, row.label); justificationsByLabel[row.label] = getSavedFeatureJustification(metric, row.label); }
        const payload = buildScalarMapSavePayload({ runId: runId.value, group: groupName, metric, rows, weightsByLabel, justificationsByLabel });
        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error(`Failed to save defaults for ${metric}`);
        continue;
      }

      const featureKeys = Object.keys(metricObj).filter((k) => k !== "(global)" && metricObj[k] && typeof metricObj[k] === "object");
      for (const feature of featureKeys) {
        let payload;
        if (schemaType === "conditional_nested") {
          payload = buildConditionalNestedFeatureSavePayload({ runId: runId.value, group: groupName, metric, schemaType, feature, metricObj, weight: getSavedFeatureWeight(metric, feature), justification: getSavedFeatureJustification(metric, feature), formatLabel: prettify, formatValue: (v) => v });
        } else if (schemaType === "group_metric_map") {
          payload = buildGroupMapFeatureSavePayload({ runId: runId.value, metric, schemaType, feature, metricObj, weight: getSavedFeatureWeight(metric, feature), justification: getSavedFeatureJustification(metric, feature), formatLabel: prettify, formatValue: (v) => v });
        } else { continue; }
        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error(`Failed to save defaults for ${metric}/${feature}`);
      }
    }
  }
}

function openMetric(group, metricKey) {
  router.push({ name: "MetricResults", params: { group, metric: metricKey } });
}

function goBack() { router.back(); }

onMounted(fetchData);
</script>

<template>
  <div class="page-layout">
    <header class="top-nav">
      <div class="nav-brand">FRIA Project | Dashboard</div>
    </header>

    <main class="hero-container">
      <div class="hero-content">
        
        <ProcessStepper :current-step="5" />
        
        <h1 class="main-title">Evaluation Results</h1>
        
        <div class="workflow-steps">
          <span class="step"><span class="num">1</span> Review results</span>
          <span class="sep">→</span>
          <span class="step"><span class="num">2</span> Assign weights (1-5)</span>
          <span class="sep">→</span>
          <span class="step"><span class="num">3</span> Generate final PDF</span>
        </div>

        <div v-if="loadingMetrics" class="state-msg">Loading your dashboard...</div>
        <div v-else-if="metricsError" class="error-banner">{{ metricsError }}</div>
        
        <div v-else-if="groupNames.length === 0" class="empty-state">
          No metrics found.
        </div>

        <div v-else class="accordion-container">
          <div v-for="group in groupNames" :key="group" class="accordion-section">
            
            <button 
              class="accordion-header" 
              :class="{ 'is-open': expandedGroup === group }"
              @click="toggleGroup(group)"
            >
              <div class="header-left">
                <span class="domain-icon">◈</span>
                <h2>{{ prettify(group) }} Domain</h2>
              </div>
              <span class="chevron" :class="{ 'rotated': expandedGroup === group }">▼</span>
            </button>

            <div v-show="expandedGroup === group" class="accordion-body">
              <div v-if="groupedMetrics[group].length === 0" class="muted">
                No metrics selected for this domain.
              </div>
              
              <div class="metrics-grid">
                <div 
                  v-for="m in groupedMetrics[group]" 
                  :key="m.key"
                  class="metric-action-card"
                  @click="openMetric(group, m.key)"
                >
                  <div class="card-content">
                    <h3>{{ m.label }}</h3>
                    <span v-if="isMetricReviewed(m.key)" class="review-tag is-done">Reviewed ✓</span>
                    <span v-else class="review-tag">Needs Review</span>
                  </div>
                  <div class="arrow-icon">→</div>
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>
    </main>

    <div class="bottom-nav">
      <button class="nav-btn ghost" @click="goBack">Cancel</button>
      
      <div class="nav-right">
        <span v-if="pdfError" class="error-text">{{ pdfError }}</span>
        <button class="nav-btn primary" :disabled="pdfBusy || !runId" @click="generatePdf">
          {{ pdfBusy ? "Generating PDF..." : "Generate PDF Report" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-layout { min-height: 100vh; background-color: #faf9f8; display: flex; flex-direction: column; padding-bottom: 120px; }
.top-nav { height: 50px; background-color: #1a1a1a; display: flex; align-items: center; padding: 0 2rem; }
.nav-brand { color: #fff; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.9rem; }
.hero-container { flex: 1; display: flex; justify-content: center; padding-top: 5vh; }
.hero-content { max-width: 900px; width: 100%; padding: 0 2rem; }

.main-title { font-family: 'Instrument Serif', serif; font-size: 4rem; color: #1243e3; margin: 0 0 1.5rem 0; text-align: center; }

/* Workflow minimalista */
.workflow-steps { display: flex; justify-content: center; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 4rem; font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #555; }
.step { display: flex; align-items: center; gap: 6px; font-weight: 500; }
.num { width: 20px; height: 20px; background: #e5e7eb; color: #111; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; }
.sep { color: #ccc; }

.state-msg { text-align: center; color: #666; font-family: 'Inter', sans-serif; }
.error-banner { background: #fff1f2; color: #e11d48; padding: 1rem; border-radius: 8px; border: 1px solid #fecdd3; text-align: center; }
.empty-state { text-align: center; padding: 3rem; color: #888; font-style: italic; }

/* Accordion */
.accordion-container { display: flex; flex-direction: column; gap: 1.5rem; }

.accordion-section { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: 0.3s; }
.accordion-section:hover { border-color: #d1d5db; }

.accordion-header { width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 2rem; background: transparent; border: none; cursor: pointer; transition: background 0.2s; }
.accordion-header.is-open { background: #f8fafc; border-bottom: 1px solid #e5e5e5; }
.accordion-header:hover:not(.is-open) { background: #fafafa; }

.header-left { display: flex; align-items: center; gap: 1rem; }
.domain-icon { font-size: 1.2rem; color: #1243e3; }
.accordion-header h2 { font-family: 'Instrument Serif', serif; font-size: 2.2rem; color: #111; margin: 0; }

.chevron { font-size: 0.8rem; color: #888; transition: transform 0.3s ease; }
.chevron.rotated { transform: rotate(-180deg); color: #111; }

.accordion-body { padding: 2rem; background: #fff; }

/* Metrics Grid Inside Accordion */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1rem; }

.metric-action-card { display: flex; align-items: center; justify-content: space-between; padding: 1.2rem 1.5rem; border: 1px solid #e5e5e5; border-radius: 12px; cursor: pointer; transition: all 0.2s ease; background: #fff; }
.metric-action-card:hover { border-color: #111; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-2px); }

.card-content h3 { font-family: 'Inter', sans-serif; font-size: 1.05rem; font-weight: 600; color: #111; margin: 0 0 0.4rem 0; }
.review-tag { font-family: 'Inter', sans-serif; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #b45309; background: #fef3c7; padding: 3px 8px; border-radius: 4px; }
.review-tag.is-done {
  color: #065f46;
  background: #dcfce7; /* Verde chiaro */
}

.arrow-icon { color: #999; font-size: 1.2rem; transition: 0.2s; }
.metric-action-card:hover .arrow-icon { color: #111; transform: translateX(4px); }

/* Bottom Nav */
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 80px; background: #fff; border-top: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; z-index: 10; }
.nav-right { display: flex; align-items: center; gap: 1.5rem; }
.error-text { color: #e11d48; font-size: 0.9rem; font-weight: 500; }
.nav-btn { font-family: 'Inter', sans-serif; font-weight: 600; padding: 0.8rem 1.5rem; border-radius: 4px; cursor: pointer; transition: 0.2s; border: 1px solid transparent; }
.ghost { background: transparent; color: #666; border-color: #e5e5e5; }
.ghost:hover { border-color: #111; color: #111; }
.primary { background: #111; color: #fff; border-color: #111; }
.primary:hover:not(:disabled) { background: #1243e3; border-color: #1243e3; }
.primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }

@media (max-width: 600px) {
  .metrics-grid { grid-template-columns: 1fr; }
  .accordion-header { flex-direction: column; align-items: flex-start; gap: 1rem; }
  .accordion-header h2 { font-size: 1.8rem; }
}
</style>