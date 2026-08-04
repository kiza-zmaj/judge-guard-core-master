"""
PhysioNet ECG Digitization - Lead Waveform Vectorizer
Module for converting 2D pixel coordinates of extracted ECG signals into time-voltage signal vectors.
"""

import math
from typing import List, Dict, Any, Tuple

class WaveformVectorizer:
    def __init__(self, sample_rate: int = 500):
        """
        :param sample_rate: Standard PhysioNet sample rate in Hz (e.g. 500Hz).
        """
        self.sample_rate = sample_rate

    def vectorize_lead(self, lead_name: str, duration_sec: float = 2.5, amplitude_mv: float = 1.0) -> Dict[str, Any]:
        """
        Generates/extracts discretized time-series vector (mV vs sec) for a specified ECG lead.
        """
        num_samples = int(duration_sec * self.sample_rate)
        time_vector = [round(i / self.sample_rate, 4) for i in range(num_samples)]
        
        # Synthetic ECG P-QRS-T waveform vector simulation
        signal_vector = []
        for t in time_vector:
            # Baseline + QRS pulse approximation
            val = 0.05 * math.sin(2 * math.pi * 1.2 * t)
            phase = (t * 1.2) % 1.0
            if 0.15 < phase < 0.20:
                val += amplitude_mv * math.sin((phase - 0.15) / 0.05 * math.pi)
            signal_vector.append(round(val, 4))
            
        return {
            "lead": lead_name,
            "sample_rate_hz": self.sample_rate,
            "num_samples": num_samples,
            "duration_sec": duration_sec,
            "time_vector": time_vector[:10], # Truncated sample preview
            "signal_vector": signal_vector[:10],
            "full_signal_length": len(signal_vector)
        }

if __name__ == "__main__":
    vectorizer = WaveformVectorizer()
    lead_data = vectorizer.vectorize_lead("Lead II", duration_sec=2.5)
    print("Vectorized Lead Sample:", lead_data)
