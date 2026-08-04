# Task: PhysioNet ECG Digitization (3-6-2 "Loptica" Protocol)

## 🎯 Current Focus

- **Project:** PhysioNet ECG Digitization
- **Protocol:** 3-6-2 "Loptica" Dynamic Resolution Protocol
- **Verification Engine:** JudgeGuard v2.1 (Anti-Drift Protection)
- **Transition:** Transitioned from CSIRO Image2Biomass (ARCHIVED)
- **Research Context:** Gemini 2026 / MedGemma Impact Challenge

---

## 📐 3-6-2 Loptica Architecture Breakdown

### 🔬 3 Analysis Steps (Dekompozicija ECG Signala)
- [x] Step A1: ECG Image Signal Preprocessing & Region Extraction
- [x] Step A2: Lead Grid & Coordinate Calibration (Dynamic Resolution)
- [x] Step A3: Multimodal Signal Trace Extraction Strategy

### ⚡ 6 Implementation Steps (Izvršenje & Kodifikacija)
- [ ] Step I1: Configure Safety & Agent Orchestration (`src/physionet_ecg/orchestration.py`)
- [ ] Step I2: Implement ECG Image Loader & Grid Calibrator (`src/physionet_ecg/loader.py`)
- [ ] Step I3: Implement Bounding Box & Lead Waveform Vectorizer (`src/physionet_ecg/vectorizer.py`)
- [ ] Step I4: Implement Dynamic Resolution Signal Interpolator (`src/physionet_ecg/interpolator.py`)
- [ ] Step I5: Implement MedGemma/PhysioNet WFDB Signal Exporter (`src/physionet_ecg/exporter.py`)
- [ ] Step I6: Integrate Full 3-6-2 "Loptica" Digitization Pipeline (`src/physionet_ecg/pipeline.py`)

### 🔍 2 Verification Steps (Zatvaranje & Arhiviranje)
- [ ] Step V1: Comprehensive JudgeGuard v2.1 Verification & Synthetic ECG Digitization Benchmark
- [ ] Step V2: Final Work Log Update & Archival

---

## 🔒 Verification & Compliance
- **ONE_SKILL_FOCUS**: Active
- **END_TO_END_DISCIPLINE**: Enforced
- **VERIFY_BEFORE_EXECUTE**: Active via `judge_guard.py`
