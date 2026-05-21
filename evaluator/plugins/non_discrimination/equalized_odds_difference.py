from fairlearn.metrics import equalized_odds_difference
from core.plugin_registry import PluginSpec, ParamSpec
from sklearn.preprocessing import LabelEncoder
from fairlearn.metrics import false_positive_rate, true_positive_rate, MetricFrame, equalized_odds_difference


class EqualizedOddsDifference:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="equalized_odds_difference",
            name="Equalized Odds Difference",
            right="Non_Discrimination",
            description="Measures Equalized Odds difference across sensitive groups (lower is better).",
            interpretation="Values near 0 indicate prediction errors are evenly distributed.",
            requires=["X_test", "y_true", "y_pred"], #datasets

            #parameters specification
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
        self.name = "Equalized Odds Difference"
        self.needs_sensitive_feature = True

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        
        
        results = {}
        
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")
            
            sensitive_column = X_test[feature]
            
            # --- Inizio blocco pulizia dati ---
            le = LabelEncoder()
            y_true_str = y_true.astype(str)
            y_pred_str = y_pred.astype(str)
            
            le.fit(y_true_str)
            y_true_clean = le.transform(y_true_str)
            y_pred_clean = le.transform(y_pred_str)
            # --- Fine blocco pulizia dati ---
            
            # Calcolo della differenza di Equalized Odds
            eod_diff = equalized_odds_difference(
                y_true=y_true_clean,
                y_pred=y_pred_clean,
                sensitive_features=sensitive_column
            )
            
            # Calcolo del MetricFrame
            metric_frame = MetricFrame(
                metrics={"FPR": false_positive_rate, "TPR": true_positive_rate},
                y_true=y_true_clean,
                y_pred=y_pred_clean,
                sensitive_features=sensitive_column
            )
            
            normalized_score = 1 - eod_diff
            
            # Formattiamo i risultati in dizionari
            fpr_dict = metric_frame.by_group["FPR"].to_dict()
            tpr_dict = metric_frame.by_group["TPR"].to_dict()
            
            # Uniamo FPR e TPR in un formato che il frontend sa leggere
            rates_by_group = {
                group: {"FPR": fpr, "TPR": tpr_dict[group]}
                for group, fpr in fpr_dict.items()
            }
            
            results[feature] = {
                "metric": self.get_spec().name,
                "status": "success",
                "sensitive_feature": feature,
                "rates_by_group": rates_by_group,
                "difference": float(eod_diff), # Tolto .item()
                "final_score": 10 * float(normalized_score), # Tolto .item()
            }
        
        return results