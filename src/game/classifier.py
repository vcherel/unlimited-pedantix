from sklearn.metrics import classification_report, fbeta_score
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
from abc import ABC, abstractmethod
from sklearn.svm import SVC
from pathlib import Path
import xgboost as xgb
from tqdm import tqdm
import numpy as np
import hashlib
import json
import os


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
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=3,
                reg_lambda=1.0,
            )
        else:
            return xgb.XGBClassifier(n_estimators=100, max_depth=5, scale_pos_weight=self.scale)


class RandomForestModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return RandomForestClassifier(
                n_estimators=300,
                max_depth=8,
                min_samples_leaf=4,
            )
        else:
            return RandomForestClassifier(n_estimators=100, max_depth=10, class_weight="balanced")


class LogisticRegressionModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return LogisticRegression(max_iter=2000, C=0.5)
        else:
            return LogisticRegression(max_iter=1000, class_weight="balanced")


class SVMModel(BaseModel):
    def create_model(self):
        if self.use_smote:
            return SVC(kernel='rbf', probability=True)
        else:
            return SVC(kernel='rbf', probability=True, class_weight="balanced")


def get_token_attribution(model_obj, text, sentence_model, clf):
    """Compute token-level attribution via perturbation"""
    tokens = text.split()
    y_pred_proba = clf.predict_proba(model_obj.encode(text).reshape(1, -1))[0]
    
    token_impacts = []
    for i, token in enumerate(tokens):
        perturbed = ' '.join(tokens[:i] + tokens[i+1:])
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
        SVMModel(use_smote)
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

def prepare_data(records, sentence_model):
    """Load embeddings or generate them, return X and y"""
    embeding_folder_path = Path("output/embeddings")
    embeddings_path = embeding_folder_path / Path("embeddings.npy")
    metadata_path = embeding_folder_path / Path("metadata.json")
    os.makedirs(embeding_folder_path, exist_ok=True)

    # Create identifiers for each record
    record_ids = []
    texts = []
    scores = []

    for r in records:
        record_id = hashlib.md5(
            f"{r['title']}".encode()
        ).hexdigest()
        record_ids.append(record_id)
        texts.append(f"{r['title']}")
        scores.append(r['score'])

    cached_embeddings = {}
    cached_metadata = {}
    
    # Load existing cached embeddings
    if embeddings_path.exists() and metadata_path.exists():
        try:
            cached_embeddings_array = np.load(embeddings_path)
            with open(metadata_path, 'r') as f:
                cached_metadata = json.load(f)
            
            # Rebuild cache dictionary
            for i, (record_id, embedding) in enumerate(
                zip(cached_metadata.get('record_ids', []), cached_embeddings_array)
            ):
                cached_embeddings[record_id] = embedding
                
            print(f"Loaded {len(cached_embeddings)} cached embeddings")
        except Exception as e:
            print(f"Error loading cached embeddings: {e}")
            cached_embeddings = {}

    # Generate embeddings for new records
    embeddings = []
    new_record_ids = []
    new_texts = []
    
    for record_id, text in zip(record_ids, texts):
        if record_id in cached_embeddings:
            embeddings.append(cached_embeddings[record_id])
        else:
            new_record_ids.append(record_id)
            new_texts.append(text)

    # Generate embeddings for new records
    if new_texts:
        print(f"Generating embeddings for {len(new_texts)} new records...")
        new_embeddings = []
        for text in tqdm(new_texts, desc="Generating embeddings"):
            new_embeddings.append(sentence_model.encode(text))
        
        # Add new embeddings to cache
        for record_id, embedding in zip(new_record_ids, new_embeddings):
            cached_embeddings[record_id] = embedding

    # Reorder all embeddings to match original order
    final_embeddings = []
    for record_id in record_ids:
        final_embeddings.append(cached_embeddings[record_id])

    # Save updated cache
    embeddings_array = np.array(final_embeddings)
    cache_metadata = {
        'record_ids': record_ids,
        'num_records': len(record_ids)
    }
    
    np.save(embeddings_path, embeddings_array)
    with open(metadata_path, 'w') as f:
        json.dump(cache_metadata, f)
    
    X = embeddings_array
    y = np.array(scores)
    return X, y

def train_models(nb_iter=100, language='fr', use_smote=True):
    """Train models nb_iter times and print average statistics"""
    print("Loading dataset...")
    with open(Path("output/dataset.json"), 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    if not records:
        return
    else:
        records = records[language]
    
    sentence_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    X, y = prepare_data(records, sentence_model)
    
    all_results = {name: [] for name in ['XGBoostModel', 'RandomForestModel', 'LogisticRegressionModel', 'SVMModel']}
    
    for _ in tqdm(range(nb_iter), desc="Training iterations"):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        if use_smote:
            X_train, y_train = SMOTE().fit_resample(X_train, y_train)
        
        balance = np.sum(y_train == 0) / np.sum(y_train == 1)
        results, _ = evaluate_models(X_train, y_train, X_test, y_test, use_smote, balance)
        
        for name, f2 in results:
            all_results[name].append(f2)
    
    print("\n~~~~~ Average F2 scores over", nb_iter, "iterations ~~~~~")
    avg_results = [(name, np.mean(scores), np.std(scores) / np.sqrt(len(scores))) for name, scores in all_results.items()]
    avg_results.sort(key=lambda x: x[1], reverse=True)
    
    for name, avg, std in avg_results:
        print(f"{name:30} : {avg * 100:.1f}% ± {std * 100:.1f}%")

def choose_title(titles, language, use_smote=True):
    """Train models, pick the best one, show one example, score the results"""
    print("\nLoading dataset...")
    with open(Path("output/dataset.json"), 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    if not records:
        return
    else:
        records = records[language]
    
    nb_pos = sum(1 for r in records if r['score'])
    nb_neg = sum(1 for r in records if not r['score'])
    if nb_pos < 6 or nb_neg < 6:
        print("Warning: Not enough data in the dataset: taking best one")
        return titles[0]
    
    sentence_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    X, y = prepare_data(records, sentence_model)
    
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
    y_pred = best_model.predict(X_test)
    print(classification_report(y_test, y_pred, labels=[1, 0], target_names=['Good', 'Bad'], zero_division=0))
    
    # Score titles and select best one
    embeddings = np.array([sentence_model.encode(title) for title in titles])
    new_scores = best_model.predict_proba(embeddings)[:, 1]

    return titles[new_scores.argmax()]
