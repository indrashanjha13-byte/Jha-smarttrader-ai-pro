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
            max_depth=5,            # Prevents Overfitting on noise
            random_state=42,        # Ensures deterministic/reproducible predictions
            n_jobs=-1               # Uses all CPU cores for faster computation
        )
        self.is_fitted = False
        self.expected_features_count = None
        self.load_model()

    def fit(self, X, y):
        """Train the model with indicator features (X) and trade labels (y: 1 for WIN, 0 for LOSS)."""
        try:
            X_arr = np.array(X)
            if len(X_arr) < 20:
                logging.warning("⚠️ Not enough data samples to train ML Model (Minimum 20 needed).")
                return False

            self.model.fit(X_arr, y)
            self.is_fitted = True
            
            # Save expected number of features for safety during prediction
            if X_arr.ndim > 1:
                self.expected_features_count = X_arr.shape[1]

            self.save_model()
            logging.info("✅ ML Model trained and saved successfully.")
            return True
        except Exception as e:
            logging.error(f"❌ ML Model Training Error: {e}")
            return False

    def predict(self, features):
        """Generates trade prediction (1: BUY, 0: NO TRADE) and confidence score."""
        if not self.is_fitted:
            logging.warning("⚠️ Model not trained yet. Defaulting prediction to 0.")
            return 0, 50.0

        try:
            X_in = np.array(features)
            
            # Reshape 1D array to 2D for single sample prediction
            if X_in.ndim == 1:
                X_in = X_in.reshape(1, -1)

            # Feature Dimension Check
            if self.expected_features_count and X_in.shape[1] != self.expected_features_count:
                logging.error(f"❌ Feature shape mismatch! Expected {self.expected_features_count}, got {X_in.shape[1]}.")
                return 0, 50.0

            pred = self.model.predict(X_in)[0]
            probs = self.model.predict_proba(X_in)[0]
            confidence = round(float(np.max(probs)) * 100, 2)
            
            return int(pred), confidence
        except Exception as e:
            logging.error(f"❌ Prediction Error: {e}")
            return 0, 50.0

    def save_model(self):
        """Persists model and feature count to disk."""
        try:
            joblib.dump({
                "model": self.model,
                "expected_features_count": self.expected_features_count
            }, MODEL_FILE)
        except Exception as e:
            logging.error(f"Failed to save ML Model: {e}")

    def load_model(self):
        """Loads pre-trained model from disk if available."""
        if os.path.exists(MODEL_FILE):
            try:
                saved_data = joblib.load(MODEL_FILE)
                if isinstance(saved_data, dict):
                    self.model = saved_data.get("model", self.model)
                    self.expected_features_count = saved_data.get("expected_features_count", None)
                else:
                    self.model = saved_data  # Backward compatibility
                
                self.is_fitted = True
                logging.info("🧠 Existing ML Model loaded successfully.")
            except Exception as e:
                logging.error(f"Failed to load ML Model: {e}")