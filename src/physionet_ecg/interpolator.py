"""
PhysioNet ECG Digitization - Dynamic Resolution Interpolator
Implementation of the 3-6-2 "Loptica" Dynamic Resolution Protocol resampling logic.
"""

from typing import List, Dict, Any

class DynamicResolutionInterpolator:
    def __init__(self, target_frequency_hz: int = 500):
        self.target_frequency_hz = target_frequency_hz

    def resample_signal(self, raw_signal: List[float], source_freq_hz: float) -> List[float]:
        """
        Resamples a discrete signal vector to target frequency using linear interpolation (Loptica Protocol).
        """
        if not raw_signal:
            return []
            
        ratio = self.target_frequency_hz / source_freq_hz
        new_length = int(len(raw_signal) * ratio)
        resampled = []
        
        for i in range(new_length):
            src_idx = i / ratio
            low_idx = int(src_idx)
            high_idx = min(low_idx + 1, len(raw_signal) - 1)
            weight = src_idx - low_idx
            
            val = (1 - weight) * raw_signal[low_idx] + weight * raw_signal[high_idx]
            resampled.append(round(val, 4))
            
        return resampled

if __name__ == "__main__":
    interpolator = DynamicResolutionInterpolator(target_frequency_hz=500)
    raw = [0.0, 0.2, 1.0, 0.3, -0.1, 0.0] # Sample low-res trace
    resampled = interpolator.resample_signal(raw, source_freq_hz=100)
    print("Resampled Signal Length:", len(resampled), "Preview:", resampled[:10])
