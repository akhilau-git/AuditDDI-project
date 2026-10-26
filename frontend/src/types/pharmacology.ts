export interface CompoundProfile {
  name: string;
  cid?: number;
  chemblId?: string;
  formula: string;
  molecularWeight: number;
  logP: number;
  tpsa: number;
  hbd: number;
  hba: number;
  rotatableBonds: number;
  canonicalSmiles: string;
  inChIKey?: string;
  complexity: number;
  ro5Violations: number;
  veberViolations: number;
  qedScore: number; // 0 to 1
  structureImageUrl?: string;
  
  // Pillar 2: In-vitro & Preclinical Liabilities
  cipaProfile: {
    hergIc50: number; // in uM
    hergSafetyMargin: number; // Ratio of IC50 to therapeutic Cmax
    nav15Ic50: number; // in uM
    cav12Ic50: number; // in uM (often protective against pure hERG)
    netArrhythmiaRisk: 'Low' | 'Moderate' | 'High' | 'Critical';
    qtProlongationLikelihood: string;
  };
  diliProfile: {
    bsepInhibition: boolean;
    mitochondrialToxicity: boolean;
    reactiveMetaboliteLiability: boolean;
    diliConcernScore: 'Low' | 'Moderate' | 'High';
  };
  ichM7AmesMutagenicity: 'Negative' | 'Alert Present' | 'Positive';

  // Pillar 3: CYP Substrate / Inhibitor Status
  cypProfile: {
    cyp3a4Role: 'Substrate' | 'Inhibitor' | 'Inducer' | 'None';
    cyp3a4Ki?: number; // uM
    cyp2d6Role: 'Substrate' | 'Inhibitor' | 'Inducer' | 'None';
    cyp2d6Ki?: number; // uM
    cyp2c9Role: 'Substrate' | 'Inhibitor' | 'Inducer' | 'None';
    cyp2c9Ki?: number; // uM
  };

  // Adverse Drug Reactions (Monotherapy)
  monotherapyADRs: Array<{ term: string; count: number; organClass: string }>;
  boxedWarnings: string[];
}

export interface CYPConflict {
  enzyme: string;
  mechanism: 'Reversible Competitive' | 'Mechanism-Based (TDI)' | 'Induction' | 'Transporter Co-substrate';
  severity: 'Contraindicated' | 'Major' | 'Moderate' | 'Minor';
  perpetrator: string;
  victim: string;
  description: string;
}

export interface ICHM12Assessment {
  leadCompound: string;
  iMaxUnbound: number; // uM
  kiUnbound: number;   // uM
  r1Value: number;
  cutoffThreshold: number; // standard 1.02
  requiresClinicalTrial: boolean;
  regulatoryActionTier: 'Exempt / Sub-threshold' | 'Mandatory In Vivo DDI Trial' | 'Critical Contraindication';
  statutoryGuideline: string;
}

export interface SynergySignal {
  reaction: string;
  coAdminCount: number;
  leadSoloCount: number;
  coMedSoloCount: number;
  rorScore: number; // Reporting Odds Ratio
  synergyLevel: 'Additive' | 'Synergistic (1+1>2)' | 'Extreme Amplification';
}

export interface OrganStress {
  organ: 'Cardiovascular' | 'Hepatic' | 'Renal' | 'Hematologic' | 'CNS';
  baselineScore: number; // 0-100
  amplifiedScore: number; // 0-100
  liabilityStatus: 'Within Tolerance' | 'Elevated Stress' | 'Hazardous Overload';
  pathwayNotes: string;
}

export interface DoubleHitADR {
  reaction: string;
  systemOrganClass: string;
  leadReported: boolean;
  coMedReported: boolean;
  severityGrade: 'Mild' | 'Moderate' | 'Severe';
  clinicalImpact: string;
}

export interface PKSimulationParams {
  leadDoseMg: number;
  coMedDoseMg: number;
  staggerHours: number; // 0 to 8 hours
  leadHalfLifeHours: number;
  coMedHalfLifeHours: number;
  mtcLevel: number; // Minimum toxic concentration (ng/mL)
  mecLevel: number; // Minimum effective concentration (ng/mL)
}

// -------------------------------------------------------------
// New Research & Pharmaceutical R&D Data Contracts
// -------------------------------------------------------------

export type DDIModelPrediction =
  | {
      status: 'available';
      rawScore: number;
      calibratedScore: number;
      decisionThreshold: number;
      interactionPredicted: boolean;
      modelArchitecture: string;
      checkpointHash: string | null;
      calibration: { status: string; method: string | null; note: string };
      uncertainty: {
        status: string;
        method?: string | null;
        prediction_set?: string | null;
        abstain?: boolean | null;
        note: string;
      };
      applicabilityDomain: {
        status: string;
        outsideDomain: boolean | null;
        pairMinimumSimilarity: number | null;
        note: string;
      };
      sevenBranchInputCoverage: Record<string, { drug_a: boolean; drug_b: boolean }> | null;
      interactionRiskNote: string;
      interactionLabelNote: string;
      disclaimer: string;
    }
  | { status: 'unavailable'; message: string };

export interface SevenSourceEvidence {
  twosides: {
    available: boolean;
    reportedEventsCount: number;
    evidenceLevel: 'Documented High-Volume Signal' | 'Moderate Evidence' | 'Unreported in Cohort';
    signalNotes: string;
  };
  pubchem: {
    available: boolean;
    cidA?: number;
    cidB?: number;
    has2DStructure: boolean;
    has3DConformer: boolean;
  };
  chembl: {
    available: boolean;
    chemblIdA?: string;
    chemblIdB?: string;
    bioassayCount: number;
    hergDocumented: boolean;
  };
  openfda: {
    available: boolean;
    labelWarningsFound: boolean;
    contraindicationDocumented: boolean;
    boxedWarningPresent: boolean;
  };
  faers: {
    available: boolean;
    coDosingReportsCount: number;
    disproportionalitySignaled: boolean;
    reportingOddsRatioMax: number;
  };
  ddinter: {
    available: boolean;
    severityTier: 'Major / Contraindicated' | 'Moderate' | 'Minor' | 'Unrecorded';
    pkMechanisms: string[];
  };
  pharmgkb: {
    available: boolean;
    genesImplicated: string[];
    clinicalAnnotationLevel: 'Level 1A' | 'Level 1B' | 'Level 2A' | 'Exploratory / Unannotated';
    vipVariantNotes: string;
  };
  identityMappings: {
    rxcuiA?: string;
    rxcuiB?: string;
    chemblA?: string;
    chemblB?: string;
    pubchemA?: number;
    pubchemB?: number;
    inchiKeyA?: string;
    inchiKeyB?: string;
  };
  leakageAudit: {
    inTransductiveTrain: boolean;
    inS1Train: boolean;
    inS2Train: boolean;
    leakageStatus: 'Clean Inductive Test Pair (S2)' | 'Single Drug in Train Set (S1)' | 'Pair Present in Training Graph (Transductive)';
    scientificDisclaimer: string;
  };
}

export interface SplitEvaluationMetrics {
  auroc: number;
  prAuc: number;
  mcc: number;
  brierScore: number;
  ece: number; // Expected Calibration Error
  nPairs: number;
}

export interface EvaluationLabData {
  splits: {
    transductive: SplitEvaluationMetrics;
    s1UnseenDrug: SplitEvaluationMetrics;
    s2UnseenPair: SplitEvaluationMetrics;
  };
  calibrationBins: Array<{
    binIndex: number;
    binMidpoint: number;
    predictedMean: number;
    observedFraction: number;
    sampleCount: number;
  }>;
  confusionMatrix: {
    tp: number;
    fp: number;
    tn: number;
    fn: number;
  };
  errorStudioCases: Array<{
    pair: string;
    groundTruth: 1 | 0;
    predictedProb: number;
    errorType: 'False Positive (FP)' | 'False Negative (FN)';
    structuralLiability: string;
    rootCauseAnalysis: string;
  }>;
  conformalCoverage: {
    targetConfidence: number; // e.g. 0.90 or 0.95
    empiricalCoverage: number;
    meanIntervalWidth: number;
  };
}

export interface BatchScreeningRow {
  id: string;
  drugA: string;
  drugB: string;
  smilesA: string;
  smilesB: string;
  calibratedDdiProb: number;
  ddiClassification: 'Critical Liability' | 'Moderate Interaction' | 'Low Risk / Tolerated';
  primaryToxAlert: string;
  ichM12Trigger: boolean;
  applicabilityDomain: boolean;
  selected?: boolean;
}

export interface ModelGovernanceSpec {
  activeCheckpoints: Array<{
    id: string;
    architecture: string;
    datasetVersion: string;
    trainDate: string;
    checkpointSha256: string;
    status: 'Production' | 'Validation Candidate' | 'Benchmark Baseline';
    aurocS2: number;
  }>;
  reproducibilitySeed: number;
  datasetLineageHashes: {
    twosides: string;
    ddinter: string;
    chembl34: string;
    openfdaSpl: string;
  };
}

export interface FullAnalysisPayload {
  leadCompound: CompoundProfile;
  coMedication: CompoundProfile;
  cypConflicts: CYPConflict[];
  ichM12: ICHM12Assessment;
  synergySignals: SynergySignal[];
  organStressList: OrganStress[];
  doubleHitADRs: DoubleHitADR[];
  
  // Research R&D Enhancements
  ddiModelPrediction: DDIModelPrediction;
  sevenSourceEvidence: SevenSourceEvidence;

  apiSourceMetadata: {
    pubchemLive: boolean;
    chemblLive: boolean;
    openFdaLive: boolean;
    ddiBackendStatus: 'connected' | 'unavailable';
    timestamp: string;
  };
}
