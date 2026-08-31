from sklearn.ensemble import RandomForestClassifier
import numpy as np
import logging
import joblib
import os

MODEL_FILE = "rf_model.pkl"


class TradeMLModel:

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            n_jobs=-1
        )
        self.is_fitted = False
        self.load_model()

    def fit(self, X, y):
        try:
            if len(X) < 20:
                logging.warning("⚠️ Not enough data samples to train ML Model.")
                return False

            self.model.fit(X, y)
            self.is_fitted = True
            self.save_model()
            logging.info("✅ ML Model trained and saved.")
            return True
        except Exception as e:
            logging.error(f"❌ ML Model Training Error: {e}")
            return False

    def predict(self, features):
        if not self.is_fitted:
            return 0, 50.0

        try:
            X_in = np.array(features).reshape(1, -1)
            pred = self.model.predict(X_in)[0]
            probs = self.model.predict_proba(X_in)[0]
            confidence = round(float(np.max(probs)) * 100, 2)
            return int(pred), confidence
        except Exception as e:
            logging.error(f"❌ Prediction Error: {e}")
            return 0, 50.0

    def save_model(self):
        try:
            joblib.dump(self.model, MODEL_FILE)
        except Exception as e:
            logging.error(f"Failed to save ML Model: {e}")

    def load_model(self):
        if os.path.exists(MODEL_FILE):
            try:
                self.model = joblib.load(MODEL_FILE)
                self.is_fitted = True
                logging.info("🧠 ML Model loaded.")
            except Exception as e:
                logging.error(f"Failed to load ML Model: {e}")