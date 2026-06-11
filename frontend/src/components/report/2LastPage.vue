<script setup>
import { computed } from "vue";

const props = defineProps({
  meta: { type: Object, required: true },
  rows: { type: Array, default: () => [] },
  pageNumber: { type: [String, Number], default: "" },
});

function getLikelihoodLabel(score) {
  if (score <= 2) return { text: "Low", color: "#1d4ed8", textColor: "#ffffff" };
  if (score <= 4) return { text: "Low-Medium", color: "#38bdf8", textColor: "#000000" };
  if (score <= 6) return { text: "Medium", color: "#facc15", textColor: "#000000" };
  if (score <= 8) return { text: "Medium-High", color: "#f97316", textColor: "#000000" };
  return { text: "High", color: "#ef4444", textColor: "#ffffff" };
}

function getGravityLabel(score) {
  if (score <= 1) return { text: "Low", color: "#1d4ed8", textColor: "#ffffff" };
  if (score <= 2) return { text: "Low-Medium", color: "#38bdf8", textColor: "#000000" };
  if (score <= 3) return { text: "Medium", color: "#facc15", textColor: "#000000" };
  if (score <= 4) return { text: "Medium-High", color: "#f97316", textColor: "#000000" };
  return { text: "High", color: "#ef4444", textColor: "#ffffff" };
}

function getFinalRiskLabel(score) {
  const v = Number(score) || 0;
  if (v <= 7.45) return { text: "Low", color: "#1d4ed8", textColor: "#ffffff" };
  if (v <= 15) return { text: "Low-Medium", color: "#38bdf8", textColor: "#000000" };
  if (v <= 24.5) return { text: "Medium", color: "#facc15", textColor: "#000000" };
  if (v <= 42) return { text: "Medium-High", color: "#f97316", textColor: "#000000" };
  return { text: "High", color: "#ef4444", textColor: "#ffffff" };
}

const groupedTableRows = computed(() => {
  const groups = [];
  
  props.rows.forEach(r => {
    if (r.type !== 'metric') return;
    
    const domain = r.right || 'N/A';
    let group = groups.find(g => g.domain === domain);
    
    if (!group) {
      group = { domain, reversibility: r.reversibility, items: [] };
      groups.push(group);
    }
    
    group.items.push({
      metric: r.label,
      likelihood: r.likelihood || 0,
      gravity: r.gravity || 0,
      finalScore: r.finalScore || 0 
    });
  });
  
  return groups;
});
</script>

<template>
  <div class="report-page-content">
    <header class="page-header">
      <div class="meta-left">
        <span class="brand">FRIA SYSTEM</span>
        <span class="sep">|</span>
        <span class="dataset">{{ meta.dataset_name }}</span>
      </div>
      <div class="meta-right">{{ meta.evaluation_date }}</div>
    </header>

    <div class="page-inner">
      <header class="title-block">
        <h1 class="page-title">Score Summary Overview</h1>
        <p class="page-subtitle">Aggregated evaluation results across all domains.</p>
      </header>
      
      <div class="summary-container">
        <table class="summary-table">
          <thead>
            <tr>
              <th>Domain</th>
              <th>Metric</th>
              <th>Likelihood</th>
              <th>Gravity</th>
              <th>Final Risk</th>
            </tr>
          </thead>
          
          <tbody v-for="(group, groupIndex) in groupedTableRows" :key="groupIndex">
            <tr v-for="(item, itemIndex) in group.items" :key="item.metric">
              
              <td v-if="itemIndex === 0" :rowspan="group.items.length" class="grouped-cell">
                {{ group.domain }}<br>
                <span class="rev-text">Rev: {{ group.reversibility ? 'Yes' : 'No' }}</span>
              </td>
              
              <td class="metric-cell">{{ item.metric }}</td>
              
              <td :style="{ backgroundColor: getLikelihoodLabel(item.likelihood).color, color: getLikelihoodLabel(item.likelihood).textColor }" class="score-cell">
                {{ getLikelihoodLabel(item.likelihood).text }}
              </td>
              
              <td :style="{ backgroundColor: getGravityLabel(item.gravity).color, color: getGravityLabel(item.gravity).textColor }" class="score-cell">
                {{ getGravityLabel(item.gravity).text }}
              </td>

              <td :style="{ backgroundColor: getFinalRiskLabel(item.finalScore).color, color: getFinalRiskLabel(item.finalScore).textColor }" class="score-cell">
                {{ getFinalRiskLabel(item.finalScore).text }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <div class="page-number">{{ pageNumber }}</div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;700&display=swap');

.report-page-content {
  height: 100%;
  padding: 20mm;
  box-sizing: border-box;
  position: relative;
  font-family: 'Inter', sans-serif;
  color: #1a202c;
  background: #fff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
  margin-bottom: 10mm;
  font-size: 9px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
}
.sep { margin: 0 8px; color: #cbd5e1; }
.brand { color: #1e293b; font-weight: 800; }

.title-block {
  text-align: left;
  margin-bottom: 8mm;
}

.page-title {
  font-family: 'Instrument Serif', serif;
  font-size: 36pt;
  line-height: 1;
  margin: 0 0 4px 0;
  font-weight: 400;
  color: #1e293b;
}

.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.summary-container {
  width: 100%;
}

.summary-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 9.5px; 
}

.summary-table th, 
.summary-table td {
  border: 1px solid #94a3b8;
  padding: 6px 4px;
  word-wrap: break-word;
  text-align: center;
  vertical-align: middle;
}

.summary-table th:nth-child(1), .summary-table td:nth-child(1) { width: 18%; }
.summary-table th:nth-child(2), .summary-table td:nth-child(2) { width: 28%; }
.summary-table th:nth-child(3), .summary-table td:nth-child(3) { width: 18%; }
.summary-table th:nth-child(4), .summary-table td:nth-child(4) { width: 18%; }
.summary-table th:nth-child(5), .summary-table td:nth-child(5) { width: 18%; }

.summary-table th {
  background: #f1f5f9;
  font-weight: 700;
  color: #1e293b;
  text-transform: uppercase;
  font-size: 9px;
}

.grouped-cell {
  background-color: #f8fafc;
  font-weight: 600;
}

.metric-cell {
  background-color: #ffffff;
}

.score-cell {
  font-weight: 600;
  color: #1a202c; 
}

.rev-text { 
  font-size: 8px; 
  font-weight: 600; 
  color: #64748b; 
  display: block; 
  margin-top: 5px; 
  text-transform: uppercase;
}

.page-number {
  position: absolute;
  bottom: 10mm;
  right: 20mm;
  font-size: 10px;
  font-family: monospace;
  color: #94a3b8;
}

@media print { 
  .report-page-content { -webkit-print-color-adjust: exact; print-color-adjust: exact; } 
}
</style>