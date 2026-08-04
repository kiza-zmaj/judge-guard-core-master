"""
PhysioNet ECG Digitization - Complete 3-6-2 "Loptica" Pipeline Integration
Orchestrates loading, grid calibration, vectorization, dynamic resampling, and WFDB export.
"""

from typing import Dict, Any
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.physionet_ecg.orchestration import LopticaOrchestrator, check_drift
from src.physionet_ecg.loader import ECGGridCalibrator
from src.physionet_ecg.vectorizer import WaveformVectorizer
from src.physionet_ecg.interpolator import DynamicResolutionInterpolator
from src.physionet_ecg.exporter import WFDBExporter

class PhysioNetECGPipeline:
    def __init__(self, record_id: str = "physionet_ecg_sample_01"):
        self.orchestrator = LopticaOrchestrator()
        self.calibrator = ECGGridCalibrator()
        self.vectorizer = WaveformVectorizer(sample_rate=500)
        self.interpolator = DynamicResolutionInterpolator(target_frequency_hz=500)
        self.exporter = WFDBExporter(record_name=record_id)

    def process_ecg_image(self, image_path: str) -> Dict[str, Any]:
        """
        Executes the end-to-end 3-6-2 "Loptica" Digitization Pipeline.
        """
        # Step A1 & A2: Load & Calibrate Grid
        image_meta = self.calibrator.simulate_load_image(image_path)
        
        # Step I3 & I4: Vectorize & Resample Leads
        digitized_signals = {}
        for lead in image_meta["leads"]:
            vec = self.vectorizer.vectorize_lead(lead, duration_sec=2.5)
            # Apply dynamic resolution interpolation
            resampled = self.interpolator.resample_signal(vec["signal_vector"], source_freq_hz=100)
            digitized_signals[lead] = resampled
            
        # Step I5: WFDB Export
        export_result = self.exporter.export_wfdb_meta(digitized_signals, sample_rate=500)
        
        return {
            "orchestration_status": self.orchestrator.get_status(),
            "image_metadata": image_meta,
            "digitized_leads_count": len(digitized_signals),
            "wfdb_export": export_result
        }

if __name__ == "__main__":
    pipeline = PhysioNetECGPipeline()
    output = pipeline.process_ecg_image("physionet_sample_ecg.png")
    print("=== PhysioNet ECG Digitization 3-6-2 Loptica Pipeline Output ===")
    print("Orchestration Status:", output["orchestration_status"]["status"])
    print("Digitized Leads Count:", output["digitized_leads_count"])
    print("Export Status:", output["wfdb_export"]["export_status"])
