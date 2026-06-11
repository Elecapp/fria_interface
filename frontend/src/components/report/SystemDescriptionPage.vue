<script setup>
import { API_HOST } from "../../utils/config";
defineProps({
  meta: { type: Object, required: true },
  pageNumber: { type: [String, Number], default: "" },
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
        <h1 class="page-title">Application of the system and Description</h1>
        <p class="page-subtitle">Description and analysis of the AI system, including related data flows</p>
      </header>

      <div class="content-sections">
        
        <div class="q-block">
          <h3>What are the main objectives of the AI system?</h3>
          <p>The main objective of the AI system is to assist the credit institution in the decision about granting or not a mortgage to the applicants. The AI system provides a credit score based on data about the applicant.</p>
        </div>

        <div class="q-block">
          <h3>What are the main features of the system?</h3>
          <p>The system uses a supervised machine learning model trained on historical mortgage application data. In particular, it uses a gradient boosting algorithm to identify patterns between applicant characteristics, loan conditions, and previous repayment outcomes. The model produces a probability of default, which is then converted into a credit risk score.</p>
        </div>

        <div class="q-block">
          <h3>In which countries will it be offered?</h3>
          <p>Italy</p>
        </div>

        <div class="q-block">
          <h3>What types of data are processed (personal, non-personal, special categories)?</h3>
          <p>Personal data and non-personal data.</p>
        </div>

        <div class="q-block">
          <h3>Identification of potential rights holders: who are the individuals of groups likely to be affected by the AI system, including vulnerable individuals or groups?</h3>
          <p>People with low income, people with no income, people with debt, young people.</p>
        </div>

        <div class="q-block">
          <h3>Identification of duty bearers: who is involved in the design, development and deployment of the AI system? What is their role?</h3>
          <p>The system is developed within the credit institution X.</p>
        </div>

        <h2 class="section-title">Fundamental rights context</h2>
        
        <div class="q-block">
          <h3>What fundamental rights are potentially affected by the use of the AI system?</h3>
          <p>Non-discrimination and privacy and data protection.</p>
        </div>

        <div class="q-block">
          <h3>What international/regional legal instruments for the protection of human/fundamental rights have been implemented at the operational level?</h3>
          <p>Applicable European and Italian regulations.</p>
        </div>

        <h2 class="section-title">Controls in place & Stakeholder engagement</h2>
        
        <div class="q-block">
          <h3>What policies and procedures are in place to assess the potential impact on fundamental rights, including stakeholder participation?</h3>
          <p>Periodic FRIA, inclusion of vulnerable groups in the FRIA process.</p>
        </div>

        <div class="q-block">
          <h3>Has an impact assessment been conducted, developed and implemented in relation to specific issues (e.g. data protection) or certain features of the system?</h3>
          <p>A DPIA has been conducted.</p>
        </div>

        <div class="q-block">
          <h3>Who are the main groups or communities potentially affected by the AI system, including its development?</h3>
          <p>People with low income.</p>
        </div>

        <div class="q-block">
          <h3>Which stakeholders should be involved in addition to the individuals or groups potentially affected by the AI system?</h3>
          <p>Civil society organizations.</p>
        </div>

        <div class="q-block">
          <h3>Have the AI provider and AI deployer provided training on fundamental rights standards to management and procurement staff dealing with the AI system?</h3>
          <p>Yes.</p>
        </div>

      </div>
    </div>

    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;700&display=swap');

.report-page-content {
  height: 100%;
  padding: 20mm 20mm 15mm;
  box-sizing: border-box;
  position: relative;
  font-family: 'Inter', sans-serif;
  color: #1a202c;
  background: #fff;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
  margin-bottom: 10mm;
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.sep { margin: 0 8px; color: #cbd5e1; }
.brand { color: #1e293b; font-weight: 800; }

/* Titles */
.title-block {
  margin-bottom: 8mm;
}
.page-title {
  font-family: 'Instrument Serif', serif;
  font-size: 24pt;
  line-height: 1.1;
  margin: 0 0 4px 0;
  color: #1e293b;
  font-weight: 400;
}
.page-subtitle {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

/* Content Formatting */
.content-sections {
  display: flex;
  flex-direction: column;
  gap: 4mm;
}

.section-title {
  font-size: 14pt;
  font-weight: 700;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 4px;
  margin-top: 4mm;
  margin-bottom: 2mm;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.q-block h3 {
  font-size: 9pt;
  font-weight: 700;
  color: #334155;
  margin: 0 0 2px 0;
}

.q-block p {
  font-size: 8pt;
  line-height: 1.4;
  color: #475569;
  margin: 0;
}

/* Footer */
.page-number {
  position: absolute;
  bottom: 10mm;
  right: 20mm;
  font-size: 10px;
  font-family: monospace;
  color: #94a3b8;
}
</style>