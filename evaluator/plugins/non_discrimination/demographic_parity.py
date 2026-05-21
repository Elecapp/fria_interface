from fairlearn.metrics import demographic_parity_difference, MetricFrame, selection_rate
from core.plugin_registry import PluginSpec, ParamSpec
from sklearn.preprocessing import LabelEncoder

class DemographicParity:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="demographic_parity",
            name="Demographic Parity",
            right="Non_Discrimination",
            description="Measures demographic parity by computing selection rate differences across sensitive groups.",
            interpretation="Values close to 1 indicate better demographic parity (less disparity) between groups.",
            requires=["X_test", "y_true", "y_pred"],

            params=[
                ParamSpec(
                    key="sensitive_features",
                    type="list[string]",
                    required=True,
                    default=None,
                    label="Sensitive features",
                    help="Select one or more sensitive feature columns (e.g., sex, age)."
                ),
            ],
        )
    
    def __init__(self):
        self.name = "Demographic Parity"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}
        for feature in sensitive_feature_names:
            try:
                if feature not in X_test.columns:
                    raise ValueError(f"Feature '{feature}' not found in X_test.")

                sensitive_column = X_test[feature]
                
                # --- INIZIO PULIZIA DATI ---
                le = LabelEncoder()
                y_true_str = y_true.astype(str)
                y_pred_str = y_pred.astype(str)
                
                le.fit(y_true_str)
                y_true_clean = le.transform(y_true_str)
                y_pred_clean = le.transform(y_pred_str)
                # --- FINE PULIZIA DATI ---

                # Calcolo della differenza
                dp_diff = demographic_parity_difference(
                    y_true=y_true_clean,
                    y_pred=y_pred_clean,
                    sensitive_features=sensitive_column
                )
                
                # Creiamo il MetricFrame per dare al frontend i dati da disegnare
                metric_frame = MetricFrame(
                    metrics=selection_rate,
                    y_true=y_true_clean,
                    y_pred=y_pred_clean,
                    sensitive_features=sensitive_column
                )
                
                selection_rates = {str(k): float(v) for k, v in metric_frame.by_group.to_dict().items()}
                normalized_score = 1.0 - float(dp_diff)

                # Formattazione corretta e standard per il frontend!
                results[feature] = {
                    "metric": self.get_spec().name,
                    "status": "success",
                    "sensitive_feature": feature,
                    "selection_rate_by_group": selection_rates,
                    "difference": float(dp_diff),
                    "final_score": 10.0 * normalized_score
                }
                
            except Exception as e:
                results[feature] = {
                    "metric": self.get_spec().name,
                    "status": "error",
                    "sensitive_feature": feature,
                    "message": str(e)
                }

        return results