<script setup>
import { ref, onMounted } from 'vue';

const participantId = ref('');
const isLoading = ref(false);
const faseCorrente = ref('sus'); 

function generateAnonymousToken() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let token = 'FRIA-';
  for (let i = 0; i < 6; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return token;
}

// ==========================================
// CONFIGURAZIONE ENTRY ID (DA SOSTITUIRE!)
// ==========================================
const FORMS_CONFIG = {
  sus: {
    url: 'https://docs.google.com/forms/d/e/1FAIpQLSfzmLp_D_vfgAoeduBr9-3SnzurrEsyhVRK8Wze80Ic7Qz4yw/formResponse',
    idField: 'entry.1434132402',
    domande: { 
      d1: 'entry.560998900', 
      d2: 'entry.2094587764',
      d3: 'entry.1021982346', 
      d4: 'entry.712438338',
      d5: 'entry.1900216695', 
      d6: 'entry.1181124848',
      d7: 'entry.39761166', 
      d8: 'entry.405894963',
      d9: 'entry.1071410908', 
      d10: 'entry.1885966387'
    }
  },
  nasa: {
    url: 'https://docs.google.com/forms/d/e/1FAIpQLSchBey4dASFhvM1XKtiVdzoiGHyLbD3gB1jf2GS5QjxZR5H2g/formResponse',
    idField: 'entry.614298882',
    domande: { 
      mentale: 'entry.925105692', 
      fisica: 'entry.1515252131',
      temporale: 'entry.481912797',
      prestazione: 'entry.1713071230',
      sforzo: 'entry.1944036744',
      frustrazione: 'entry.129190563'
    }
  },
  seq: {
    url: 'https://docs.google.com/forms/d/e/1FAIpQLSeLEQE0LbbuMITiSNvWIIqH1sIhC5-TM1Nd__a1Jk-ypHX0-Q/formResponse',
    idField: 'entry.166493714',
    domande: { 
      facilita: 'entry.447858561' 
    }
  }
};

// ==========================================
// MODELLI DELLE RISPOSTE (Valori neutri iniziali)
// ==========================================
const risposteSus = ref({ d1: 3, d2: 3, d3: 3, d4: 3, d5: 3, d6: 3, d7: 3, d8: 3, d9: 3, d10: 3 });
const risposteNasa = ref({ mentale: 5, fisica: 5, temporale: 5, prestazione: 5, sforzo: 5, frustrazione: 5 });
const risposteSeq = ref({ facilita: 4 });

// ==========================================
// LOGICA DI INVIO
// ==========================================
// Sostituisci l'intera funzione inviaEPassaAlProssimo con questa versione infallibile
async function inviaEPassaAlProssimo(tipoQuestionario) {
  isLoading.value = true;
  const config = FORMS_CONFIG[tipoQuestionario];
  
  // 1. Creiamo un elemento <form> HTML al volo in background (invisibile)
  const hiddenForm = document.createElement('form');
  hiddenForm.action = config.url;
  hiddenForm.method = 'POST';
  hiddenForm.target = 'hidden_iframe'; // Mandiamo la risposta in un iframe fantasma per non far ricaricare la pagina Vue
  hiddenForm.style.display = 'none';

  // Funzione di supporto per aggiungere i campi input nel form nascosto
  const aggiungiCampo = (name, value) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = String(value);
    hiddenForm.appendChild(input);
  };

  // 2. Iniettiamo l'ID Partecipante invisibile
  aggiungiCampo(config.idField, participantId.value);
  
  // 3. Iniettiamo le risposte in base al questionario corrente
  if (tipoQuestionario === 'sus') {
    Object.keys(risposteSus.value).forEach(key => {
      aggiungiCampo(config.domande[key], risposteSus.value[key]);
    });
  } else if (tipoQuestionario === 'nasa') {
    Object.keys(risposteNasa.value).forEach(key => {
      aggiungiCampo(config.domande[key], risposteNasa.value[key]);
    });
  } else if (tipoQuestionario === 'seq') {
    Object.keys(risposteSeq.value).forEach(key => {
      aggiungiCampo(config.domande[key], risposteSeq.value[key]);
    });
  }

  // 4. Creiamo un iframe invisibile di destinazione per assorbire il reindirizzamento di Google
  let iframe = document.getElementById('hidden_iframe');
  if (!iframe) {
    iframe = document.createElement('iframe');
    iframe.id = 'hidden_iframe';
    iframe.name = 'hidden_iframe';
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
  }

  // 5. Appendiamo il form al documento, lo inviamo e lo distruggiamo subito dopo
  document.body.appendChild(hiddenForm);
  
  try {
    hiddenForm.submit(); // L'invio nativo bypassa qualunque blocco CORS o di sicurezza!
    
    // Piccolo trucco: aspettiamo mezzo secondo per simulare il caricamento di rete
    await new Promise(resolve => setTimeout(resolve, 600));
    
    // Rimozione del form temporaneo dal DOM
    document.body.removeChild(hiddenForm);

    // LOGICA DI TRANSIZIONE DELLE TAB
    if (tipoQuestionario === 'sus') faseCorrente.value = 'nasa';
    else if (tipoQuestionario === 'nasa') faseCorrente.value = 'seq';
    else if (tipoQuestionario === 'seq') faseCorrente.value = 'completato';
    window.scrollTo(0, 0);
    
  } catch (error) {
    console.error("Errore durante l'invio nativo:", error);
    alert("Errore nell'invio dei dati. Riprova.");
  } finally {
    isLoading.value = false;
  }
}


onMounted(() => {
  participantId.value = generateAnonymousToken();
});
</script>

<template>
  <div class="survey-page-wrapper">
    
    <header class="form-header">
      <div class="header-top">
        <h1>Fase di Test UX</h1>
        <div class="session-badge">Sessione: {{ participantId }}</div>
      </div>
      <div class="progress-bar-flat">
        <div :class="['step-tick', { 'is-active': ['sus','nasa','seq','completato'].includes(faseCorrente) }]">1. SUS</div>
        <div :class="['step-tick', { 'is-active': ['nasa','seq','completato'].includes(faseCorrente) }]">2. NASA</div>
        <div :class="['step-tick', { 'is-active': ['seq','completato'].includes(faseCorrente) }]">3. SEQ</div>
      </div>
    </header>

    <div v-if="faseCorrente === 'sus'" class="survey-step">
      <h2>1. Valutazione Usabilità Generale (SUS)</h2>
      
      <div class="question-row" v-for="(testo, index) in [
        'Penso che vorrei utilizzare questo sistema frequentemente.',
        'Ho trovato il sistema inutilmente complesso.',
        'Ho pensato che il sistema fosse facile da usare.',
        'Penso che avrei bisogno del supporto di un tecnico per essere in grado di utilizzare questo sistema.',
        'Ho trovato che le varie funzioni del sistema fossero ben integrate.',
        'Ho pensato che ci fosse troppa incoerenza in questo sistema.',
        'Immagino che la maggior parte delle persone potrebbe imparare a usare questo sistema molto rapidamente.',
        'Ho trovato il sistema molto scomodo da usare.',
        'Mi sono sentito molto sicuro nell\'usare il sistema.',
        'Ho avuto bisogno di imparare molte cose prima di poter utilizzare questo sistema.'
      ]" :key="`sus-${index}`">
        <div class="question-text">{{ index + 1 }}. {{ testo }}</div>
        <div class="scale-selector">
          <span class="extreme-label">Disaccordo</span>
          <label v-for="voto in 5" :key="`sus-${index}-${voto}`" :class="['radio-tile', { 'is-active': risposteSus[`d${index+1}`] === voto }]">
            <input type="radio" v-model="risposteSus[`d${index+1}`]" :value="voto" />{{ voto }}
          </label>
          <span class="extreme-label">Accordo</span>
        </div>
      </div>

      <button @click="inviaEPassaAlProssimo('sus')" :disabled="isLoading" class="submit-action-btn">
        {{ isLoading ? "SALVATAGGIO IN CORSO..." : "SALVA E VAI AL NASA-TLX" }}
      </button>
    </div>

    <div v-else-if="faseCorrente === 'nasa'" class="survey-step">
      <h2>2. Carico Cognitivo (NASA-TLX)</h2>
      
      <div class="question-row" v-for="(item, key) in {
        mentale: 'Richiesta Mentale: Quanto impegno mentale, di calcolo, decisione o memoria è stato richiesto?',
        fisica: 'Richiesta Fisica: Quanto sforzo fisico è stato richiesto (es. click, scorrimento)?',
        temporale: 'Richiesta Temporale: Hai avvertito pressione temporale o un ritmo troppo frenetico?',
        prestazione: 'Prestazione: Quanto ritieni di aver avuto successo nel raggiungere gli obiettivi dell\'analisi?',
        sforzo: 'Sforzo: Quanto hai dovuto lavorare (mentalmente e fisicamente) per raggiungere questo livello?',
        frustrazione: 'Frustrazione: Quanto ti sei sentito insicuro, scoraggiato, irritato o stressato?'
      }" :key="`nasa-${key}`">
        <div class="question-text">{{ item }}</div>
        <div class="scale-selector">
          <span class="extreme-label">{{ key === 'prestazione' ? 'Fallimento' : 'Molto Basso' }}</span>
          <label v-for="voto in 10" :key="`nasa-${key}-${voto}`" :class="['radio-tile', { 'is-active': risposteNasa[key] === voto }]">
            <input type="radio" v-model="risposteNasa[key]" :value="voto" />{{ voto }}
          </label>
          <span class="extreme-label">{{ key === 'prestazione' ? 'Successo Perfetto' : 'Molto Alto' }}</span>
        </div>
      </div>

      <button @click="inviaEPassaAlProssimo('nasa')" :disabled="isLoading" class="submit-action-btn">
        {{ isLoading ? "SALVATAGGIO IN CORSO..." : "SALVA E VAI ALL'ULTIMO STEP" }}
      </button>
    </div>

    <div v-else-if="faseCorrente === 'seq'" class="survey-step">
      <h2>3. Facilità Singola (SEQ)</h2>
      
      <div class="question-row">
        <div class="question-text">1. Complessivamente, quanto è stata facile o difficile l'operazione appena conclusa nell'interfaccia?</div>
        <div class="scale-selector">
          <span class="extreme-label">Molto Difficile</span>
          <label v-for="voto in 7" :key="`seq-${voto}`" :class="['radio-tile', { 'is-active': risposteSeq.facilita === voto }]">
            <input type="radio" v-model="risposteSeq.facilita" :value="voto" />{{ voto }}
          </label>
          <span class="extreme-label">Molto Facile</span>
        </div>
      </div>

      <button @click="inviaEPassaAlProssimo('seq')" :disabled="isLoading" class="submit-action-btn">
        {{ isLoading ? "SALVATAGGIO IN CORSO..." : "CONCLUDI IL TEST UX" }}
      </button>
    </div>

    <div v-else class="success-feedback">
      <h2>Test Concluso con Successo</h2>
      <p>Grazie per aver partecipato. I tuoi dati di usabilità sono stati sincronizzati in modo anonimo.</p>
    </div>

  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

.survey-page-wrapper {
  font-family: 'JetBrains Mono', monospace;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
  color: #1e293b;
}

/* Header & Progress */
.form-header { margin-bottom: 40px; }
.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-top h1 { font-size: 24px; font-weight: 700; margin: 0; text-transform: uppercase; }
.session-badge { background: #e2e8f0; padding: 6px 12px; font-size: 12px; font-weight: 700; }

.progress-bar-flat { display: flex; gap: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
.step-tick { flex: 1; font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }
.step-tick.is-active { color: #1243e3; }

/* Questions */
.survey-step h2 { font-size: 18px; margin-bottom: 24px; color: #1243e3; text-transform: uppercase; }
.question-row { border-bottom: 1px solid #f1f5f9; padding: 24px 0; }
.question-text { font-size: 13px; font-weight: 700; margin-bottom: 16px; line-height: 1.5; }

/* Scales */
.scale-selector { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.extreme-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }

.radio-tile {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  border: 1.5px solid #e2e8f0; font-size: 12px; font-weight: 700;
  cursor: pointer; background: #fff; transition: all 0.15s ease;
}
.radio-tile input { display: none; }
.radio-tile:hover { border-color: #cbd5e1; }
.radio-tile.is-active { background: #1243e3; border-color: #1243e3; color: #fff; }

/* Buttons */
.submit-action-btn {
  margin-top: 40px; background: #1e293b; color: #fff; border: none;
  padding: 16px 32px; font-family: 'JetBrains Mono', monospace;
  font-size: 12px; font-weight: 700; cursor: pointer; transition: background 0.2s;
  width: 100%; text-align: center;
}
.submit-action-btn:hover { background: #1243e3; }
.submit-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Success */
.success-feedback { border: 2px solid #10b981; padding: 40px; background: #f0fdf4; }
.success-feedback h2 { color: #10b981; margin-top: 0; }
</style>