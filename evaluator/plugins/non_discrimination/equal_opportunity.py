from fairlearn.metrics import (true_positive_rate_difference, true_positive_rate, MetricFrame) 
from core.plugin_registry import PluginSpec, ParamSpec
import numpy as np
from sklearn.preprocessing import LabelEncoder

class EqualOpportunity:
    @classmethod
    def get_spec(cls):
        return PluginSpec(
            id="equal_opportunity",
            name="Equal Opportunity",
            right="Non_Discrimination",
            description="Measures Equal Opportunity by comparing True Positive Rates across sensitive groups.",
            interpretation="Values close to 0 means equal opportunity is preserved.",
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
            ]
        )

    def __init__(self):
        self.name = "Equal Opportunity"
        self.needs_sensitive_feature = True
        self.requires_all_sensitive_features = False

    def evaluate(self, y_true, y_pred, X_test, sensitive_feature_names):
        results = {}
        
        for feature in sensitive_feature_names:
            if feature not in X_test.columns:
                raise ValueError(f"Feature '{feature}' not found in X_test.")
            
            sensitive_column = X_test[feature]
            
            # 1. CODIFICA FLESSIBILE (Senza stringhe manuali e senza np.array dtype=int)
            le = LabelEncoder()
            y_true_str = y_true.astype(str)
            y_pred_str = y_pred.astype(str)
            
            le.fit(y_true_str)
            y_true_clean = le.transform(y_true_str)
            y_pred_clean = le.transform(y_pred_str)
            
            # 2. CALCOLO DELLA DIFFERENZA (mancava nel codice che mi hai incollato!)
            eo_diff = true_positive_rate_difference(
                y_true=y_true_clean,
                y_pred=y_pred_clean,
                sensitive_features=sensitive_column
            )
            
            # 3. CREAZIONE DEL METRIC FRAME (Assicurandoci di usare i dati _clean)
            metric_frame = MetricFrame(
                metrics={"TPR": true_positive_rate},
                y_true=y_true_clean,
                y_pred=y_pred_clean,
                sensitive_features=sensitive_column
            )

            normalized_score = 1 - eo_diff
            
            results[feature] = {
                "metric": self.get_spec().name,
                "status": "success",
                "sensitive_feature": feature,

                # 4. RISULTATI PULITI DA OGNI .item()
                "tpr_by_group": metric_frame.by_group["TPR"].to_dict(),
                "difference": float(eo_diff),
                "final_score": 10 * float(normalized_score), 
            }
        
        return results