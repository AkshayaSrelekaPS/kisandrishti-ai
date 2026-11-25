"""
OpenCV NEON-Accelerated Severity Quantification Engine.
Calculates Disease Infection Severity Index (S) via calibrated HSV color segmentation.
Heuristic thresholds (10% and 25%) provide leaf-blade experimental estimates.
"""
import cv2
import numpy as np


class SeverityAnalyzer:
    def __init__(self):
        # Calibrated HSV ranges for outdoor field foliage and lesions
        self.lower_healthy = np.array([25, 30, 30], dtype=np.uint8)
        self.upper_healthy = np.array([85, 255, 255], dtype=np.uint8)

        self.lower_necrotic = np.array([5, 40, 20], dtype=np.uint8)
        self.upper_necrotic = np.array([24, 255, 180], dtype=np.uint8)

        self.lower_chlorotic = np.array([22, 100, 100], dtype=np.uint8)
        self.upper_chlorotic = np.array([38, 255, 255], dtype=np.uint8)

    def compute_foliage_ratio(self, leaf_bgr: np.ndarray) -> float:
        """Returns fraction of image pixels occupied by foliage/lesion colors (0.0 to 1.0)."""
        hsv = cv2.cvtColor(leaf_bgr, cv2.COLOR_BGR2HSV)
        mask_healthy = cv2.inRange(hsv, self.lower_healthy, self.upper_healthy)
        mask_necrosis = cv2.inRange(hsv, self.lower_necrotic, self.upper_necrotic)
        mask_chlorosis = cv2.inRange(hsv, self.lower_chlorotic, self.upper_chlorotic)
        mask_leaf = cv2.bitwise_or(mask_healthy, cv2.bitwise_or(mask_necrosis, mask_chlorosis))
        total_pixels = leaf_bgr.shape[0] * leaf_bgr.shape[1]
        if total_pixels == 0:
            return 0.0
        return float(cv2.countNonZero(mask_leaf)) / float(total_pixels)

    def analyze(self, leaf_bgr: np.ndarray, uncertain: bool = False):
        """
        Takes raw BGR leaf image and returns:
        - severity_index (float): percentage of leaf blade area damaged (0 - 100%)
        - stage (str): 'Healthy', 'Mild', 'Moderate', 'Severe', or 'Uncertain'
        - annotated_image (np.ndarray): visual output with contours and lesion overlays
        """
        hsv = cv2.cvtColor(leaf_bgr, cv2.COLOR_BGR2HSV)

        # 1. Segment Total Leaf Blade Area
        mask_healthy = cv2.inRange(hsv, self.lower_healthy, self.upper_healthy)
        mask_necrosis = cv2.inRange(hsv, self.lower_necrotic, self.upper_necrotic)
        mask_chlorosis = cv2.inRange(hsv, self.lower_chlorotic, self.upper_chlorotic)

        mask_leaf = cv2.bitwise_or(mask_healthy, cv2.bitwise_or(mask_necrosis, mask_chlorosis))

        kernel_5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_leaf = cv2.morphologyEx(mask_leaf, cv2.MORPH_CLOSE, kernel_5)
        mask_leaf = cv2.morphologyEx(mask_leaf, cv2.MORPH_OPEN, kernel_5)

        # 2. Segment Pathogen Lesion Area strictly within Leaf
        raw_lesions = cv2.bitwise_or(mask_necrosis, mask_chlorosis)
        mask_pathogen = cv2.bitwise_and(raw_lesions, mask_leaf)

        kernel_3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask_pathogen = cv2.morphologyEx(mask_pathogen, cv2.MORPH_OPEN, kernel_3)

        # 3. Calculate Surface Area Metrics
        leaf_pixels = int(cv2.countNonZero(mask_leaf))
        lesion_pixels = int(cv2.countNonZero(mask_pathogen))

        if leaf_pixels == 0:
            return 0.0, "Uncertain", leaf_bgr.copy()

        severity_index = (lesion_pixels / float(leaf_pixels)) * 100.0

        # 4. Map to Heuristic Leaf-Level Severity Tiers
        if uncertain:
            stage = "Uncertain"
        elif severity_index < 2.0:
            stage = "Healthy"
        elif severity_index < 10.0:
            stage = "Mild"
        elif 10.0 <= severity_index <= 25.0:
            stage = "Moderate"
        else:
            stage = "Severe"

        # 5. Create Visual Overlay
        annotated = leaf_bgr.copy()
        contours_leaf, _ = cv2.findContours(mask_leaf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(annotated, contours_leaf, -1, (0, 255, 0), 2)
        annotated[mask_pathogen > 0] = [0, 0, 255]

        text_banner = f"Severity: {severity_index:.1f}% ({stage})"
        if stage in ["Healthy", "Mild"]:
            color_badge = (0, 255, 0)
        elif stage in ["Moderate", "Uncertain"]:
            color_badge = (0, 165, 255)
        else:
            color_badge = (0, 0, 255)

        cv2.rectangle(annotated, (10, 10), (350, 50), (0, 0, 0), -1)
        cv2.putText(annotated, text_banner, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_badge, 2)

        return round(severity_index, 2), stage, annotated
