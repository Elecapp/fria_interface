<script setup>
import { API_HOST } from "../utils/config";
import { computed, onMounted, ref, shallowRef } from "vue";
import { useRoute, useRouter } from "vue-router";

import ConditionalNestedView2 from "../components/metrics/ConditionalNestedView2.vue";
import ScalarMapView from "../components/metrics/ScalarMapView.vue";
import GroupMetricMapView2 from "../components/metrics/GroupMetricMapView2.vue";
import RecordWithTableView from "../components/metrics/RecordWithTableView.vue";
import CardMap from "../components/metrics/CardMap.vue";
import { getSessionId } from "../utils/report_builder_helper";

const route = useRoute();
const router = useRouter();

const group = computed(() => String(route.params.group || "")); 
const metricKey = computed(() => String(route.params.metric || "")); 

const loading = ref(false);
const error = ref("");

const runId = ref(String(route.query.runId || ""));   
const allResults = ref({}); 
const allSchemas = ref({}); 
const forceRenderKey = ref(Date.now());

const metricViewRef = shallowRef(null);

async function handleBack() {
  const view = metricViewRef.value;
  
  if (view && typeof view.goBackSafely === "function") {
    await view.goBackSafely();
    return;
  }
  
  const childContainer = document.querySelector('.content-container');
  if (childContainer) {
    const buttons = Array.from(childContainer.querySelectorAll('button'));
    const saveBtn = buttons.find(b => 
      (b.textContent.toLowerCase().includes('save') || b.textContent.toLowerCase().includes('submit')) && 
      !b.classList.contains('btn-confirm')
    );
    
    if (saveBtn) {
      saveBtn.click(); 
      setTimeout(() => { router.back(); }, 600); 
      return;
    }
  }

  try {
    const payload = {
        run_id: runId.value,
        metric: metricKey.value,
        group: group.value,
        weights: {},
        justifications: {},
        reversibilityByLabel: {},
        gravity: metricObj.value?.gravity ?? metricObj.value?.user_weight ?? 0,
        reversibility: metricObj.value?.reversibility ?? false,
        user_weight: metricObj.value?.user_weight ?? metricObj.value?.gravity,
        user_justification: metricObj.value?.user_justification ?? metricObj.value?.justification ?? ""
    };

    if (metricObj.value) {
        for (const key in metricObj.value) {
            const feat = metricObj.value[key];
            if (feat && typeof feat === 'object') {
                if (feat.user_weight !== undefined || feat.gravity !== undefined || feat.weight !== undefined) {
                    payload.weights[key] = feat.user_weight ?? feat.gravity ?? feat.weight;
                    payload.justifications[key] = feat.user_justification ?? feat.justification ?? "";
                    payload.reversibilityByLabel[key] = feat.reversibility ?? false;
                }
            }
        }
    }
    
    const APIHOST = `${API_HOST}`;
    payload.session_id = getSessionId();
    await fetch( APIHOST+"/results/save_weights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
  } catch (e) {
      console.error("Salvataggio di emergenza fallito", e);
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
  let scores = [];
  function findScores(obj) {
    if (!obj || typeof obj !== 'object') return;
    if (obj.final_score !== undefined && typeof obj.final_score === 'number') scores.push(obj.final_score);
    else if (obj["Final Score"] !== undefined && typeof obj["Final Score"] === 'number') scores.push(obj["Final Score"]);
    for (const key in obj) findScores(obj[key]);
  }
  findScores(metricObj.value);
  if (scores.length > 0) {
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    return (avg <= 1 ? avg * 10 : avg).toFixed(2);
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

function deepRestore(obj) {
  if (!obj || typeof obj !== 'object') return;
  
  if ('user_weight_report' in obj) { obj.user_weight = obj.user_weight_report; obj.weight = obj.user_weight_report; }
  if ('gravity_report' in obj) { obj.gravity = obj.gravity_report; }
  if ('user_justification_report' in obj) { obj.user_justification = obj.user_justification_report; obj.justification = obj.user_justification_report; }
  if ('reversibility_report' in obj) { obj.reversibility = obj.reversibility_report; }
  
  if ('gravity' in obj && !('user_weight' in obj)) obj.user_weight = obj.gravity;
  if ('user_weight' in obj && !('gravity' in obj)) obj.gravity = obj.user_weight;

  Object.values(obj).forEach(val => { if (typeof val === 'object') deepRestore(val); });
}

// --- DIZIONARIO METRICHE (Con spazio per inserire il link delle immagini) ---
// Inserisci l'URL dell'immagine presa dalle slide nel campo `image: "..."`
const metricDescriptions = {
  anonymity_set_size: {
    text: "The core purpose of this metric is to assess how much risk there is that our data could be 'de-anonymized' (meaning, how easily we could figure out who a specific person is). <br><br> <b>The Rule of Thumb:</b><ul><li> A large Anonymity Set Size means many people share those characteristics (i.e., the so-called quasi-identifiers), making it very difficult to point to any single person. This suggests a lower risk.</li><li> A very small Anonymity Set Size (e.g., 1, 2, or 3) means that only a handful of people share that specific combination of traits. This suggests a high risk because that small group could be vulnerable to re-identification. </li></ul><br>In short, a low Anonymity Set Size is a warning sign that the data might be too specific and could compromise the privacy of the people within it.",
    accordionText: "<b>Scenario:</b> Your dataset includes records for people who work in veterinary medicine and live in a specific small town. </br> <b>Result:</b> The Anonymity Set Size for this combination is 3. <br><b>Interpretation:</b> This means only three people in the entire dataset match the pattern ('Vet' + 'Small Town'). If the system were to leak details about this group, those three individuals could be easily identified, posing a significant privacy risk.",
    image: "/img/anonimity_set_size.png" 
  },
  k_anonymity: {
    text: "<b>K-anonymity aims to make each individual so similar as to be indistinguishable from at least k-1 others</b>.<br> k-anonymity is a privacy metric that <b>ensures that if we know certain characteristics about you, we cannot definitively point you out</b>. <br> Think of k as a minimum group size. When a dataset achieves k-anonymity, it means that for any combination of patterns (like a specific combination of Zip Code, Age, and Occupation), which are usually called quasi-identifiers, there must be at least k people who share those characteristics.<br><br><b>The Rule of Thumb:</b><ul><li> A high k (e.g. k=50) is usually considered a good result. This means that for any pattern observed, there are at least 50 people who match. If an attacker knows a specific pattern, they only narrow the risk down to a large, manageable group, making individual identification nearly impossible. This suggests a low risk.</li><li> A low k (e.g. k=3) is concerning. This means that for some specific patterns, only a very small number of people match. If an attacker knows that pattern, they have only three potential targets, significantly raising the risk of privacy violation.</li></ul><br> In simple terms, the higher the k value, the stronger the guarantee of anonymity and the better the protection for the people whose data is being used. ",
    accordionText: "<b>Scenario:</b> Your dataset contains information about people who are retired, live in a small county, and enjoy horse riding. <br><b>Result:</b> The system reports a k-anonymity of 4. At this stage of the computation, k-anonymity is used only to compute the minimum Anonymity Set score in the dataset.<br> <b>Interpretation:</b> This means that for the combination of 'Retired + Small County + Horse Riding,' there are at least four people in the dataset who match. This is better than if only two people matched, but if the goal was a high level of privacy (e.g. k=10), the data might still be too specific and needs further protection.",
    image: "/img/k-anonimity.png"
  },
  l_diversity: {
    text: "l-diversity is a privacy measure that acts as a <b>safety check after k-anonymity</b> has been applied.<br> If k-anonymity makes sure that we cannot identify a person by their characteristics, <b>l-diversity makes sure that even if we know they belong to a group, we cannot guess their sensitive private details</b>. <br> Imagine a dataset that is k-anonymous, meaning 100 people are grouped together (high k). This seems safe, right? <br>However, the risk is that all 100 people in that group might share the same extremely private detail (the <i>sensitive attribute</i>). <br> For example, if every person in that group of 100 all suffered from a certain medical condition, their shared secret is exposed. This is called a <i>Homogeneity Attack</i>.<br><br><b> The Rule of Thumb</b>: <ul><li> <b>High l (Good)</b>: If l is large, it means the information is highly diverse. Within the group, there are many different outcomes or details, making it impossible for an attacker to deduce a single, secret piece of information about any individual.</li><li><b> Low l (Bad)</b>: If l is small (like 1 or 2), it means the group is homogenous—meaning many members share the same private detail. This indicates a significant privacy risk, even if the group size is large.</li></ul><br> In simple terms, <b>l-diversity ensures variety. The higher the l value, the better the data protection against the leakage of private details.</b> ",
    accordionText: "<b>Scenario</b>: The AI system analyzes a group of patients who live in the same area and have similar ages (k-anonymous group). The 'sensitive attribute' is the patient's diagnosis. <br><b>Result</b>: The system reports an l-diversity of 2. <br><b>Interpretation:</b> This is a concern. It means that while the group is large, at least some subset of that group only share two possible diagnoses (e.g., 'Condition A' or 'Condition B'). <br>This significantly increases the risk, as an attacker might be able to determine which of those two conditions a specific patient has.",
    image: "/img/l_diversity.png" 
  },
  t_closeness: {
    text: "The goal of t-Closeness is to ensure that the probability of an outcome for a specific group in your <i>data</i> is very close to the probability of that same outcome for that group in the <i>actual population</i>. <br> Think of t-Closeness not as a measurement of data, but as a measurement of <b>fairness in representation</b>.<br> Most privacy techniques ensure that no single group is overly exposed, but t-Closeness ensures that the <i>sensitive features</i> within the data are representative of the real world. <br><b>The Rule of Thumb:</b> <ul><li><b>High t-Closeness:</b> There is a high distance between the original data and the anonymized version of it. The equivalence classes are highly unrepresentative or biased. </li><li><b>Low t-Closeness</b>: The data is highly representative of real world. This should offer some protection against fine attacks, leveraging on additional background knowledge.",
    accordionText: "<b>Example in a Concrete scenario</b>: Imagine you are building a system for helping doctors in reaching diagnosis.<br><ul><li> <b>The Whole Original Dataset</b>: The entire patients population (i.e., diverse disease).</li><li><b>The considered equivalence class</b>: medical records where patients are sharing the same quasi-identifiers.</li></ul><br> When the disease values in an equivalence class are distinct but semantically similar (for example, they are all stomach-related diseases), an adversary can rely on this <i>similarity attack</i> and learn important information. <br> When the disease values are heart-related diseases but there is one different value, an adversary can rely on the <i>background knowledge</i> attack to exclude strokes, arrhythmias, cardiomyopathy, whether the attack target is usually not subjected to such diseases (for example, Japanese people have an extremely low incidence of heart disease).",
    image: "/img/t-closeness.png" 
  },
  mutual_information_metric: {
    text: "Mutual Information (MI) answers the question: <b>'How much does knowing the value of Feature A help you guess the value of Feature B?'</b><br> In the context of data privacy and AI development, <b>Mutual Information (MI)</b> is a mathematical measure that quantifies the <b>statistical dependency</b> between two or more variables (or features).<br><br> <i>Why is Mutual Information Critical for AI Privacy? </i> <br> When building an Artificial Intelligence model, we feed it hundreds of features (like age, location, spending habits, etc.). Many of these features might be completely unnecessary or might inadvertently reveal sensitive information.<br> <br>The core goal of analyzing MI is to perform a 'dependency check' to Detect Leakage (identify if a seemingly innocuous feature is highly dependent on a sensitive attribute like race or health status) and Identify Redundancy.<br><b> The Rule of Thumb</b>:<ul><li><b> High MI Score</b>: Means the features are strongly dependent. Knowing one tells you a lot about the other (a potential privacy leak or redundancy).</li><li><b> Low MI Score</b>: Means the features are independent.</li></ul>",
    accordionText: "<b>Example in a Concrete scenario</b>: <ul><li><b>Feature A</b>: person's ZIP code.</li><li><b> Feature B</b>: A person's racial background.</li><li><b> MI Score</b>: High.</li><li><b> Meaning</b>: Because certain ZIP codes are heavily concentrated with specific populations, knowing the ZIP code gives you a very strong hint about the person’s race. The ZIP code, therefore, is not independent of the race attribute, making it a potential privacy risk even if it wasn't explicitly labeled as 'race'.</li></ul>",
    image: "/img/mutual_information.png" 
  },
  demographic_parity: {
    text: "Demographic Parity is a fairness check. Its purpose is to determine if an Artificial Intelligence (AI) system is giving positive results (like a 'yes' or an 'approve') to different groups of people at the same rate.<br> Think of it as <b>checking if the AI system treats all groups equally, regardless of who they are.</b><br><br> <b>The Rule Of Thumb</b>: <ul><li> <b>The Check</b>:It compares the chance that Group A gets a 'Yes' compared to the chance that Group B gets a 'Yes.'</li><li><b>The Goal of Fariness</b>: If the AI is fair, these rates should be nearly the same. If the rates are significantly different, it suggests the system is biased or discriminating against a certain group.</li></ul>",
    accordionText: " When assessing an AI system's impact on your rights, especially your right to non-discrimination, you are asking: <b>Is the AI making decisions based on qualifications, or is it making decisions based on who you are?</b> <br>If the Demographic Parity metric shows a large difference in outcomes between groups, it is a strong indicator of algorithmic bias. This bias means the system is unfairly restricting opportunities for one group over another, which can be seen as a violation of the fundamental right of non-discrimination. <br><br><b>Example in a Concrete Scenario</b>: <ul><li><b>The AI System</b>: Decides who qualifies for a bank loan.</li><li><b> The Groups</b>: People living in a specific, lower-income neighborhood (Group A) vs. people living in an affluent neighborhood (Group B).</li><li><b> The Result</b>: The metric shows that only 10% of applicants from Group A receive a loan, but 60% of applicants from Group B receive a loan.</li><li><b> Interpretation</b>: The AI is showing a clear difference in outcomes, suggesting that the system may be unfairly penalizing people simply because of where they live, rather than based on their actual financial merit.</li></ul>",
    image: "/img/demographic_parity.png" 
  },
  disparate_impact: {
    text: "Disparate Impact is a fairness check that <b>measures whether an AI system is affecting different groups of people at dramatically different rates</b>.<br> It doesn't matter if the AI was programmed to discriminate; what matters is the <b>outcome</b>. <br>If the system results in one group having a much lower chance of success than another group, even if the AI never looked at identity factors like gender or race, then it shows a potential unfair impact.<br> <b>The Rule of Thumb</b>: <ul><li><b>The Check</b>:It compares the likelihood of getting a positive result for different groups.</li><li><b>The Goal of Fairness</b> For the AI to be considered fair, the chances of success must be roughly equal across all groups.</li></ul>",
    accordionText: " When assessing an AI system's impact on your right to non-discrimination, you are asking: Are people from one group being disproportionately blocked from opportunities compared to others?<br> If the Disparate Impact metric shows a wide and measurable gap in selection rates, it serves as powerful evidence that the AI system is introducing systemic bias. This bias creates an unfair advantage or disadvantage, which is a violation of the right to non-discrimination.<br><br><b>Example in a Concrete Scenario</b>: <ul><li><b>The AI System</b>: Reviews resumes and assigns a 'suitability score' to candidates.</li><li><b> The Groups</b>: Candidates from a specific demographic background (Group A) vs. candidates from a different background (Group B).</li><li><b> The Result</b>: The metric shows that Group B receives the top-ranking score 75% of the time, but Group A only receives the top-ranking score 20% of the time.</li><li><b> Interpretation:</b> The impact is disparate. The system is disproportionately favoring one group, suggesting that the underlying data or rules used by the AI are creating an unfair barrier for Group A.</li></ul>",
    image: "/img/disparate_impact.png" 
  },
  equal_opportunity: {
    text: "This metric focuses on fairness among the qualified. It asks a specific question: <br><i>If two people are equally qualified for a job, applying for a loan, or needing help, will the system treat them the same way?</i><br> It doesn't care about who is disqualified; it only focuses on the group that <i>should</i> succeed. <br><br><b>The Rule of Thumb</b>: <br> You are looking for <b>equality</b>.<ul><li> <b>The Green Light (Good)</b>: If the success rates are similar across all groups, the system is fair.</li><li><b> The Yellow/Red Light (Bad)</b>: If one group consistently has a much lower success rate, the system is biased.</li></ul><br> A significant gap indicates that the criteria used by the system are systematically disadvantaging a particular group, regardless of their actual qualifications.<br><br><b>In simple terms:</b> this metric measures how often the system correctly identifies a qualified person, and whether that rate is the same across different groups.",
    accordionText: "Example in a concrete scenario:<br><br> A hiring system is being tested.<br><ul><li> 1.The system is tested on 100 equally qualified candidates.</li><li> 2.It finds 90 successes for Group A.</li><li>3. It only finds 50 successes for Group B.</li></ul><b> Conclusion</b>: The system shows a failure of equal opportunity, as it fails Group B disproportionately, suggesting systemic bias.",
    image: "/img/equality_of_opportunity.png" 
  },
  equalized_odds_difference: {
    text: "Equalized Odds demands that an algorithm must make errors at the same rate across different groups.<br><br>When we look at a high-stakes decision (like approving a loan, flagging a criminal, or accepting a job candidate), we aren't just worried about being right overall. We are worried about who we are wrong about.<br><br>For a system to be considered fair under Equalized Odds, it must pass two key fairness tests:<br><br><ul><li><b>Test 1: Equal False Negative Rates (The 'Missed Opportunity' Check).</b> This checks if the system is equally likely to fail to recognize someone who is genuinely qualified or safe. In practice: If the system is much more likely to mistakenly flag a qualified person from Group A, while leaving a qualified person from Group B alone, it is unfair. This means the opportunity for Group A is being unfairly cut off. The Goal: To make sure that the chance of missing a qualified individual is the same across all protected groups.</li><br><li><b>Test 2: Equal False Positive Rates (The 'Wrongful Accusation' Check).</b> This checks if the system is equally likely to mistakenly reject someone who is actually qualified or safe. In practice: If the system is much more likely to wrongly flag a harmless person from Group A, while letting a harmful person from Group B slip through, it is unfair. This means Group A is bearing a disproportionate risk of being punished or rejected based on flawed data. The Goal: To make sure that the rate of making an incorrect, harmful judgment (a false positive) is the same across all protected groups.</li></ul><br><b>The Rule of Thumb:</b> IF the error rates (FNR and FPR) are statistically different between groups, the system is biased, and it cannot be used until the disparity is corrected.",
    accordionText: "<b>Example in a concrete scenario:</b> Imagine a bank uses an algorithm to decide who gets a loan. <br><br>The system is comparing two protected groups, Group A and Group B. <br><b>The Equalized Odds Standard</b>: To be fair, the bank must ensure that the system has the same chance of missing a qualified person in Group A as it does in Group B, AND it must have the same chance of making a wrong, risky approval in both groups.",
    image: "/img/equalized_odds.png" // Ricordati di mappare la slide corrispondente nella cartella public/img!
  },
  
  predictive_parity: {
    text: "Predictive Parity is a fairness metric that answers the question: “When the AI predicts a positive outcome, is that prediction equally trustworthy for all groups of people?”<br><br>It measures whether the AI model is equally accurate and reliable when making a positive prediction across different groups (e.g., based on gender, race, or age).<br><br><b>Why is it important for fairness?</b> The right to non-discrimination means that opportunities and judgments should be based on merit, not on who a person is. When the metric shows a major imbalance, it suggests that the AI model might be systemically more reliable—or simply more accurate—for one group than another. This doesn't mean the model is intentionally biased, but it means that its judgments are inherently less dependable for the disadvantaged group. If the model is less dependable, the outcomes for that group might be unfairly negative. For example, the model might refuse a loan to someone in Group B, not because they are actually risky, but because the model has historically shown less trust in making accurate positive predictions about Group B.<br><br><b>The Rule of Thumb:</b> When you review the predictive parity score, you are looking for consistency.<br><br><ul><li><b>Goal:</b> The metric should be close to 1 (or very balanced) across all measured groups. This indicates the model is equally reliable.</li><br><li><b>Warning Sign:</b> If the metric is significantly lower for one group, it means the model’s predictions are not equally trustworthy. You should investigate why the model’s positive predictions are less reliable for that specific group, as this imbalance itself constitutes a risk of unfair discrimination.</li></ul>",
    accordionText: "<b>Example in a concrete scenario:</b><br><br><ul><li><b>Scenario:</b> An AI model predicts which applicants are 'highly likely' to succeed in a job.</li><br><li><b>Assessment:</b> If the predictive parity score is low for female applicants compared to male applicants, it suggests that even when the AI predicts a female applicant will succeed, that prediction is less trustworthy. This could lead to talented female applicants being unfairly filtered out by a system that is not equally sure of its positive judgments.</li></ul>",
    image: "/img/predictive_parity.png" 
  },

  overall_accuracy_equality: {
    text: "Overall Accuracy Equality asks: “Is the AI system performing equally well for all groups of people?”<br><br>It measures whether the model has the same overall rate of correctness (its 'accuracy') when judging individuals from different groups (e.g., men vs. women, or people in different geographical areas). It is the broadest check of fairness, asking: Are we trusting this AI system equally for everyone?<br><br><b>Why is it important for fairness?</b> The right to non-discrimination means that individuals should be treated fairly, and equally, under the law. If a model has significantly lower accuracy for one group, it means that the judgments being made about that group are fundamentally flawed and unreliable. This flaw can lead to discrimination—not because the AI is intentionally biased, but simply because it is wrong more often when judging that group.<br><br>If the accuracy is high and equal: The AI is consistently good at its job, regardless of who it is looking at. If the accuracy is uneven: The people in the group with lower accuracy are being treated unfairly because the system's judgments about them are inherently unreliable.<br><br><b>The Rule of Thumb:</b> When you review the overall accuracy equality score, you are looking for consistency across the board.<br><br><ul><li><b>Goal:</b> The metric should be close to 1 (or very balanced) across all measured groups. This indicates that the model performs at the same high standard for everyone.</li><br><li><b>Warning Sign:</b> If the metric is significantly lower for one group, you must be concerned. It means the system is consistently misunderstanding, misinterpreting, or making errors when dealing with that group. This signals a critical weakness in the system that needs correction before it can be used fairly.</li></ul>",
    accordionText: "<b>Example in a concrete scenario:</b><br><br><ul><li><b>Scenario:</b> An AI system predicts the likelihood that a person will file a claim against their insurance policy.</li><br><li><b>Assessment:</b> If the overall accuracy is significantly lower for a lower-income group, it means the system is making more mistakes about that group. It might frequently misclassify low-risk people as high-risk, or vice versa. This leads to an unfair denial of coverage or the application of unaffordable rates, simply because the model cannot accurately read the data from that group.</li></ul>",
    image: "/img/overall_accuracy_equality.png" 
  },
  conditional_statistical_parity: {
    text: "Conditional Statistical Parity addresses the question: “If we compare two people who have the same measurable qualifications, should the AI treat them the same, regardless of their background?”<br><br><b>The Rule of Thumb:</b> When you review the conditional statistical parity score, you are looking for conditional equality.<br><br><ul><li><b>Goal:</b> The metric should show that the prediction probability is the same across all groups, given that the measurable factors are identical. This confirms the AI is acting only on the relevant qualifications.</li><br><li><b>Warning Sign:</b> If the metric is unbalanced, it means the AI is disproportionately assigning weight or risk to the protected attribute. The system isn't merely inaccurate for one group; it is exhibiting a patterned bias that cannot be explained solely by the qualifications themselves.</li></ul>",
    accordionText: "This metric controls for measurable factors (like income, education, or test scores). Instead of just comparing the average result for an entire group, it asks the AI to prove that its predictions are based only on the objective facts, and not on protected characteristics like race or gender.<br><br><b>Why is it important for fairness?</b> The right to non-discrimination requires that opportunities should be based on merit. When the metric shows an imbalance, it means the AI model is finding systemic differences even after accounting for the actual qualifications. It suggests that the protected characteristic (like race) is playing a hidden or measurable role in the model’s decision-making process—a form of indirect or systemic discrimination.<br><br><hr style='border:0; border-top:1px dashed #cbd5e1; margin:15px 0;'><br><b>Example in a concrete scenario:</b><br><br><ul><li><b>Scenario:</b> An AI model is deciding whether to approve a loan applicant.</li><br><li><b>Assessment:</b> Using Conditional Statistical Parity, we can filter out all applicants who have the exact same credit score, debt-to-income ratio, and years of employment. If the model still recommends fewer loans for applicants from one ethnic group compared to another—even though their financial profiles are identical—it indicates that the model is introducing a discriminatory factor unrelated to credit risk.</li></ul>",
    image: "/img/conditional_statistical_parity.png" 
  },
  conditional_use_accuracy_equality: {
    text: "Conditional Use Accuracy Equality checks if the model's biases 'activate' only when a specific combination of two or more features appears together. It asks: 'Does the model fail to be fair only when Group A meets Condition B?'<br><br><b>The Rule of Thumb:</b> When analyzing your metrics, do not look for a single average number. Look for discrepancies across the intersections of features. Use this simple rule when comparing your risk assessment results: 'If I can find one combination of two or more attributes (e.g., Female AND Blue-collar), where the performance or error rate is significantly worse than the system average, the system fails the fairness test.'",
    accordionText: "Think of it like stress-testing a bridge. You don't just test the bridge when it's empty; you test it when it's carrying a specific weight (a container filled with heavy equipment) or when it's hit by a specific force (a flash flood).<br><br>What Does a Conditional Test Examine? A conditional test looks for interaction bias or interaction effects. It checks if the relationship between the outcome and the protected characteristic (like race, gender, or socioeconomic status) changes depending on the values of other variables. It reveals 'hidden' biases that are invisible when you look at the groups in isolation.<br><br><ul><li><b>Scenario 1 (Simple Test):</b> The model is fair for men overall, and it is fair for women overall. (Good)</li><br><li><b>Scenario 2 (Conditional Test):</b> The model might be perfectly fair for men in general, AND perfectly fair for women in general. BUT, the model might suddenly become highly unfair only when the group is composed of low-income, single mothers.</li></ul><br><hr style='border:0; border-top:1px dashed #cbd5e1; margin:15px 0;'><br><b>Example in a concrete scenario:</b> Imagine a bank AI is evaluating loan risk. The simple test might show: The AI is fair for all white applicants, and the AI is fair for all Hispanic applicants. The conditional test checks the interaction: The bank suspects that the risk factor is not just income, but the combination of low income AND living in a specific, lower-income zip code. If the model unfairly rejects loans only for Hispanic applicants who live in that specific zip code, the model has a conditional bias.",
    image: "/img/conditional_use_accuracy_equality.png" 
  },

};

const currentDescription = computed(() => {
  return metricDescriptions[metricKey.value] || null;
});

onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";
    if (route.query.runId) runId.value = String(route.query.runId);

    const t = new Date().getTime();
    const sid = getSessionId();
    const res = await fetch(`${API_HOST}/results/values_to_display?run_id=${runId.value}&session_id=${sid}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    runId.value = String(data?.run_id || runId.value || "");  
    const results = data?.results ?? {};
    deepRestore(results);
    allResults.value = results;

    if (data?.schemas) {
      allSchemas.value = data.schemas;
    } else {
      // ORA CHIEDE GLI SCHEMI CORRETTAMENTE!
      const sres = await fetch(`${API_HOST}/results/result_schemas?run_id=${runId.value}`);
      
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

      <div v-if="currentDescription" class="metric-description-section">
        
        <div class="metric-desc-text" v-html="currentDescription.text"></div>
        
        <details v-if="currentDescription.accordionText" class="metric-accordion">
          <summary>View Example / Concrete Scenario</summary>
          <div class="accordion-content">
            <div v-html="currentDescription.accordionText"></div>
          </div>
        </details>

        <div class="image-placeholder-container">
          <img 
            v-if="currentDescription.image" 
            :src="currentDescription.image" 
            alt="Metric visualization" 
            class="metric-image" 
          />
          <div v-else class="empty-image-box">
            <span>[ QUI ANDRÀ L'IMMAGINE DELLA PRESENTAZIONE - INSERISCI IL LINK NEL CODICE ]</span>
          </div>
        </div>
      </div>

      <component
        v-if="renderer"
        :is="renderer"
        :key="`${metricKey}-${forceRenderKey}`"
        :metric-key="metricKey"
        ref="metricViewRef"
        :metric-obj="metricObj"
        :schema-type="metricSchemaFromBackend"
        :run-id="runId"                 
        @go-back-safe="handleChildSafeBack"
      ></component>

      <div v-if="renderer" class="action-footer">
        <button class="btn-primary btn-confirm" @click="handleBack">
          Confirm Changes & Return to Dashboard
        </button>
      </div>

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

.wrapper { min-height: 100vh; background-color: #faf9f8; font-family: 'Inter', sans-serif; padding: 40px 20px; }
.content-container { max-width: 1300px; width: 100%; margin: 0 auto; min-width: 0; }

:deep(.summary-container), :deep(table), :deep(pre), :deep(.fallback-card), :deep(.disparity-summary), :deep(.context-condition) {
  max-width: 100% !important; overflow-x: auto !important; box-sizing: border-box;
}

.top-navigation { margin-bottom: 24px; }
.btn-ghost { background: transparent; border: none; font-weight: 600; cursor: pointer; color: #64748b; font-family: 'Inter', sans-serif; transition: 0.2s; }
.btn-ghost:hover { color: #1e293b; text-decoration: underline; }

.executive-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 40px; border-bottom: 2px solid #1243e3; padding-bottom: 20px; }
.metric-title { font-family: 'Instrument Serif', serif; font-size: 56px; font-weight: 600; color: #1243e3; margin: 0; text-transform: capitalize; line-height: 1; }
.badge-likelihood { display: flex; flex-direction: column; align-items: flex-end; background: #1243e3; color: white; padding: 15px 30px; }
.badge-label { font-family: 'JetBrains Mono', monospace; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #cbd5e1; margin-bottom: 4px; }
.badge-value { font-family: 'JetBrains Mono', monospace; font-size: 36px; font-weight: 700; color: #fff; line-height: 1; }

/* STILI DELLA NUOVA SEZIONE DESCRIZIONE ED IMMAGINI */
.metric-description-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.metric-desc-text {
  font-size: 1.05rem;
  color: #334155;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.metric-accordion {
  margin-bottom: 2rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
}

.metric-accordion summary {
  background: #f8fafc;
  padding: 1rem;
  font-weight: 600;
  cursor: pointer;
  color: #1243e3;
  list-style: none;
  position: relative;
  border-bottom: 1px solid transparent;
}

.metric-accordion summary::-webkit-details-marker { display: none; }
.metric-accordion summary::after {
  content: "▼"; position: absolute; right: 1rem; font-size: 0.8rem; color: #64748b; transition: transform 0.2s;
}
.metric-accordion[open] summary { border-bottom-color: #cbd5e1; }
.metric-accordion[open] summary::after { transform: rotate(180deg); }

/* IL TESTO GRIGIO NELL'ACCORDION */
.accordion-content {
  padding: 1.5rem;
  background: #f8fafc; /* Sfondo leggermente grigio */
  color: #64748b;      /* Testo grigio */
  font-style: italic;  /* Corsivo per distinguere l'esempio */
  font-size: 0.95rem;
  line-height: 1.6;
}

/* SPAZIO IMMAGINI */
.image-placeholder-container {
  width: 100%;
  margin-top: 1rem;
  display: flex;
  justify-content: center;
}

.metric-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.empty-image-box {
  width: 100%;
  height: 250px;
  background: #f1f5f9;
  border: 2px dashed #cbd5e1;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.9rem;
  text-align: center;
  padding: 20px;
}
/* FINE STILI DESCRIZIONE */

.action-footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e5; display: flex; justify-content: flex-end; }
.btn-primary { background-color: #1243e3; color: white; border: none; padding: 14px 32px; font-size: 16px; font-weight: 600; cursor: pointer; font-family: 'Inter', sans-serif; transition: all 0.2s ease; border-radius: 4px; }
.btn-primary:hover { background-color: #0f36b3; box-shadow: 0 4px 12px rgba(18, 67, 227, 0.2); }
.btn-primary:active { transform: scale(0.98); }

.fullscreen-msg { height: 80vh; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #666; }
.error-msg { color: #e11d48; }
.spinner { width: 40px; height: 40px; margin-bottom: 1rem; border: 3px solid #e5e5e5; border-top: 3px solid #1243e3; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
.fallback-card { background: #fff; border: 1px solid #e5e5e5; padding: 2rem; margin-top: 20px; }
.pre { background: #f8fafc; padding: 1rem; font-size: 0.85rem; overflow-x: auto; font-family: 'JetBrains Mono', monospace; }
.muted { color: #888; font-size: 0.9rem; }
</style>