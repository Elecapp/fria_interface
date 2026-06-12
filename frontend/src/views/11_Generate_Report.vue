<script setup>
import { API_HOST } from "../utils/config";
import { onMounted, ref, computed, nextTick, markRaw } from "vue";
import { useRoute } from "vue-router";

import CoverPage1 from "../components/report/0CoverPage.vue";
import SystemDescriptionPage from "../components/report/SystemDescriptionPage.vue";
import MetricReportPage2 from "../components/report/1MetricReportPage.vue";
import LastPage2 from "../components/report/2LastPage.vue";

//Report pages layout (per metric & sensitive_feature or per metric)
import ScalarMapViewReport from "../components/report/ScalarMapViewReport.vue";
import ConditionalNestedViewReport from "../components/report/ConditionalNestedViewReport.vue";
import GroupMetricMapViewReport from "../components/report/GroupMetricMapViewReport.vue";
import RecordWithTableViewReport from "../components/report/RecordWithTableViewReport.vue";
import CardMapReport from "../components/report/CardMapReport.vue";


const route = useRoute();

const runId = computed(() => String(route.params.runId || ""));

const meta = ref({
  evaluation_date: "Month, Day, Year",
  dataset_name: "Dataset Test",
  evaluator: "Credit Institution Y",
});

const loading = ref(false);
const error = ref("");

const isPrintMode = computed(() => route.query.print === "1");
const pdfTriggered = ref(false);

const resultSchemas = ref({});
const metricPages = ref([]);
const reportJson = ref({});
const summaryPages = ref([]);

function resolveSchema(metricKey, schemaMap) {
  return schemaMap?.[metricKey]?.schema ?? null;
}
/** 
function getReportRenderer(schema) {
  switch (schema) {
    case "card_map": return CardMapReport;
    case "scalar_map": return ScalarMapViewReport;
    case "conditional_nested": return ConditionalNestedViewReport;
    case "group_metric_map": return GroupMetricMapViewReport;
    case "record_with_table": return RecordWithTableViewReport;
    default: return null;
  }
}
*/
// Sostituisci la tua vecchia funzione con questa:

function getReportRenderer(schema) {
  switch (schema) {
    case "card_map":
      return markRaw(CardMapReport);
    case "scalar_map":
      return markRaw(ScalarMapViewReport);
    case "conditional_nested":
      return markRaw(ConditionalNestedViewReport);
    case "group_metric_map":
      return markRaw(GroupMetricMapViewReport);
    case "record_with_table":
      return markRaw(RecordWithTableViewReport);
    default:
      return null;
  }
}

function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildMetricPages(reportJson, schemaMap) {
  const pages = [];

  for (const [metricKey, metricGroup] of Object.entries(reportJson || {})) {
    if (!metricGroup || typeof metricGroup !== "object") continue;

    const schema = resolveSchema(metricKey, schemaMap);
    const reportComponent = getReportRenderer(schema);

    if (!schema || !reportComponent) continue;

    if (schema === "conditional_nested" || schema === "group_metric_map" || schema === "scalar_map") {
      for (const [featureKey, metricEntry] of Object.entries(metricGroup)) {
        if (!metricEntry || typeof metricEntry !== "object") continue;
        pages.push({
          id: `${metricKey}__${featureKey}`,
          metricKey,
          featureKey,
          schema,
          reportComponent,
          data: metricEntry,
        });
      }
    } else if (metricGroup["(global)"] && typeof metricGroup["(global)"] === "object") {
      pages.push({
        id: `${metricKey}`,
        metricKey,
        featureKey: "(global)",
        schema,
        reportComponent,
        data: metricGroup["(global)"],
      });
    } else {
      pages.push({
        id: metricKey,
        metricKey,
        featureKey: null,
        schema,
        reportComponent,
        data: metricGroup,
      });
    }
  }
  return pages;
}

async function generatePdf() {
  if (pdfTriggered.value) return;
  pdfTriggered.value = true;

  try {
    error.value = "";
    const res = await fetch(`${API_HOST}/results/generate_pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId.value }),
    });

    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `final_evaluation_report_${runId.value}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    error.value = e?.message || String(e);
    pdfTriggered.value = false;
  }
}

// LA FUNZIONE CORRETTA E PULITA
function buildGroupedScores(reportJson) {
  const grouped = {};
  let orderCounter = 0;

  // Stampo il JSON appena arriva per assicurarci che sia tutto okay
  console.log("1. Inizio elaborazione reportJson:", reportJson);

  for (const [topKey, topValue] of Object.entries(reportJson || {})) {
    if (!topValue || typeof topValue !== "object") continue;

    // Funzione magica che trova i dati ovunque siano nascosti
    const extractData = (entry, fallbackName) => {
      // Caccia alla Likelihood: controlla tutti i posti possibili
      let l = entry.final_score;
      if (l === undefined && entry.summary_report) l = entry.summary_report["Final Score"];
      if (l === undefined && entry.disparity_summary) l = entry.disparity_summary.final_score;
      if (l === undefined && entry.context_report) l = entry.context_report["Final Score"];
      l = Number(l) || 0;

      // Trova Gravity
      let g = Number(entry.gravity_report ?? entry.gravity ?? 0);

      // Trova Reversibilità
      let isRev = entry.reversibility_report === true;
      let revMulti = isRev ? 1 : 1.5;

      // IL FAMOSO CALCOLO MATEMATICO CHE ORA NON PUÒ FALLIRE
      let calculatedFinalScore = Number((l * g * revMulti).toFixed(2));

      // Nome e Dominio
      let domain = entry.metric_right_report || entry.right_report || "Unknown Domain";
      let metricName = entry.metric_report || entry.metric || fallbackName;

      return {
        label: prettifyLabel(metricName),
        likelihood: l,
        gravity: g,
        finalScore: calculatedFinalScore,
        domain: prettifyLabel(domain),
        reversibility: isRev,
        order: orderCounter++
      };
    };

    // È una metrica principale (es. Anonymity) o raggruppata (es. CSP)?
    if (topValue.metric || topValue.final_score !== undefined) {
       // METRICA SINGOLA
       let data = extractData(topValue, topKey);
       if (!grouped[data.domain]) grouped[data.domain] = [];
       grouped[data.domain].push(data);
       
    } else {
       // METRICA RAGGRUPPATA (es. Gender in Conditional Statistical Parity)
       for (const [subKey, subValue] of Object.entries(topValue)) {
         if (typeof subValue !== "object" || !subValue) continue;
         
         // Se è un nodo valido di metrica...
         if (subValue.metric || subValue.final_score !== undefined || subValue.summary_report) {
            let data = extractData(subValue, topKey);
            
            // Aggiungiamo il prefisso (es: "Gender (Conditional Statistical Parity)")
            data.label = `${prettifyLabel(subKey)} (${data.label})`;

            // Se il dominio generale è specificato sopra, lo usiamo
            if (topValue.metric_right_report) {
               data.domain = prettifyLabel(topValue.metric_right_report);
            }

            if (!grouped[data.domain]) grouped[data.domain] = [];
            grouped[data.domain].push(data);
         }
       }
    }
  }

  // Stampo il risultato finale! Qui dentro DEVI vedere 50.25 per CSP Gender
  console.log("2. Risultato finale raggruppato calcolato:", grouped);

  return Object.entries(grouped).map(([right, metrics]) => ({
    right,
    metrics: metrics.sort((a, b) => a.order - b.order)
  }));
}

function paginateScoreGroups(groups, maxRowsPerPage = 14) {
  const pages = [];
  let currentPage = [];
  let currentRows = 0;

  for (const group of groups) {
    const headerRowCost = 1;
    if (currentRows + headerRowCost > maxRowsPerPage) {
      pages.push(currentPage);
      currentPage = [];
      currentRows = 0;
    }

    currentPage.push({ type: "header", right: group.right });
    currentRows += headerRowCost;

    for (const metric of group.metrics) {
      const metricRowCost = 1;
      if (currentRows + metricRowCost > maxRowsPerPage) {
        pages.push(currentPage);
        currentPage = [];
        currentPage.push({ type: "header", right: group.right, continued: true });
        currentRows = 1;
      }
      currentPage.push({ type: "metric", right: group.right, ...metric });
      currentRows += metricRowCost;
    }
  }

  if (currentPage.length) {
    pages.push(currentPage);
  }

  return pages;
}

onMounted(async () => {
  window.__REPORT_READY__ = false;
  try {
    loading.value = true;
    error.value = "";

    const res = await fetch(`${API_HOST}/results/values_to_display`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    meta.value = {
      evaluation_date: data?.evaluation_date ?? meta.value.evaluation_date,
      dataset_name: data?.dataset_name ?? meta.value.dataset_name,
      evaluator: data?.evaluator ?? meta.value.evaluator,
    };

    const reportRes = await fetch(`${API_HOST}/results/${runId.value}_report`);
    if (!reportRes.ok) throw new Error(await reportRes.text());
    const reportData = await reportRes.json();


    // ricalcolo punteggi jsoon alla fonte
    
    const fixScoresRecursively = (obj) => {
      if (!obj || typeof obj !== 'object') return;

      // Se questo "nodo" è una metrica valutata (ha gravity o total_score)
      if ('total_score_report' in obj || 'gravity_report' in obj || 'user_weight_report' in obj) {
        let l = obj.final_score;
        if (l === undefined && obj.summary_report) l = obj.summary_report["Final Score"];
        if (l === undefined && obj.disparity_summary) l = obj.disparity_summary.final_score;
        if (l === undefined && obj.context_report) l = obj.context_report["Final Score"];
        
        // FIX T-CLOSENESS: se la metrica non ha score (es. ha solo un "message"), forziamo a 0
        l = (l !== undefined && !Number.isNaN(Number(l))) ? Number(l) : 0;

        // Recuperiamo il peso (se l'utente non ha messo nulla, usiamo 1 come base)
        let g = Number(obj.user_weight_report ?? obj.gravity_report ?? obj.user_weight ?? obj.gravity ?? 1);
        let revMulti = obj.reversibility_report === true ? 1 : 1.5;

        // MAGIA VERA: Forziamo il final_score alla radice dell'oggetto! 
        // In questo modo le pagine del PDF (Gauge) lo troveranno a colpo sicuro.
        obj.final_score = l;
        obj.total_score_report = Number((l * g * revMulti).toFixed(2));
      }

      // Continua a cercare in tutte le altre metriche del JSON
      for (const key in obj) {
        fixScoresRecursively(obj[key]);
      }
    };

  
    fixScoresRecursively(reportData);
    // =========================================================================
    // FINE MAGIA
    // =========================================================================

    reportJson.value = reportData;

    const groupedScores = buildGroupedScores(reportData);
    summaryPages.value = paginateScoreGroups(groupedScores, 18);

    const schemaRes = await fetch(`${API_HOST}/results/result_schemas?run_id=${encodeURIComponent(runId.value)}`);
    if (!schemaRes.ok) throw new Error(await schemaRes.text());
    const schemaData = await schemaRes.json();

    resultSchemas.value = schemaData;
    metricPages.value = buildMetricPages(reportData, schemaData);

    await nextTick();

    if (document.fonts?.ready) {
      await document.fonts.ready;
    }

    window.__REPORT_READY__ = true;

    if (!isPrintMode.value) {
      setTimeout(() => { generatePdf(); });
    }

  } catch (e) {
    error.value = e?.message || String(e);
    window.__REPORT_READY__ = false;
  } finally {
    loading.value = false;
  }
});

</script>

<template>
  <div class="reportRoot">
    <div v-if="loading" class="loading">Loading report…</div>
    <div v-else-if="error" class="loading">{{ error }}</div>

    <template v-else>
      <section class="pdfPage">
        <CoverPage1 :meta="meta" page-number="1" />
      </section>

      <section class="pdfPage">
        <SystemDescriptionPage :meta="meta" page-number="2" />
      </section>

      <section class="pdfPage">
        <MetricReportPage2 :meta="meta" page-number="3" />
      </section>

      <section v-for="(page, index) in metricPages" :key="page.id" class="pdfPage">
        <component
          :is="page.reportComponent"
          :node="page.data"
          :meta="meta"
          :metric-key="page.metricKey"
          :feature-key="page.featureKey"
          :page-number="index + 4" 
        />
      </section>

      <section v-for="(rows, summaryIndex) in summaryPages" :key="`summary-page-${summaryIndex}`" class="pdfPage">
        <LastPage2 :meta="meta" :rows="rows" :page-number="metricPages.length + 4 + summaryIndex" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.reportRoot {
  background: #ddd;
  padding: 16px;
}

.pdfPage {
  width: 210mm;
  height: 297mm;
  background: #fff;
  margin: 0 auto 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  overflow: hidden;
  page-break-after: always;
}

@media print {
  .reportRoot { background: transparent; padding: 0; }
  .pdfPage {
    margin: 0;
    box-shadow: none;
    page-break-after: always;
  }
  .loading { display: none; }
}

.loading {
  width: 210mm;
  margin: 0 auto;
  background: #fff;
  padding: 18px;
  border-radius: 12px;
  text-align: center;
}

.page-number {
  position: absolute;
  bottom: 5mm;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 1;
}
</style>