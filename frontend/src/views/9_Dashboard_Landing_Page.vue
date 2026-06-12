<script setup>
import { API_HOST } from "../utils/config";
import { onMounted, onUnmounted, ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import ProcessStepper from "../components/ProcessStepper.vue";

import {
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildConditionalNestedFeatureSavePayload,
  buildGroupMapFeatureSavePayload,
  buildScalarMapSavePayload,
  buildRecordWithTableSavePayload,
  buildCardMapSavePayload,
  getSessionId
} from "../utils/report_builder_helper";

const router = useRouter();
const route = useRoute();

const loadingMetrics = ref(true);
const metricsError = ref("");

const latestResults = ref(null);
const resultSchemas = ref({});
const existingReport = ref({});

const runId = ref("");
const pdfBusy = ref(false);
const pdfError = ref("");

const expandedGroup = ref("");
const domainReversibility = ref({});

const BASE_GRAVITY = 1;

function toggleGroup(groupName) {
  expandedGroup.value = expandedGroup.value === groupName ? "" : groupName;
}

function prettify(s) {
  return String(s || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

async function saveDomainReversibility(groupName) {
  const isReversible = domainReversibility.value[groupName];
  try {
    const payload = {
      run_id: runId.value,
      domain: groupName,
      session_id: getSessionId(),
      reversibility: isReversible
    };
    await fetch(`${API_HOST}/results/save_domain_config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (error) {
    console.error("Errore salvataggio Reversibility:", error);
  }
}

async function resetRun() {
  if (!confirm("Sei sicuro? Questa azione eliminerà tutti i pesi e i report salvati. Ripartirai da zero.")) return;
  try {
    const res = await fetch(`${API_HOST}/results/purge_run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId.value, session_id: getSessionId() })
    });
    if (res.ok) { window.location.reload(); }
  } catch (e) {
    alert("Errore durante il reset: " + e.message);
  }
}

async function generatePdf() {
  pdfError.value = "";
  pdfBusy.value = true;
  try {
    if (!runId.value) throw new Error("runId is missing");
    await buildReportPayloadWithDefaults();
    router.push({ name: "Report", params: { runId: runId.value } });
  } catch (e) {
    pdfError.value = e?.message || String(e);
  } finally {
    pdfBusy.value = false;
  }
}

const groupedMetrics = computed(() => {
  const out = {};
  const allMetricKeys = Object.keys(resultSchemas.value || {});

  const privacyList = ["anonymity_set_size", "k_anonymity", "l_diversity", "mutual_information_metric", "t_closeness"];
  const fairnessList = ["conditional_statistical_parity", "conditional_use_accuracy_equality", "demographic_parity", "disparate_impact", "equal_opportunity", "equalized_odds_difference", "overall_accuracy_equality", "predictive_parity"];

  for (const metricKey of allMetricKeys) {
    let group = "Other Rights";
    if (privacyList.includes(metricKey)) group = "privacy";
    else if (fairnessList.includes(metricKey)) group = "non_discrimination";

    if (!out[group]) out[group] = [];
    out[group].push({
      key: metricKey,
      label: prettify(metricKey),
    });
  }
  return out;
});

const groupNames = computed(() => Object.keys(groupedMetrics.value).sort());

// ─── Sincronizza domainReversibility dal report salvato ──────────────────────
function syncDomainReversibility() {
  const savedDomainConfigs = existingReport.value?.domain_configs || {};
  groupNames.value.forEach(group => {
    if (savedDomainConfigs[group] !== undefined) {
      domainReversibility.value[group] = savedDomainConfigs[group].reversibility;
    }
    // se non c'è nel report non tocchiamo il valore in memoria
    // (l'utente potrebbe averlo appena cliccato senza ancora salvare)
  });
}

// ─── Ricarica solo existingReport + risincronizza reversibility, senza spinner 
async function refreshExistingReport() {
  if (!runId.value) return;
  try {
    const sid = getSessionId();
    const reportResp = await fetch(
      `${API_HOST}/results/${runId.value}_report?session_id=${sid}&t=${Date.now()}`
    );
    if (reportResp.ok) {
      existingReport.value = await reportResp.json();
      syncDomainReversibility(); // ← aggiorna anche i checkbox
    }
  } catch {
    // silenzioso
  }
}
// ─────────────────────────────────────────────────────────────────────────────

async function fetchData() {
  try {
    loadingMetrics.value = true;
    metricsError.value = "";

    runId.value = route.params.runId || "";

    const sid = getSessionId();

    let fetchUrl = `${API_HOST}/results/values_to_display?run_id=${runId.value}&session_id=${sid}&t=${Date.now()}`;

    const results = await fetch(fetchUrl);
    if (!results.ok) throw new Error(await results.text());
    const valsData = await results.json();

    latestResults.value = valsData?.results?.results ? valsData.results : valsData;

    const schemasResp = await fetch(`${API_HOST}/results/result_schemas?run_id=${encodeURIComponent(runId.value)}`);
    if (!schemasResp.ok) throw new Error(await schemasResp.text());
    resultSchemas.value = await schemasResp.json();

    try {
      const reportResp = await fetch(`${API_HOST}/results/${runId.value}_report?session_id=${sid}`);
      if (reportResp.ok) {
        existingReport.value = await reportResp.json();
      } else {
        existingReport.value = {};
      }
    } catch {
      existingReport.value = {};
    }

    groupNames.value.forEach(group => { domainReversibility.value[group] = false; });
    syncDomainReversibility();

    if (groupNames.value.length > 0) {
      expandedGroup.value = expandedGroup.value || groupNames.value[0];
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

  if (m.user_weight_report !== undefined || m.user_justification_report !== undefined) return true;
  if (m["(global)"] && (m["(global)"].user_weight_report !== undefined || m["(global)"].user_justification_report !== undefined)) return true;

  for (const key in m) {
    if (m[key] && typeof m[key] === "object" && (m[key].user_weight_report !== undefined || m[key].user_justification_report !== undefined)) {
      return true;
    }
  }
  return false;
}

function getReportRoot() { return existingReport.value?.results ?? existingReport.value ?? {}; }

function getSavedGlobalWeight(metric) { const m = getReportRoot()?.[metric]?.["(global)"]; return m?.user_weight_report ?? m?.gravity_report ?? BASE_GRAVITY; }
function getSavedGlobalJustification(metric) { return getReportRoot()?.[metric]?.["(global)"]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }
function getSavedMetricWeight(metric) { const m = getReportRoot()?.[metric]; return m?.user_weight_report ?? m?.gravity_report ?? BASE_GRAVITY; }
function getSavedMetricJustification(metric) { return getReportRoot()?.[metric]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }
function getSavedFeatureWeight(metric, feature) { const m = getReportRoot()?.[metric]?.[feature]; return m?.user_weight_report ?? m?.gravity_report ?? BASE_GRAVITY; }
function getSavedFeatureJustification(metric, feature) { return getReportRoot()?.[metric]?.[feature]?.user_justification_report ?? DEFAULT_WEIGHT_JUSTIFICATION; }

async function buildReportPayloadWithDefaults() {
  const all = latestResults.value?.results ?? latestResults.value ?? {};

  for (const [groupName, metrics] of Object.entries(groupedMetrics.value)) {
    const domainRev = !!domainReversibility.value[groupName];

    for (const metricEntry of metrics) {
      const metric = metricEntry.key;
      const schemaType = resultSchemas.value?.[metric]?.schema ?? null;
      if (!["conditional_nested", "group_metric_map", "scalar_map", "record_with_table", "card_map"].includes(schemaType)) continue;

      const metricObj = all?.[metric];
      if (!metricObj || typeof metricObj !== "object") continue;

      if (schemaType === "card_map") {
        const w = getSavedGlobalWeight(metric);
        const j = getSavedGlobalJustification(metric);
        const payload = buildCardMapSavePayload({ runId: runId.value, group: groupName, metric, schemaType, metricObj, userWeight: w, userJustification: j });
        payload.gravity = w;
        payload.reversibility = domainRev;
        payload.session_id = getSessionId();
        await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        continue;
      }
      if (schemaType === "record_with_table") {
        const w = getSavedMetricWeight(metric);
        const j = getSavedMetricJustification(metric);
        const payload = buildRecordWithTableSavePayload({ runId: runId.value, group: groupName, metric, metricObj, userWeight: w, userJustification: j });
        payload.gravity = w;
        payload.reversibility = domainRev;
        payload.session_id = getSessionId();
        await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        continue;
      }
      if (schemaType === "scalar_map") {
        const rows = Object.entries(metricObj).map(([label, value]) => ({ label, value }));
        if (!rows.length) continue;
        const weightsByLabel = {}; const justificationsByLabel = {};
        for (const row of rows) {
          weightsByLabel[row.label] = getSavedFeatureWeight(metric, row.label);
          justificationsByLabel[row.label] = getSavedFeatureJustification(metric, row.label);
        }
        const payload = buildScalarMapSavePayload({ runId: runId.value, group: groupName, metric, rows, weightsByLabel, justificationsByLabel });
        payload.reversibilityByLabel = {};
        for (const row of rows) { payload.reversibilityByLabel[row.label] = domainRev; }
        payload.session_id = getSessionId();
        await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        continue;
      }

      const featureKeys = Object.keys(metricObj).filter((k) => k !== "(global)" && metricObj[k] && typeof metricObj[k] === "object");
      for (const feature of featureKeys) {
        let payload;
        const w = getSavedFeatureWeight(metric, feature);
        const j = getSavedFeatureJustification(metric, feature);

        if (schemaType === "conditional_nested") {
          payload = buildConditionalNestedFeatureSavePayload({ runId: runId.value, group: groupName, metric, schemaType, feature, metricObj, weight: w, justification: j, formatLabel: prettify, formatValue: (v) => v });
        } else if (schemaType === "group_metric_map") {
          payload = buildGroupMapFeatureSavePayload({ runId: runId.value, metric, schemaType, feature, metricObj, weight: w, justification: j, formatLabel: prettify, formatValue: (v) => v });
        } else { continue; }

        payload.gravity = w;
        payload.reversibility = domainRev;
        payload.session_id = getSessionId();
        await fetch(`${API_HOST}/results/save_weights`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      }
    }
  }
}

function openMetric(group, metricKey) {
  router.push({
    name: "MetricResults",
    params: { group, metric: metricKey },
    query: { runId: runId.value }
  });
}

function goBack() { router.back(); }

// ─── CICLO DI VITA ────────────────────────────────────────────────────────────
// fetchData completo solo al mount iniziale.
// refreshExistingReport (leggero) ogni volta che si torna su questa pagina
// tramite visibilitychange (tab focus) o popstate (tasto back del browser).
onMounted(() => {
  fetchData();
  document.addEventListener("visibilitychange", onVisibilityChange);
  window.addEventListener("popstate", refreshExistingReport);
});

onUnmounted(() => {
  document.removeEventListener("visibilitychange", onVisibilityChange);
  window.removeEventListener("popstate", refreshExistingReport);
});

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    refreshExistingReport();
  }
}
// ─────────────────────────────────────────────────────────────────────────────
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
        <div v-else-if="groupNames.length === 0" class="empty-state">No metrics found.</div>

        <div v-else class="accordion-container">
          <div v-for="group in groupNames" :key="group" class="accordion-section">
            
            <div class="accordion-header" :class="{ 'is-open': expandedGroup === group }">
              <div class="header-left" @click="toggleGroup(group)" style="cursor: pointer; flex: 1;">
                <span class="domain-icon">◈</span>
                <h2>{{ prettify(group) }} Domain</h2>
              </div>
              <div class="header-right">
                <label class="reversibility-toggle">
                  <input type="checkbox" v-model="domainReversibility[group]" @change="saveDomainReversibility(group)"/>
                  <span class="checkbox-box"></span>
                  <span class="checkbox-text">Reversibility ({{ domainReversibility[group] ? 'Yes' : 'No' }})</span>
                </label>
                <span class="chevron" :class="{ 'rotated': expandedGroup === group }" @click="toggleGroup(group)" style="cursor: pointer; padding: 10px;">▼</span>
              </div>
            </div>

            <div v-show="expandedGroup === group" class="accordion-body">
              <div v-if="groupedMetrics[group].length === 0" class="muted">No metrics selected for this domain.</div>
              <div class="metrics-grid">
                <div v-for="m in groupedMetrics[group]" :key="m.key" class="metric-action-card" @click="openMetric(group, m.key)">
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
.main-title { font-family: 'Instrument Serif', serif; font-size: 4rem; color: #1A365D; margin: 0 0 1.5rem 0; text-align: center; }
.workflow-steps { display: flex; justify-content: center; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 4rem; font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #555; }
.step { display: flex; align-items: center; gap: 6px; font-weight: 500; }
.num { width: 20px; height: 20px; background: #e5e7eb; color: #111; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; }
.sep { color: #ccc; }
.state-msg { text-align: center; color: #666; font-family: 'Inter', sans-serif; }
.error-banner { background: #fff1f2; color: #e11d48; padding: 1rem; border-radius: 8px; border: 1px solid #fecdd3; text-align: center; }
.empty-state { text-align: center; padding: 3rem; color: #888; font-style: italic; }
.accordion-container { display: flex; flex-direction: column; gap: 1.5rem; }
.accordion-section { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: 0.3s; }
.accordion-section:hover { border-color: #d1d5db; }

/* Adattato da button a div */
.accordion-header { width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 2rem; background: transparent; border: none; transition: background 0.2s; }
.accordion-header.is-open { background: #f8fafc; border-bottom: 1px solid #e5e5e5; }
.accordion-header:hover:not(.is-open) { background: #fafafa; }

.header-left { display: flex; align-items: center; gap: 1rem; }
.domain-icon { font-size: 1.2rem; color: #1243e3; }
.accordion-header h2 { font-family: 'Instrument Serif', serif; font-size: 2.2rem; color: #111; margin: 0; }
.header-right { display: flex; align-items: center; gap: 2rem; }
.chevron { font-size: 0.8rem; color: #888; transition: transform 0.3s ease; }
.chevron.rotated { transform: rotate(-180deg); color: #111; }
.reversibility-toggle { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.reversibility-toggle input { display: none; }
.checkbox-box { width: 22px; height: 22px; border: 2px solid #cbd5e1; display: inline-block; position: relative; transition: 0.2s; border-radius: 4px; background: #fff; }
.reversibility-toggle input:checked ~ .checkbox-box { background-color: #1A365D; border-color: #1A365D; }
.reversibility-toggle input:checked ~ .checkbox-box:after { content: ""; position: absolute; left: 6px; top: 2px; width: 4px; height: 10px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.checkbox-text { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; }
.accordion-body { padding: 2rem; background: #fff; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1rem; }
.metric-action-card { display: flex; align-items: center; justify-content: space-between; padding: 1.2rem 1.5rem; border: 1px solid #e5e5e5; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; background: #fff; }
.metric-action-card:hover { border-color: #1A365D; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-2px); }
.card-content h3 { font-family: 'Inter', sans-serif; font-size: 1.05rem; font-weight: 600; color: #111; margin: 0 0 0.4rem 0; }
.review-tag { font-family: 'Inter', sans-serif; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #b45309; background: #fef3c7; padding: 3px 8px; border-radius: 4px; }
.review-tag.is-done { color: #065f46; background: #dcfce7; }
.arrow-icon { color: #999; font-size: 1.2rem; transition: 0.2s; }
.metric-action-card:hover .arrow-icon { color: #1A365D; transform: translateX(4px); }
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 80px; background: #fff; border-top: 1px solid #e5e5e5; display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; z-index: 10; box-shadow: 0 -4px 12px rgba(0,0,0,0.02); }
.nav-right { display: flex; align-items: center; gap: 1.5rem; }
.error-text { color: #e11d48; font-size: 0.9rem; font-weight: 500; }
.nav-btn { font-family: 'Inter', sans-serif; font-weight: 600; padding: 0.8rem 1.5rem; border-radius: 4px; cursor: pointer; transition: 0.2s; border: 1px solid transparent; }
.ghost { background: transparent; color: #666; border-color: #e5e5e5; }
.ghost:hover { border-color: #1A365D; color: #1A365D; }
.primary { background: #1A365D; color: #fff; border-color: #1A365D; }
.primary:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; }
.primary:disabled { background: #e5e5e5; color: #a0a0a0; border-color: #e5e5e5; cursor: not-allowed; }
@media (max-width: 600px) {
  .metrics-grid { grid-template-columns: 1fr; }
  .accordion-header { flex-direction: column; align-items: flex-start; gap: 1rem; }
  .header-right { width: 100%; justify-content: space-between; margin-top: 10px; }
  .accordion-header h2 { font-size: 1.8rem; }
}
</style>
// CARD MAP VUE: anonymity_set_size,  k_anonymity, l_diversity, t_closeness, mutual_information_metric
// GroupMetricMapView2.vue: demographic_parity, disparate_impact, equal_opportunity, equalized_odds_difference, predictive_parity, overall_accuracy_equality
// ConditionalNestedView2.vue:conditional_statistical_parity,conditional_use_accuracy_equality