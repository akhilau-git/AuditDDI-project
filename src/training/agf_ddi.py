#!/usr/bin/env python
"""AGF-DDI: Auditable Graph-Fingerprint framework for cold-start DDI prediction.

Run on the SAME frozen AuditDDI split CSVs (transductive_train, validation,
transductive_test, s1_dev, s2_dev, s1_test, s2_test).  Nothing from a dev/test
split is ever used to build features or to fit a model, except that dev splits
are used for early stopping / threshold choice (as in the project protocol).

Idea
----
Every drug gets a *graph fingerprint* made of three label-free / train-only parts:

1. Structural + biological fingerprints -> drug-drug similarity graphs
   (ECFP, atom-pair, MACCS, and the PharmGKB/openFDA/target/... source matrix).
2. Interaction-graph topology from TRAIN positives only (common neighbours,
   Adamic-Adar, resource allocation, spectral link score, degree).
3. Analog transfer: a cold drug "borrows" the known interaction partners of its
   most similar known drugs:  M[a,b] = sum_{a',b'} w(a,a') A[a',b'] w(b,b').
   Each score is therefore traceable to named analog drug pairs (auditable).

A gradient-boosted head is trained per regime (transductive / S2 / S1).  Cold
regimes are trained with DRUG-FOLD MASKING: the edges of the simulated-cold drugs
are removed from the graph before their features are computed, so the training
features look exactly like the features at S1/S2 test time (no label leakage).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import (average_precision_score, f1_score,
                             matthews_corrcoef, roc_auc_score)

warnings.filterwarnings("ignore")

SPLIT_NAMES = ("transductive_train", "validation", "transductive_test",
               "s1_dev", "s2_dev", "s1_test", "s2_test")
EVAL_SPLITS = {"trans": ("transductive_test",),
               "s2": ("s2_dev", "s2_test"),
               "s1": ("s1_dev", "s1_test")}
GROUPS = ("analog_transfer", "graph_topology", "chem_pair", "bio_pair")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------
def load_splits(split_dir: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for name in SPLIT_NAMES:
        p = split_dir / f"{name}.csv"
        if not p.is_file():
            raise FileNotFoundError(f"Missing frozen split file: {p}")
        df = pd.read_csv(p, usecols=["source", "target", "label"])
        df["source"] = df["source"].astype(str)
        df["target"] = df["target"].astype(str)
        df["label"] = df["label"].astype(np.float32)
        out[name] = df
    return out


def pair_keys(df: pd.DataFrame) -> set[tuple[str, str]]:
    a, b = df["source"].to_numpy(), df["target"].to_numpy()
    return {(x, y) if x <= y else (y, x) for x, y in zip(a, b)}


def leakage_audit(splits: dict[str, pd.DataFrame]) -> dict:
    """Hard checks that the evaluation protocol is leak-free."""
    seen = set(splits["transductive_train"][["source", "target"]].to_numpy().ravel())
    seen |= set(splits["validation"][["source", "target"]].to_numpy().ravel())
    fit_keys = pair_keys(splits["transductive_train"]) | pair_keys(splits["validation"])
    report = {"n_seen_drugs": len(seen)}
    for name in ("transductive_test", "s1_dev", "s2_dev", "s1_test", "s2_test"):
        df = splits[name]
        ov = len(pair_keys(df) & fit_keys)
        in_a = df["source"].isin(seen).to_numpy()
        in_b = df["target"].isin(seen).to_numpy()
        n_seen_endpoints = in_a.astype(int) + in_b.astype(int)
        expect = {"transductive_test": 2, "s1_dev": 0, "s1_test": 0,
                  "s2_dev": 1, "s2_test": 1}[name]
        ok = bool((n_seen_endpoints == expect).all())
        report[name] = {"rows": len(df), "pairs_overlapping_fit_pairs": ov,
                        "seen_endpoint_rule_ok": ok, "expected_seen_endpoints": expect}
        if ov or not ok:
            raise RuntimeError(f"Leakage/protocol violation in {name}: {report[name]}")
    return report


# ----------------------------------------------------------------------------
# Drug representations
# ----------------------------------------------------------------------------
def rdkit_fingerprints(smiles: list[str]) -> dict[str, np.ndarray]:
    from rdkit import Chem, DataStructs, RDLogger
    from rdkit.Chem import MACCSkeys, rdFingerprintGenerator
    RDLogger.DisableLog("rdApp.*")
    morgan = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    apair = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=2048)
    n = len(smiles)
    ecfp = np.zeros((n, 2048), np.float32)
    ap = np.zeros((n, 2048), np.float32)
    maccs = np.zeros((n, 167), np.float32)
    bad = 0
    for i, s in enumerate(smiles):
        m = Chem.MolFromSmiles(s)
        if m is None:
            bad += 1
            continue
        ecfp[i] = morgan.GetFingerprintAsNumPy(m)
        ap[i] = apair.GetFingerprintAsNumPy(m)
        arr = np.zeros((167,), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(MACCSkeys.GenMACCSKeys(m), arr)
        maccs[i] = arr
    if bad:
        log(f"WARNING: {bad} SMILES could not be parsed by RDKit (zero fingerprint).")
    return {"ecfp": ecfp, "atompair": ap, "maccs": maccs}


def table_fingerprints(path: Path, smiles: list[str]) -> dict[str, np.ndarray]:
    """Alternative to RDKit: npz with canonical_smiles + one or more 2-D arrays."""
    with np.load(path, allow_pickle=False) as z:
        key = z["canonical_smiles"].astype(str)
        row = {s: i for i, s in enumerate(key)}
        out = {}
        for name in z.files:
            if name == "canonical_smiles":
                continue
            arr = z[name].astype(np.float32)
            m = np.zeros((len(smiles), arr.shape[1]), np.float32)
            for i, s in enumerate(smiles):
                j = row.get(s)
                if j is not None:
                    m[i] = arr[j]
            out[name] = m
    return out


def _align(keys, mat, smiles, label):
    row = {k: i for i, k in enumerate(keys)}
    out = np.zeros((len(smiles), mat.shape[1]), np.float32)
    hit = 0
    for i, sm in enumerate(smiles):
        j = row.get(sm)
        if j is not None:
            out[i] = mat[j]
            hit += 1
    log(f"  {label}: matched {hit}/{len(smiles)} drugs, {mat.shape[1]} columns")
    if hit < 0.2 * len(smiles):
        log(f"  WARNING: {label} matches <20% of drugs - check that its canonical_smiles "
            f"column uses the same SMILES as the split files.")
    keep = [j for j in range(mat.shape[1]) if out[:, j].std() > 0]
    return out[:, keep]


def load_feature_source(path: Path, smiles: list[str]) -> dict[str, np.ndarray]:
    """Return {view_name: (n_drugs, d) matrix}.  Accepts
    (a) per-branch CSV: canonical_smiles + numeric columns (drug_profile.csv, adverse_event.csv, ...)
    (b) seven-branch bundle npz: <branch>_features / <branch>_mask arrays
    (c) legacy source_feature_matrix.npz: canonical_smiles / features / feature_names
    """
    out: dict[str, np.ndarray] = {}
    stem = path.stem
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        if "canonical_smiles" not in df.columns:
            log(f"  skipped {path.name}: no canonical_smiles column")
            return out
        df = df.drop_duplicates("canonical_smiles")
        num = df.drop(columns=["canonical_smiles"]).apply(pd.to_numeric, errors="coerce")
        num = num.loc[:, num.notna().any()].fillna(0.0)
        m = _align(df["canonical_smiles"].astype(str).to_numpy(), num.to_numpy(np.float32), smiles, path.name)
        if m.shape[1]:
            out[f"bio_{stem}"] = m
    else:
        with np.load(path, allow_pickle=False) as z:
            key = z["canonical_smiles"].astype(str)
            if "features" in z.files:                       # legacy format
                feats = z["features"].astype(np.float32)
                names = z["feature_names"].astype(str).tolist() if "feature_names" in z.files else []
                keep = [j for j in range(feats.shape[1])
                        if not (names and names[j].startswith(("availability:", "faers:")))]
                m = _align(key, feats[:, keep], smiles, path.name)
                if m.shape[1]:
                    out[f"bio_{stem}"] = m
            for name in z.files:                            # bundle format
                if name.endswith("_features"):
                    br = name[: -len("_features")]
                    mat = z[name].astype(np.float32)
                    mk = z[f"{br}_mask"].astype(bool) if f"{br}_mask" in z.files else np.ones(len(key), bool)
                    m = _align(key[mk], mat[mk], smiles, f"{path.name}:{br}")
                    if m.shape[1]:
                        out[f"bio_{br}"] = m
    return out


def discover_sources(data_base: str | None) -> list[Path]:
    """Find the per-source feature tables your preparation scripts write to Drive."""
    if not data_base:
        return []
    base = Path(data_base) / "processed"
    cands = [base / "seven_branch" / f for f in
             ("drug_profile.csv", "adverse_event.csv", "protein_target.csv",
              "pdb_structure.csv", "gene_expression.csv")]
    cands += [base / "seven_branch" / "seven_branch_bundle.npz",
              base / "auditddi_v2" / "source_feature_matrix.npz"]
    found = [c for c in cands if c.is_file()]
    log("Auto-discovered feature sources: " + (", ".join(str(c.relative_to(base)) for c in found) or "none"))
    return found


def tanimoto(X: np.ndarray) -> np.ndarray:
    Xb = (X > 0).astype(np.float32)
    inter = Xb @ Xb.T
    s = Xb.sum(1)
    sim = inter / np.maximum(s[:, None] + s[None, :] - inter, 1e-6)
    sim[(s[:, None] == 0) | (s[None, :] == 0)] = 0.0
    np.fill_diagonal(sim, 0.0)
    return sim.astype(np.float32)


def cosine(X: np.ndarray) -> np.ndarray:
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    Xn = X / np.maximum(nrm, 1e-8)
    sim = np.clip(Xn @ Xn.T, 0, 1)
    sim[(nrm[:, 0] == 0)[:, None] | (nrm[:, 0] == 0)[None, :]] = 0.0
    np.fill_diagonal(sim, 0.0)
    return sim.astype(np.float32)


class DrugSpace:
    """Label-free drug similarity graphs and low-dimensional embeddings."""

    def __init__(self, smiles, fps, bio_blocks, emb_dim=12, bio_dim=8, seed=0):
        self.smiles = smiles
        self.n = len(smiles)
        self.sims: dict[str, np.ndarray] = {}
        self.bio_views: set[str] = set()
        for name, X in fps.items():
            self.sims[name] = tanimoto(X)
        for name, X in bio_blocks.items():
            self.sims[name] = cosine(X)
            self.bio_views.add(name)
        chem = [self.sims[k] for k in self.sims if k not in self.bio_views]
        self.sims["combo"] = np.mean(list(self.sims.values()), axis=0).astype(np.float32)
        self.sims["chem_combo"] = np.mean(chem, axis=0).astype(np.float32) if chem else self.sims["combo"]
        self.emb = self._embed(fps.get("ecfp", next(iter(fps.values()))), emb_dim, seed)
        bio_all = [X for X in bio_blocks.values()]
        self.bio_emb = (self._embed(np.hstack(bio_all), bio_dim, seed)
                        if bio_all else np.zeros((self.n, 0), np.float32))

    @staticmethod
    def _embed(X, d, seed):
        d = max(1, min(d, X.shape[1] - 1))
        Z = TruncatedSVD(d, random_state=seed).fit_transform(X.astype(np.float32))
        Z = (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-6)
        return Z.astype(np.float32)


# ----------------------------------------------------------------------------
# Graph helpers
# ----------------------------------------------------------------------------
def adjacency(df: pd.DataFrame, idx: dict[str, int], n: int) -> np.ndarray:
    pos = df[df["label"] > 0.5]
    a = pos["source"].map(idx).to_numpy()
    b = pos["target"].map(idx).to_numpy()
    A = np.zeros((n, n), np.float32)
    A[a, b] = 1.0
    A[b, a] = 1.0
    np.fill_diagonal(A, 0.0)
    return A


def knn_weights(S: np.ndarray, pool: np.ndarray, k: int, power: float = 2.0):
    """Sparse row-normalised top-k analog weights restricted to known drugs."""
    n = S.shape[0]
    M = np.where(pool[None, :], S, -1.0)
    np.fill_diagonal(M, -1.0)
    kk = int(max(1, min(k, pool.sum() - 1)))
    idx = np.argpartition(-M, kk - 1, axis=1)[:, :kk]
    raw = np.clip(np.take_along_axis(M, idx, 1), 0, None)
    w = raw ** power
    rs = w.sum(1, keepdims=True)
    w = np.where(rs > 0, w / np.maximum(rs, 1e-12), 0.0)
    W = sp.csr_matrix((w.ravel().astype(np.float32),
                       (np.repeat(np.arange(n), kk), idx.ravel())), shape=(n, n))
    return W, raw.mean(1)


def pair_features(A: np.ndarray, ai: np.ndarray, bi: np.ndarray, space: DrugSpace,
                  ks=(10, 30), ranks=(16, 48)) -> tuple[np.ndarray, list[str], list[str]]:
    """All symmetric pair features for graph A (dense, symmetric, zero diagonal)."""
    F: dict[str, np.ndarray] = {}
    G: dict[str, str] = {}
    # canonical order => features are exactly invariant to the order of the two drugs
    ai, bi = np.minimum(ai, bi), np.maximum(ai, bi)

    def add(name, arr, grp):
        F[name] = np.asarray(arr, np.float32)
        G[name] = grp

    deg = A.sum(1)
    logd = np.log1p(deg)
    pool = deg > 0
    la, lb = logd[ai], logd[bi]

    # ---- graph topology (train positives only) -----------------------------
    add("deg_min", np.minimum(la, lb), "graph_topology")
    add("deg_max", np.maximum(la, lb), "graph_topology")
    add("known_cnt", pool[ai].astype(int) + pool[bi].astype(int), "graph_topology")
    CN = A @ A
    add("cn_log", np.log1p(CN[ai, bi]), "graph_topology")
    add("cn_norm", CN[ai, bi] / np.sqrt((deg[ai] + 1) * (deg[bi] + 1)), "graph_topology")
    add("jaccard", CN[ai, bi] / np.maximum(deg[ai] + deg[bi] - CN[ai, bi], 1.0), "graph_topology")
    AA = (A * (1.0 / np.log(2.0 + deg))[None, :]) @ A
    add("adamic_adar", AA[ai, bi], "graph_topology")
    RA = (A * (1.0 / (1.0 + deg))[None, :]) @ A
    add("resource_alloc", RA[ai, bi], "graph_topology")
    P3 = CN @ A
    add("path3_norm", P3[ai, bi] / np.sqrt((deg[ai] + 1) * (deg[bi] + 1)) / 10.0, "graph_topology")
    del AA, RA, P3
    dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
    An = (A * dinv[:, None] * dinv[None, :]).astype(np.float64)
    w, V = np.linalg.eigh(An)
    order = np.argsort(-np.abs(w))[:max(ranks)]
    w, V = w[order], V[:, order]
    for r in ranks:
        add(f"spectral_r{r}", ((V[ai, :r] * V[bi, :r]) * w[:r]).sum(1), "graph_topology")
    del CN, An, V

    # ---- analog transfer ---------------------------------------------------
    for view, S in space.sims.items():
        if view == "chem_combo":
            continue
        for k in ks:
            W, conf = knn_weights(S, pool, k)
            WA = W @ A                      # (n, n) dense: analogs' partners
            M = W @ WA.T                    # W A W^T (symmetric)
            o1, o2 = WA[ai, bi], WA[bi, ai]
            add(f"{view}_k{k}_M", M[ai, bi], "analog_transfer")
            add(f"{view}_k{k}_omax", np.maximum(o1, o2), "analog_transfer")
            add(f"{view}_k{k}_omin", np.minimum(o1, o2), "analog_transfer")
            if k == ks[0] and view in ("combo", "ecfp"):
                add(f"{view}_conf_min", np.minimum(conf[ai], conf[bi]), "analog_transfer")
                add(f"{view}_conf_max", np.maximum(conf[ai], conf[bi]), "analog_transfer")
            if k == ks[0] and view == "combo":
                kd = W @ logd
                kda = np.where(pool, logd, kd)   # observed degree if known else analog estimate
                add("kdeg_min", np.minimum(kda[ai], kda[bi]), "analog_transfer")
                add("kdeg_max", np.maximum(kda[ai], kda[bi]), "analog_transfer")
            del W, WA, M

    # ---- pairwise chemistry / biology -------------------------------------
    for view, S in space.sims.items():
        grp = "bio_pair" if view in space.bio_views else "chem_pair"
        if view in ("combo", "chem_combo"):
            grp = "chem_pair"
        add(f"sim_{view}", S[ai, bi], grp)
    E = space.emb
    for j in range(E.shape[1]):
        add(f"emb{j}_sum", E[ai, j] + E[bi, j], "chem_pair")
        add(f"emb{j}_prod", E[ai, j] * E[bi, j], "chem_pair")
    B = space.bio_emb
    for j in range(B.shape[1]):
        add(f"bio{j}_sum", B[ai, j] + B[bi, j], "bio_pair")
        add(f"bio{j}_prod", B[ai, j] * B[bi, j], "bio_pair")

    names = list(F)
    return np.column_stack([F[k] for k in names]), names, [G[k] for k in names]


# ----------------------------------------------------------------------------
# Training-matrix construction (leak-free simulated regimes)
# ----------------------------------------------------------------------------
def build_trans_matrix(train, A_tr, idx, space, n_folds, seed):
    n = space.n
    a = train["source"].map(idx).to_numpy()
    b = train["target"].map(idx).to_numpy()
    y = train["label"].to_numpy()
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, n_folds, size=len(train))
    X = None
    for f in range(n_folds):
        m = fold == f
        Af = A_tr.copy()
        pos = m & (y > 0.5)
        Af[a[pos], b[pos]] = 0.0
        Af[b[pos], a[pos]] = 0.0
        Xf, names, groups = pair_features(Af, a[m], b[m], space)
        if X is None:
            X = np.zeros((len(train), Xf.shape[1]), np.float32)
        X[m] = Xf
        log(f"  trans OOF fold {f + 1}/{n_folds}")
    return X, y, names, groups


def build_cold_matrix(L, A_L, idx, space, regime, n_drug_folds, seed):
    n = space.n
    a = L["source"].map(idx).to_numpy()
    b = L["target"].map(idx).to_numpy()
    y = L["label"].to_numpy()
    rng = np.random.default_rng(seed)
    drugs = np.unique(np.concatenate([a, b]))
    fold_of = np.full(n, -1)
    fold_of[drugs] = rng.integers(0, n_drug_folds, size=len(drugs))
    fa, fb = fold_of[a], fold_of[b]
    X, keep = None, np.zeros(len(L), bool)
    names = groups = None
    if regime == "s2":
        cold_is_a = rng.random(len(L)) < 0.5
        ca = np.where(cold_is_a, a, b)
        oa = np.where(cold_is_a, b, a)
        fc, fo = fold_of[ca], fold_of[oa]
        keep = fc != fo
        keys = [(f,) for f in range(n_drug_folds)]
        sel = lambda key: keep & (fc == key[0])
        mask_folds = lambda key: {key[0]}
        pa_, pb_ = ca, oa
    else:  # s1: both endpoints cold
        keep = np.ones(len(L), bool)
        lo, hi = np.minimum(fa, fb), np.maximum(fa, fb)
        keys = [(i, j) for i in range(n_drug_folds) for j in range(i, n_drug_folds)]
        sel = lambda key: (lo == key[0]) & (hi == key[1])
        mask_folds = lambda key: {key[0], key[1]}
        pa_, pb_ = a, b
    out_rows = []
    for t, key in enumerate(keys):
        m = sel(key)
        if not m.any():
            continue
        cold = np.isin(fold_of, list(mask_folds(key)))
        Af = A_L.copy()
        Af[cold, :] = 0.0
        Af[:, cold] = 0.0
        Xf, names, groups = pair_features(Af, pa_[m], pb_[m], space)
        out_rows.append((np.where(m)[0], Xf))
        if (t + 1) % 5 == 0 or t + 1 == len(keys):
            log(f"  {regime} masked-episode {t + 1}/{len(keys)}")
    n_rows = sum(len(r) for r, _ in out_rows)
    X = np.zeros((n_rows, len(names)), np.float32)
    yy = np.zeros(n_rows, np.float32)
    pos = 0
    for rows, Xf in out_rows:
        X[pos:pos + len(rows)] = Xf
        yy[pos:pos + len(rows)] = y[rows]
        pos += len(rows)
    return X, yy, names, groups


# ----------------------------------------------------------------------------
# Gradient-boosted head
# ----------------------------------------------------------------------------
class Booster:
    def __init__(self, seed=0, fast=False, n_jobs=-1):
        self.seed, self.fast, self.n_jobs = seed, fast, n_jobs
        self.kind = None

    def fit(self, X, y, Xv, yv):
        try:
            import lightgbm as lgb
            self.kind = "lgb"
            p = dict(objective="binary", learning_rate=0.1 if self.fast else 0.03,
                     num_leaves=63, min_child_samples=40, feature_fraction=0.7,
                     bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
                     seed=self.seed, verbose=-1, num_threads=max(self.n_jobs, 0))
            dtr = lgb.Dataset(X, y)
            dva = lgb.Dataset(Xv, yv, reference=dtr)
            self.m = lgb.train(p, dtr, num_boost_round=600 if self.fast else 4000,
                               valid_sets=[dva],
                               callbacks=[lgb.early_stopping(150, verbose=False)])
            self.best = self.m.best_iteration
        except ImportError:
            from sklearn.ensemble import HistGradientBoostingClassifier
            self.kind = "hgb"
            self.m = HistGradientBoostingClassifier(
                max_iter=250 if self.fast else 500, learning_rate=0.08,
                max_leaf_nodes=48, min_samples_leaf=40, l2_regularization=5.0,
                early_stopping=False, random_state=self.seed).fit(X, y)
            best, best_auc = 1, -1
            for i, pr in enumerate(self.m.staged_predict_proba(Xv), 1):
                if i % 10 == 0:
                    auc = roc_auc_score(yv, pr[:, 1])
                    if auc > best_auc:
                        best, best_auc = i, auc
            self.best = best
        return self

    def predict(self, X):
        if self.kind == "lgb":
            return self.m.predict(X, num_iteration=self.best)
        for i, pr in enumerate(self.m.staged_predict_proba(X), 1):
            if i == self.best:
                return pr[:, 1]
        return self.m.predict_proba(X)[:, 1]

    def contributions(self, X):
        if self.kind != "lgb":
            return None
        return self.m.predict(X, num_iteration=self.best, pred_contrib=True)


def fit_ensemble(X, y, Xv, yv, seeds, fast=False, n_jobs=-1):
    return [Booster(seed=s, fast=fast, n_jobs=n_jobs).fit(X, y, Xv, yv) for s in seeds]


def ens_predict(models, X):
    return np.mean([m.predict(X) for m in models], axis=0)


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def pick_threshold(y, p):
    """Youden-J threshold chosen on a dev/validation split only."""
    qs = np.unique(np.quantile(p, np.linspace(0.02, 0.98, 97)))
    best, bt = -1, 0.5
    for t in qs:
        pred = p >= t
        tpr = (pred & (y > 0.5)).sum() / max((y > 0.5).sum(), 1)
        fpr = (pred & (y < 0.5)).sum() / max((y < 0.5).sum(), 1)
        if tpr - fpr > best:
            best, bt = tpr - fpr, float(t)
    return bt


def metrics(y, p, thr):
    pred = (p >= thr).astype(int)
    return {"auroc": float(roc_auc_score(y, p)), "auprc": float(average_precision_score(y, p)),
            "accuracy": float((pred == (y > 0.5)).mean()), "f1": float(f1_score(y, pred)),
            "mcc": float(matthews_corrcoef(y > 0.5, pred)), "n": int(len(y)),
            "n_pos": int((y > 0.5).sum())}


# ----------------------------------------------------------------------------
# Audit evidence (why was this pair scored high?)
# ----------------------------------------------------------------------------
def explain(A, space, ai, bi, names, k=10, top=5):
    deg = A.sum(1)
    pool = deg > 0
    W, _ = knn_weights(space.sims["combo"], pool, k)
    W = W.tocsr()
    ev = []
    for a, b in zip(ai, bi):
        ra, rb = W[a], W[b]
        pairs = []
        for ja, wa in zip(ra.indices, ra.data):
            for jb, wb in zip(rb.indices, rb.data):
                if A[ja, jb] > 0 and ja != jb:
                    pairs.append((float(wa * wb), int(ja), int(jb)))
        pairs.sort(reverse=True)
        ev.append({
            "drug_a": space.smiles[a], "drug_b": space.smiles[b],
            "analogs_a": [(space.smiles[j], round(float(w), 3)) for j, w in
                          sorted(zip(ra.indices, ra.data), key=lambda t: -t[1])[:3]],
            "analogs_b": [(space.smiles[j], round(float(w), 3)) for j, w in
                          sorted(zip(rb.indices, rb.data), key=lambda t: -t[1])[:3]],
            "supporting_known_pairs": [
                {"analog_of_a": space.smiles[ja], "analog_of_b": space.smiles[jb],
                 "weight": round(w, 4)} for w, ja, jb in pairs[:top]],
            "n_supporting_known_pairs": len(pairs)})
    return ev


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits_dir", default=os.environ.get("AUDITDDI_FIXED_PAIR_SPLITS_DIR"))
    ap.add_argument("--data_base", default=os.environ.get("AUDITDDI_DATA_BASE"))
    ap.add_argument("--out_dir", default="agf_ddi_results")
    ap.add_argument("--bio_npz", nargs="*", default=None,
                    help="feature tables (csv with canonical_smiles + numeric columns, or npz). "
                         "Default: auto-discover in <data_base>/processed/seven_branch and auditddi_v2")
    ap.add_argument("--fp_table", default=None, help="npz fingerprints instead of RDKit")
    ap.add_argument("--names_csv", default=None, help="csv with smiles,names columns (optional)")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--trans_folds", type=int, default=8)
    ap.add_argument("--drug_folds", type=int, default=8)
    ap.add_argument("--ablate", action="store_true")
    ap.add_argument("--explain_top", type=int, default=50)
    ap.add_argument("--fast", action="store_true", help="quick smoke run")
    ap.add_argument("--n_jobs", type=int, default=-1)
    args = ap.parse_args(argv)
    if not args.splits_dir:
        sys.exit("Provide --splits_dir (or set AUDITDDI_FIXED_PAIR_SPLITS_DIR).")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    log("Loading frozen splits ...")
    splits = load_splits(Path(args.splits_dir))
    audit = leakage_audit(splits)
    log(f"Leakage audit passed: {json.dumps({k: v for k, v in audit.items() if k != 'n_seen_drugs'})}")

    smiles = sorted(set(np.concatenate([df[["source", "target"]].to_numpy().ravel()
                                        for df in splits.values()])))
    idx = {s: i for i, s in enumerate(smiles)}
    n = len(smiles)
    log(f"{n} drugs")

    log("Computing fingerprints ...")
    fps = table_fingerprints(Path(args.fp_table), smiles) if args.fp_table else rdkit_fingerprints(smiles)

    bio_paths = [Path(p) for p in args.bio_npz] if args.bio_npz else discover_sources(args.data_base)
    bio_blocks = {}
    for p in bio_paths:
        if p.is_file():
            bio_blocks.update(load_feature_source(p, smiles))
        else:
            log(f"  not found: {p}")
    log(f"Biology/source views used: {list(bio_blocks)}")
    if not bio_blocks:
        log("NOTE: no biological feature matrix found; running chemistry + graph only.")
    space = DrugSpace(smiles, fps, bio_blocks)

    train, val = splits["transductive_train"], splits["validation"]
    L = pd.concat([train, val], ignore_index=True)
    A_tr, A_L = adjacency(train, idx, n), adjacency(L, idx, n)
    for name in ("transductive_test", "s1_dev", "s2_dev", "s1_test", "s2_test"):
        d = splits[name]
        ab = A_L[d["source"].map(idx).to_numpy(), d["target"].map(idx).to_numpy()]
        assert (ab[d["label"].to_numpy() > 0.5] == 0).all(), f"{name} positives are inside the graph!"
    seeds = list(range(args.seeds))

    results, preds_all, importance, ablation = {}, [], {}, []
    heads = {}
    for regime in ("trans", "s2", "s1"):
        log(f"=== Regime: {regime} ===")
        if regime == "trans":
            X, y, names, groups = build_trans_matrix(train, A_tr, idx, space, args.trans_folds, 7)
            va = val
            Xv, _, _ = pair_features(A_tr, va["source"].map(idx).to_numpy(),
                                     va["target"].map(idx).to_numpy(), space)
            yv = va["label"].to_numpy()
            thr_split = "validation"
        else:
            X, y, names, groups = build_cold_matrix(L, A_L, idx, space, regime, args.drug_folds, 11)
            dev = splits[f"{regime}_dev"]
            Xv, _, _ = pair_features(A_L, dev["source"].map(idx).to_numpy(),
                                     dev["target"].map(idx).to_numpy(), space)
            yv = dev["label"].to_numpy()
            thr_split = f"{regime}_dev"
        log(f"  training matrix {X.shape}, positives {int(y.sum())}")
        models = fit_ensemble(X, y, Xv, yv, seeds, args.fast, args.n_jobs)
        thr = pick_threshold(yv, ens_predict(models, Xv))
        heads[regime] = (models, names, groups)
        log(f"  early-stop/threshold split: {thr_split}; best iters "
            f"{[getattr(m, 'best', None) for m in models]}")

        for split in EVAL_SPLITS[regime]:
            d = splits[split]
            ai, bi = d["source"].map(idx).to_numpy(), d["target"].map(idx).to_numpy()
            Xt, _, _ = pair_features(A_L, ai, bi, space)
            p = ens_predict(models, Xt)
            # symmetry self-check (swapping drug order must not change the score)
            Xs, _, _ = pair_features(A_L, bi[:200], ai[:200], space)
            assert np.allclose(ens_predict(models, Xs), p[:200], atol=1e-5), "order-dependence"
            results[split] = metrics(d["label"].to_numpy(), p, thr)
            results[split]["regime"] = regime
            results[split]["threshold_from"] = thr_split
            log(f"  {split:18s} AUROC {results[split]['auroc']:.4f}  "
                f"ACC {results[split]['accuracy']:.4f}  AUPRC {results[split]['auprc']:.4f}")
            pdf = d.copy()
            pdf["score"], pdf["split"], pdf["regime"] = p, split, regime
            preds_all.append(pdf)

            # auditable evidence for the highest-scoring test pairs
            if split.endswith("_test") and args.explain_top > 0:
                top = np.argsort(-p)[:args.explain_top]
                ev = explain(A_L, space, ai[top], bi[top], names)
                contrib = models[0].contributions(Xt[top])
                for j, e in enumerate(ev):
                    e.update({"score": float(p[top[j]]), "label": float(d["label"].iloc[top[j]])})
                    if contrib is not None:
                        c = contrib[j, :-1]
                        e["group_contribution_logit"] = {
                            g: round(float(sum(c[k] for k in range(len(c)) if groups[k] == g)), 4)
                            for g in GROUPS}
                with open(out / f"audit_evidence_{split}.jsonl", "w") as fh:
                    for e in ev:
                        fh.write(json.dumps(e) + "\n")

        imp = np.zeros(len(names))
        for m in models:
            if m.kind == "lgb":
                imp += m.m.feature_importance("gain")
        if imp.sum() > 0:
            g_imp = {g: float(sum(imp[k] for k in range(len(names)) if groups[k] == g) / imp.sum())
                     for g in GROUPS}
            importance[regime] = g_imp
            log(f"  evidence-group share of gain: {json.dumps({k: round(v, 3) for k, v in g_imp.items()})}")

        if args.ablate:
            subsets = {"chem_pair only": ["chem_pair"],
                       "+bio_pair": ["chem_pair", "bio_pair"],
                       "+analog_transfer": ["chem_pair", "bio_pair", "analog_transfer"],
                       "full (+graph_topology)": list(GROUPS)}
            for label, gs in subsets.items():
                cols = [k for k in range(len(names)) if groups[k] in gs]
                if not cols:
                    continue
                ms = fit_ensemble(X[:, cols], y, Xv[:, cols], yv, [0], True, args.n_jobs)
                for split in EVAL_SPLITS[regime]:
                    d = splits[split]
                    Xt, _, _ = pair_features(A_L, d["source"].map(idx).to_numpy(),
                                             d["target"].map(idx).to_numpy(), space)
                    ablation.append({"regime": regime, "feature_set": label, "split": split,
                                     "auroc": float(roc_auc_score(d["label"], ms[0].predict(Xt[:, cols])))})
            log("  ablation done")

    pd.concat(preds_all).to_csv(out / "predictions.csv", index=False)
    summary = {"metrics": results, "evidence_group_importance": importance,
               "leakage_audit": audit, "n_drugs": n, "bio_blocks": list(bio_blocks), "bio_block_dims": {k: int(v.shape[1]) for k, v in bio_blocks.items()},
               "seeds": seeds, "runtime_sec": round(time.time() - t0, 1),
               "protocol": "dev splits used only for early stopping/threshold; test splits untouched"}
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    pd.DataFrame(results).T.to_csv(out / "metrics.csv")
    if ablation:
        pd.DataFrame(ablation).to_csv(out / "ablation.csv", index=False)

    print("\n================ FINAL (test splits) ================")
    for s in ("transductive_test", "s1_test", "s2_test"):
        r = results[s]
        print(f"{s:18s} AUROC {r['auroc']:.4f}  ACC {r['accuracy']:.4f}  "
              f"AUPRC {r['auprc']:.4f}  F1 {r['f1']:.4f}  MCC {r['mcc']:.4f}  (n={r['n']})")
    print(f"Saved to {out.resolve()}  |  runtime {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
