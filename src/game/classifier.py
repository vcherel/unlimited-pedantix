import hashlib
import json
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sentence_transformers import SentenceTransformer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, fbeta_score
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from tqdm import tqdm

from config import SCORE_THRESHOLD


class BaseModel(ABC):
    """Base class for all models"""

    def __init__(self, use_smote):
        self.model = None
        self.use_smote = use_smote
        self.name = self.__class__.__name__

    @abstractmethod
    def create_model(self):
        """Create and return the sklearn/xgboost model"""
        pass

    def train(self, X_train, y_train):
        """Train the model"""
        self.model = self.create_model()
        self.model.fit(X_train, y_train)

    def predict(self, X):
        """Predict classes"""
        return self.model.predict(X)

    def predict_proba(self, X):
        """Predict probabilities"""
        return self.model.predict_proba(X)


class XGBoostModel(BaseModel):
    def __init__(self, use_smote, scale):
        super().__init__(use_smote)
        self.scale = scale

    def create_model(self):
        if self.use_smote:
            return xgb.XGBClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=5,
                reg_alpha=0.1,
                reg_lambda=1.0,
                gamma=0.1,
                random_state=42,
            )
        else:
            return xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                scale_pos_weight=self.scale,
                subsample=0.9,
                colsample_bytree=0.8,
                min_child_weight=3,
                reg_lambda=1.0,
                random_state=42,
            )


class RandomForestModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                min_samples_split=10,
                min_samples_leaf=5,
                max_features="sqrt",
                n_jobs=-1,
                random_state=42,
            )
        else:
            return RandomForestClassifier(
                n_estimators=150,
                max_depth=8,
                min_samples_split=5,
                min_samples_leaf=4,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=42,
            )


class LogisticRegressionModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return LogisticRegression(
                max_iter=1000, C=1.0, l1_ratio=0, solver="liblinear", random_state=42
            )
        else:
            return LogisticRegression(
                max_iter=1000,
                C=0.8,
                l1_ratio=0,
                class_weight="balanced",
                solver="liblinear",
                random_state=42,
            )


class SVMModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return CalibratedClassifierCV(
                SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42), ensemble=False
            )
        else:
            return CalibratedClassifierCV(
                SVC(kernel="rbf", C=0.8, gamma="scale", class_weight="balanced", random_state=42),
                ensemble=False,
            )


def get_token_attribution(model_obj, text, sentence_model, clf):
    """Compute token-level attribution via perturbation"""
    tokens = text.split()
    y_pred_proba = clf.predict_proba(model_obj.encode(text).reshape(1, -1))[0]

    token_impacts = []
    for i, token in enumerate(tokens):
        perturbed = " ".join(tokens[:i] + tokens[i + 1 :])
        X_perturbed = sentence_model.encode(perturbed).reshape(1, -1)
        pred_perturbed = clf.predict_proba(X_perturbed)[0][1]
        impact = y_pred_proba[1] - pred_perturbed
        token_impacts.append((token, impact))

    return token_impacts, y_pred_proba


def evaluate_models(X_train, y_train, X_test, y_test, use_smote, balance):
    """Train and evaluate all models, return results and best model"""
    models = [
        XGBoostModel(use_smote, balance),
        RandomForestModel(use_smote),
        LogisticRegressionModel(use_smote),
        SVMModel(use_smote),
    ]

    best_model = None
    best_f2 = 0
    results = []

    for model_wrapper in models:
        model_wrapper.train(X_train, y_train)
        y_pred = model_wrapper.predict(X_test)
        f2 = fbeta_score(y_test, y_pred, beta=2, pos_label=1, zero_division=0)
        results.append((model_wrapper.name, f2))

        if f2 > best_f2:
            best_f2 = f2
            best_model = model_wrapper

    return results, best_model


def prepare_data(records, language):
    sentence_model = load_model(language)

    embeding_folder_path = Path(f"data/embeddings_{language}")
    embeddings_path = embeding_folder_path / Path("embeddings.npy")
    metadata_path = embeding_folder_path / Path("metadata.json")
    os.makedirs(embeding_folder_path, exist_ok=True)

    record_ids = []
    texts = []
    scores = []

    for r in records:
        record_id = hashlib.md5(f"{r['title']}".encode()).hexdigest()
        record_ids.append(record_id)
        texts.append(f"{r['title']}")
        scores.append(r["score"])

    cached_embeddings = {}
    cached_metadata = {}

    if embeddings_path.exists() and metadata_path.exists():
        try:
            cached_embeddings_array = np.load(embeddings_path)
            with open(metadata_path, "r") as f:
                cached_metadata = json.load(f)

            # Rebuild cache dictionary
            for i, (record_id, embedding) in enumerate(
                zip(cached_metadata.get("record_ids", []), cached_embeddings_array)
            ):
                cached_embeddings[record_id] = embedding

            print(f"Loaded {len(cached_embeddings)} cached embeddings")
        except Exception as e:
            print(f"Error loading cached embeddings: {e}")
            cached_embeddings = {}

    embeddings = []
    new_record_ids = []
    new_texts = []

    for record_id, text in zip(record_ids, texts):
        if record_id in cached_embeddings:
            embeddings.append(cached_embeddings[record_id])
        else:
            new_record_ids.append(record_id)
            new_texts.append(text)

    if new_texts:
        print(f"Generating embeddings for {len(new_texts)} new records...")
        new_embeddings = []
        for text in tqdm(new_texts, desc="Generating embeddings"):
            new_embeddings.append(sentence_model.encode(text))

        for record_id, embedding in zip(new_record_ids, new_embeddings):
            cached_embeddings[record_id] = embedding

    # reorder to match original record order since cache lookup is unordered
    final_embeddings = []
    for record_id in record_ids:
        final_embeddings.append(cached_embeddings[record_id])

    # Save updated cache
    embeddings_array = np.array(final_embeddings)
    cache_metadata = {"record_ids": record_ids, "num_records": len(record_ids)}

    np.save(embeddings_path, embeddings_array)
    with open(metadata_path, "w") as f:
        json.dump(cache_metadata, f)

    X = embeddings_array
    y = np.array(scores)

    return X, y, sentence_model


@lru_cache(maxsize=2)
def load_model(language):
    if language == "fr":
        return SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v2")
    elif language == "en":
        return SentenceTransformer("all-MiniLM-L6-v2")
    else:
        raise Exception(f"Language {language} is not accepted")


def train_models(nb_iter=100, language="fr", use_smote=True):
    """Train models nb_iter times and print average statistics"""
    print("Loading dataset...")
    with open(Path("data/dataset.json"), "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        return
    else:
        records = records[language]

    X, y, _ = prepare_data(records, language)

    all_results = {
        name: []
        for name in ["XGBoostModel", "RandomForestModel", "LogisticRegressionModel", "SVMModel"]
    }

    for _ in tqdm(range(nb_iter), desc="Training iterations"):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        if use_smote:
            X_train, y_train = SMOTE().fit_resample(X_train, y_train)

        balance = np.sum(y_train == 0) / np.sum(y_train == 1)
        results, _ = evaluate_models(X_train, y_train, X_test, y_test, use_smote, balance)

        for name, f2 in results:
            all_results[name].append(f2)

    print("\n~~~~~ Average F2 scores over", nb_iter, "iterations ~~~~~")
    avg_results = [
        (name, np.mean(scores), np.std(scores) / np.sqrt(len(scores)))
        for name, scores in all_results.items()
    ]
    avg_results.sort(key=lambda x: x[1], reverse=True)

    for name, avg, std in avg_results:
        print(f"{name:30} : {avg * 100:.1f}% ± {std * 100:.1f}%")


def _dataset_hash(records: list) -> str:
    return hashlib.md5(json.dumps(records, sort_keys=True).encode()).hexdigest()


def _score_titles(clf, sentence_model, titles):
    embeddings = np.array([sentence_model.encode(title) for title in titles])
    scores = clf.predict_proba(embeddings)[:, 1]
    for i, score in enumerate(scores):
        if score > SCORE_THRESHOLD:
            return titles[i]
    return titles[scores.argmax()]


def choose_title(titles, language, use_smote=True):
    """Pick the best article title using a trained classifier, retrained only when data changes."""
    with open(Path("data/dataset.json"), "r", encoding="utf-8") as f:
        records = json.load(f)

    records = records.get(language, []) if records else []

    nb_pos = sum(1 for r in records if r["score"])
    nb_neg = sum(1 for r in records if not r["score"])
    if nb_pos < 6 or nb_neg < 6:
        print("Not enough data in dataset: taking best article by views")
        return titles[0]

    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    clf_path = models_dir / f"classifier_{language}.joblib"
    hash_path = models_dir / f"classifier_{language}_hash.txt"

    current_hash = _dataset_hash(records)
    sentence_model = load_model(language)

    if clf_path.exists() and hash_path.exists() and hash_path.read_text().strip() == current_hash:
        print("Loading saved classifier...")
        clf = joblib.load(clf_path)
        return _score_titles(clf, sentence_model, titles)

    X, y, _ = prepare_data(records, language)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    if use_smote:
        X_train, y_train = SMOTE().fit_resample(X_train, y_train)

    balance = np.sum(y_train == 0) / np.sum(y_train == 1)

    print("\nTraining models...")
    results, best_model = evaluate_models(X_train, y_train, X_test, y_test, use_smote, balance)

    print("\n~~~~~ Model comparison (F2) ~~~~~")
    results.sort(key=lambda x: x[1], reverse=True)
    for name, f2 in results:
        print(f"{name:30} : {f2 * 100:.1f}%")

    print(f"\n~~~~~ Best model: {best_model.name} ~~~~~")
    print(
        classification_report(
            y_test,
            best_model.predict(X_test),
            labels=[1, 0],
            target_names=["Good", "Bad"],
            zero_division=0,
        )
    )

    joblib.dump(best_model.model, clf_path)
    hash_path.write_text(current_hash)

    return _score_titles(best_model.model, sentence_model, titles)
