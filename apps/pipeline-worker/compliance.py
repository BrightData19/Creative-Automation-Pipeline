# /apps/pipeline-worker/compliance.py

import re
import cv2
import numpy as np
from PIL import Image, ImageDraw
from typing import Dict, List, Tuple, Optional, Union
import json
import os

class BrandComplianceChecker:
    """Comprehensive brand compliance checking system."""
    
    def __init__(self):
        # Brand guidelines configuration
        self.brand_colors = {
            "primary": [(0, 123, 255), (0, 100, 200)],  # Blue variations
            "secondary": [(255, 193, 7), (255, 180, 0)],  # Yellow variations
            "accent": [(220, 53, 69), (200, 50, 60)],    # Red variations
            "neutral": [(108, 117, 125), (90, 100, 110)]  # Gray variations
        }
        
        # Logo detection templates (placeholder - in production, these would be actual logo images)
        self.logo_templates = []
        self.logo_threshold = float(os.getenv("LOGO_DETECTION_THRESHOLD", "0.7"))
        
        # Brand guidelines
        self.brand_guidelines = {
            "min_logo_size": float(os.getenv("MIN_LOGO_SIZE_RATIO", "0.05")),  # Logo should be at least 5% of image area
            "max_text_ratio": float(os.getenv("MAX_TEXT_RATIO", "0.3")),  # Text should not exceed 30% of image
            "required_elements": ["logo", "brand_colors"],
            "prohibited_elements": ["watermarks", "copyright_symbols"]
        }
    
    def check_logo_presence(self, image: Image.Image) -> Dict[str, any]:
        """Check if brand logo is present and properly sized in the image."""
        try:
            # Convert PIL image to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Enhanced logo detection using multiple methods
            logo_detected = self._detect_logo_enhanced(img_cv)
            
            # Calculate logo coverage
            logo_coverage = self._calculate_logo_coverage_enhanced(img_cv)
            
            # Check if logo meets size requirements
            meets_size_requirement = logo_coverage >= self.brand_guidelines["min_logo_size"]
            
            # Calculate compliance score with more granular scoring
            if logo_detected and meets_size_requirement:
                compliance_score = 1.0
            elif logo_detected:
                compliance_score = 0.7  # Logo detected but too small
            else:
                compliance_score = 0.0
            
            return {
                "logo_detected": logo_detected,
                "logo_coverage": logo_coverage,
                "meets_size_requirement": meets_size_requirement,
                "compliance_score": compliance_score,
                "confidence": logo_coverage * 10,  # Convert coverage to confidence score
                "issues": [] if (logo_detected and meets_size_requirement) else [
                    "Logo not detected" if not logo_detected else "Logo too small"
                ]
            }
            
        except Exception as e:
            return {
                "logo_detected": False,
                "logo_coverage": 0.0,
                "meets_size_requirement": False,
                "compliance_score": 0.0,
                "confidence": 0.0,
                "issues": [f"Logo detection error: {str(e)}"]
            }
    
    def _detect_logo_enhanced(self, img_cv: np.ndarray) -> bool:
        """Enhanced logo detection using multiple OpenCV methods."""
        try:
            # Method 1: Template matching (if templates available)
            if self.logo_templates:
                if self._template_matching_detection(img_cv):
                    return True
            
            # Method 2: Feature-based detection
            if self._feature_based_detection(img_cv):
                return True
            
            # Method 3: Contour-based detection (improved)
            if self._contour_based_detection(img_cv):
                return True
            
            # Method 4: Color-based detection
            if self._color_based_detection(img_cv):
                return True
            
            return False
            
        except Exception as e:
            print(f"Logo detection error: {e}")
            return False
    
    def _template_matching_detection(self, img_cv: np.ndarray) -> bool:
        """Template matching for logo detection."""
        # Placeholder for template matching
        # In production, this would use actual logo templates
        return False
    
    def _feature_based_detection(self, img_cv: np.ndarray) -> bool:
        """Feature-based logo detection using SIFT/ORB."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Use ORB detector (faster than SIFT, good for logos)
            orb = cv2.ORB_create(
                nfeatures=1000,
                scaleFactor=1.2,
                nlevels=8,
                edgeThreshold=31,
                firstLevel=0,
                WTA_K=2,
                patchSize=31
            )
            
            # Detect keypoints and compute descriptors
            keypoints, descriptors = orb.detectAndCompute(gray, None)
            
            # If we have enough keypoints, consider it a potential logo area
            return len(keypoints) > 50
            
        except Exception:
            return False
    
    def _contour_based_detection(self, img_cv: np.ndarray) -> bool:
        """Improved contour-based logo detection."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding for better edge detection
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Apply morphological operations to clean up the image
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours based on area and shape
            logo_candidates = []
            min_area = (img_cv.shape[0] * img_cv.shape[1]) * 0.001  # 0.1% of image area
            max_area = (img_cv.shape[0] * img_cv.shape[1]) * 0.3   # 30% of image area
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h
                    
                    # Check if aspect ratio is reasonable for a logo
                    if 0.2 < aspect_ratio < 5.0:
                        # Calculate contour properties
                        perimeter = cv2.arcLength(contour, True)
                        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                        
                        # Logos typically have moderate circularity (not too round, not too angular)
                        if 0.1 < circularity < 0.8:
                            logo_candidates.append((x, y, w, h, area, circularity))
            
            # If we find reasonable logo candidates, consider logo detected
            return len(logo_candidates) > 0
            
        except Exception as e:
            print(f"Contour detection error: {e}")
            return False
    
    def _color_based_detection(self, img_cv: np.ndarray) -> bool:
        """Color-based logo detection using brand color analysis."""
        try:
            # Convert to HSV color space for better color analysis
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            
            # Define brand color ranges in HSV
            brand_color_ranges = [
                # Blue (primary brand color)
                (np.array([100, 50, 50]), np.array([130, 255, 255])),
                # Yellow (secondary brand color)
                (np.array([20, 50, 50]), np.array([30, 255, 255])),
                # Red (accent brand color)
                (np.array([0, 50, 50]), np.array([10, 255, 255])),
                (np.array([170, 50, 50]), np.array([180, 255, 255]))  # Red wraps around
            ]
            
            # Check if any brand colors are present in significant amounts
            for lower, upper in brand_color_ranges:
                mask = cv2.inRange(hsv, lower, upper)
                color_coverage = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])
                
                if color_coverage > 0.05:  # 5% coverage threshold
                    return True
            
            return False
            
        except Exception as e:
            print(f"Color detection error: {e}")
            return False
    
    def _calculate_logo_coverage_enhanced(self, img_cv: np.ndarray) -> float:
        """Enhanced logo coverage calculation using multiple detection methods."""
        try:
            # Method 1: Edge density analysis
            edge_coverage = self._calculate_edge_coverage(img_cv)
            
            # Method 2: Color-based coverage
            color_coverage = self._calculate_color_coverage(img_cv)
            
            # Method 3: Texture-based coverage
            texture_coverage = self._calculate_texture_coverage(img_cv)
            
            # Combine multiple methods for more accurate estimation
            combined_coverage = (edge_coverage + color_coverage + texture_coverage) / 3
            
            # Apply smoothing and bounds
            smoothed_coverage = np.clip(combined_coverage, 0.0, 0.25)  # Cap at 25%
            
            return float(smoothed_coverage)
            
        except Exception as e:
            print(f"Coverage calculation error: {e}")
            return 0.0
    
    def _calculate_edge_coverage(self, img_cv: np.ndarray) -> float:
        """Calculate coverage based on edge density."""
        try:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply bilateral filter to reduce noise while preserving edges
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Use Canny edge detection with automatic thresholding
            sigma = 0.33
            median = np.median(filtered)
            lower = int(max(0, (1.0 - sigma) * median))
            upper = int(min(255, (1.0 + sigma) * median))
            
            edges = cv2.Canny(filtered, lower, upper)
            
            # Calculate edge density
            total_pixels = edges.shape[0] * edges.shape[1]
            edge_pixels = np.count_nonzero(edges)
            edge_density = edge_pixels / total_pixels
            
            # Convert to estimated logo coverage
            estimated_coverage = min(edge_density * 8, 0.2)  # Scale factor and cap
            
            return estimated_coverage
            
        except Exception:
            return 0.0
    
    def _calculate_color_coverage(self, img_cv: np.ndarray) -> float:
        """Calculate coverage based on brand color presence."""
        try:
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            
            # Define brand color ranges
            brand_colors = [
                (np.array([100, 50, 50]), np.array([130, 255, 255])),  # Blue
                (np.array([20, 50, 50]), np.array([30, 255, 255])),   # Yellow
                (np.array([0, 50, 50]), np.array([10, 255, 255])),    # Red
            ]
            
            total_coverage = 0.0
            for lower, upper in brand_colors:
                mask = cv2.inRange(hsv, lower, upper)
                coverage = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])
                total_coverage += coverage
            
            return min(total_coverage, 0.15)  # Cap at 15%
            
        except Exception:
            return 0.0
    
    def _calculate_texture_coverage(self, img_cv: np.ndarray) -> float:
        """Calculate coverage based on texture analysis."""
        try:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply Gabor filter for texture detection
            kernel = cv2.getGaborKernel((21, 21), 8.0, np.pi/4, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(gray, cv2.CV_8UC3, kernel)
            
            # Calculate texture variance
            texture_variance = np.var(filtered)
            max_variance = 255 * 255  # Maximum possible variance
            
            # Normalize and convert to coverage estimate
            texture_coverage = min((texture_variance / max_variance) * 10, 0.1)
            
            return texture_coverage
            
        except Exception:
            return 0.0
    
    def check_brand_colors(self, image: Image.Image) -> Dict[str, any]:
        """Check if the image uses brand-appropriate colors."""
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Analyze color distribution
            color_analysis = self._analyze_colors(img_array)
            
            # Check brand color compliance
            brand_color_score = self._calculate_brand_color_score(color_analysis)
            
            # Identify non-brand colors
            non_brand_colors = self._identify_non_brand_colors(color_analysis)
            
            return {
                "brand_color_score": brand_color_score,
                "color_compliance": brand_color_score >= 0.7,
                "dominant_colors": color_analysis["dominant_colors"],
                "non_brand_colors": non_brand_colors,
                "compliance_score": brand_color_score,
                "issues": [] if brand_color_score >= 0.7 else [
                    f"Low brand color compliance: {brand_color_score:.2f}"
                ]
            }
            
        except Exception as e:
            return {
                "brand_color_score": 0.0,
                "color_compliance": False,
                "dominant_colors": [],
                "non_brand_colors": [],
                "compliance_score": 0.0,
                "issues": [f"Color analysis error: {str(e)}"]
            }
    
    def _analyze_colors(self, img_array: np.ndarray) -> Dict[str, any]:
        """Analyze the color distribution in the image."""
        try:
            # Reshape image to 2D array of pixels
            pixels = img_array.reshape(-1, 3)
            
            # Convert to float for calculations
            pixels = pixels.astype(np.float32)
            
            # Calculate dominant colors using k-means clustering
            from sklearn.cluster import KMeans
            
            try:
                kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
                kmeans.fit(pixels)
                
                # Get cluster centers (dominant colors)
                dominant_colors = kmeans.cluster_centers_.astype(np.uint8)
                
                # Count pixels in each cluster
                labels = kmeans.labels_
                color_counts = np.bincount(labels)
                
                # Sort by frequency
                sorted_indices = np.argsort(color_counts)[::-1]
                dominant_colors = dominant_colors[sorted_indices]
                color_counts = color_counts[sorted_indices]
                
                return {
                    "dominant_colors": dominant_colors.tolist(),
                    "color_counts": color_counts.tolist(),
                    "total_pixels": len(pixels)
                }
                
            except ImportError:
                # Fallback if sklearn is not available
                return self._fallback_color_analysis(img_array)
                
        except Exception as e:
            print(f"Color analysis error: {e}")
            return {
                "dominant_colors": [],
                "color_counts": [],
                "total_pixels": 0
            }
    
    def _fallback_color_analysis(self, img_array: np.ndarray) -> Dict[str, any]:
        """Fallback color analysis using OpenCV methods."""
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # Calculate histograms for each channel
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Find peaks in histograms
            peak_h = np.argmax(hist_h)
            peak_s = np.argmax(hist_s)
            peak_v = np.argmax(hist_v)
            
            # Convert HSV peaks back to RGB
            peak_hsv = np.array([[[peak_h, peak_s, peak_v]]], dtype=np.uint8)
            peak_rgb = cv2.cvtColor(peak_hsv, cv2.COLOR_HSV2RGB)
            dominant_color = peak_rgb[0, 0].tolist()
            
            return {
                "dominant_colors": [dominant_color],
                "color_counts": [np.max(hist_v)],
                "total_pixels": img_array.shape[0] * img_array.shape[1]
            }
            
        except Exception:
            return {
                "dominant_colors": [],
                "color_counts": [],
                "total_pixels": 0
            }
    
    def _calculate_brand_color_score(self, color_analysis: Dict[str, any]) -> float:
        """Calculate how well the image colors align with brand guidelines."""
        dominant_colors = color_analysis["dominant_colors"]
        color_counts = color_analysis["color_counts"]
        total_pixels = color_analysis["total_pixels"]
        
        if not dominant_colors or total_pixels == 0:
            return 0.0
        
        brand_color_matches = 0
        total_weighted_pixels = 0
        
        for i, color in enumerate(dominant_colors):
            color_weight = color_counts[i] / total_pixels
            
            # Check if this color matches any brand color
            best_match = self._find_best_brand_color_match(color)
            if best_match > 0.8:  # 80% similarity threshold
                brand_color_matches += color_weight
            
            total_weighted_pixels += color_weight
        
        if total_weighted_pixels == 0:
            return 0.0
        
        return brand_color_matches / total_weighted_pixels
    
    def _find_best_brand_color_match(self, color: List[int]) -> float:
        """Find the best match between a color and brand colors."""
        best_match = 0.0
        
        for brand_color_name, brand_color_variations in self.brand_colors.items():
            for brand_color in brand_color_variations:
                # Calculate color similarity using Euclidean distance
                distance = np.sqrt(sum((np.array(color) - np.array(brand_color)) ** 2))
                max_distance = np.sqrt(255 ** 2 * 3)  # Maximum possible distance
                similarity = 1.0 - (distance / max_distance)
                
                if similarity > best_match:
                    best_match = similarity
        
        return best_match
    
    def _identify_non_brand_colors(self, color_analysis: Dict[str, any]) -> List[List[int]]:
        """Identify colors that don't match brand guidelines."""
        non_brand_colors = []
        dominant_colors = color_analysis["dominant_colors"]
        
        for color in dominant_colors:
            best_match = self._find_best_brand_color_match(color)
            if best_match < 0.6:  # 60% similarity threshold
                non_brand_colors.append(color)
        
        return non_brand_colors

class LegalContentChecker:
    """Legal content filtering and compliance checking."""
    
    def __init__(self):
        # Load prohibited words and phrases
        self.prohibited_words = self._load_prohibited_words()
        self.content_safety_rules = self._load_content_safety_rules()
    
    def _load_prohibited_words(self) -> List[str]:
        """Load prohibited words from configuration or database."""
        # In production, this would come from a database or configuration file
        # For now, we'll use a basic list
        return [
            "prohibited", "restricted", "banned", "illegal", "unlawful",
            "copyright", "trademark", "registered", "patent", "confidential",
            "secret", "private", "internal", "classified", "restricted",
            "adult", "explicit", "mature", "violent", "offensive",
            "discriminatory", "hate", "harassment", "bullying", "abuse"
        ]
    
    def _load_content_safety_rules(self) -> Dict[str, any]:
        """Load content safety rules and guidelines."""
        return {
            "max_text_length": int(os.getenv("MAX_TEXT_LENGTH", "1000")),
            "prohibited_symbols": ["©", "®", "™", "℠"],
            "required_disclaimers": [],
            "prohibited_topics": ["politics", "religion", "controversial"]
        }
    
    def check_text_content(self, text: str) -> Dict[str, any]:
        """Check text content for legal compliance and safety."""
        if not text:
            return {
                "content_safe": True,
                "compliance_score": 1.0,
                "issues": [],
                "flagged_words": [],
                "flagged_symbols": []
            }
        
        issues = []
        flagged_words = []
        flagged_symbols = []
        
        # Check for prohibited words
        text_lower = text.lower()
        for word in self.prohibited_words:
            if word.lower() in text_lower:
                flagged_words.append(word)
                issues.append(f"Prohibited word detected: {word}")
        
        # Check for prohibited symbols
        for symbol in self.content_safety_rules["prohibited_symbols"]:
            if symbol in text:
                flagged_symbols.append(symbol)
                issues.append(f"Prohibited symbol detected: {symbol}")
        
        # Check text length
        if len(text) > self.content_safety_rules["max_text_length"]:
            issues.append(f"Text too long: {len(text)} characters (max: {self.content_safety_rules['max_text_length']})")
        
        # Check for prohibited topics
        for topic in self.content_safety_rules["prohibited_topics"]:
            if topic.lower() in text_lower:
                issues.append(f"Prohibited topic detected: {topic}")
        
        # Calculate compliance score
        compliance_score = 1.0 if len(issues) == 0 else max(0.0, 1.0 - (len(issues) * 0.2))
        
        return {
            "content_safe": len(issues) == 0,
            "compliance_score": compliance_score,
            "issues": issues,
            "flagged_words": flagged_words,
            "flagged_symbols": flagged_symbols,
            "text_length": len(text),
            "max_allowed_length": self.content_safety_rules["max_text_length"]
        }
    
    def check_image_content(self, image: Image.Image) -> Dict[str, any]:
        """Check image content for legal compliance and safety."""
        try:
            # Convert PIL image to OpenCV format for analysis
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Basic image content analysis using OpenCV
            analysis_result = self._analyze_image_content_opencv(img_cv)
            
            return {
                "content_safe": analysis_result["content_safe"],
                "compliance_score": analysis_result["compliance_score"],
                "issues": analysis_result["issues"],
                "warnings": analysis_result["warnings"],
                "analysis_details": analysis_result["details"]
            }
            
        except Exception as e:
            return {
                "content_safe": True,  # Default to safe on error
                "compliance_score": 1.0,
                "issues": [],
                "warnings": [f"Image content analysis error: {str(e)}"],
                "analysis_details": {}
            }
    
    def _analyze_image_content_opencv(self, img_cv: np.ndarray) -> Dict[str, any]:
        """Analyze image content using OpenCV methods."""
        try:
            issues = []
            warnings = []
            details = {}
            
            # Check image dimensions
            height, width = img_cv.shape[:2]
            details["dimensions"] = {"width": width, "height": height}
            
            # Check for potential text in images using edge detection
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply morphological operations to detect text-like structures
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(gray, kernel, iterations=1)
            eroded = cv2.erode(dilated, kernel, iterations=1)
            
            # Find contours that might represent text
            contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_candidates = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if 100 < area < 10000:  # Reasonable text area
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h
                    if 0.1 < aspect_ratio < 10:  # Text-like aspect ratio
                        text_candidates += 1
            
            details["text_candidates"] = text_candidates
            
            # Check for potential faces (privacy concern)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if face_cascade is not None:
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                details["faces_detected"] = len(faces)
                
                if len(faces) > 0:
                    warnings.append(f"Potential faces detected: {len(faces)}")
            else:
                details["faces_detected"] = 0
                warnings.append("Face detection not available")
            
            # Calculate overall content safety score
            content_safe = len(issues) == 0
            compliance_score = 1.0 if content_safe else max(0.5, 1.0 - len(issues) * 0.1)
            
            return {
                "content_safe": content_safe,
                "compliance_score": compliance_score,
                "issues": issues,
                "warnings": warnings,
                "details": details
            }
            
        except Exception as e:
            return {
                "content_safe": True,
                "compliance_score": 1.0,
                "issues": [],
                "warnings": [f"OpenCV analysis error: {str(e)}"],
                "details": {}
            }

import privacy as privacy_mod


class ComplianceEngine:
    """Main compliance engine that orchestrates all compliance checks."""
    
    def __init__(self):
        self.brand_checker = BrandComplianceChecker()
        self.legal_checker = LegalContentChecker()
        self.ethics_checker = EthicsChecker()
        self.privacy_checker = privacy_mod.PrivacyChecker()
    
    def run_comprehensive_check(self, image: Image.Image, text: str = "") -> Dict[str, any]:
        """Run all compliance checks and return comprehensive report."""
        try:
            # Run brand compliance checks
            logo_check = self.brand_checker.check_logo_presence(image)
            color_check = self.brand_checker.check_brand_colors(image)
            
            # Run legal/ethics/privacy content checks
            text_check = self.legal_checker.check_text_content(text)
            ethics_check = self.ethics_checker.check_ethics(text)
            privacy_check = self.privacy_checker.check_text_privacy(text)
            image_check = self.legal_checker.check_image_content(image)
            
            # Calculate overall compliance score with weighted components
            weights = {
                "logo": 0.25,
                "color": 0.2,
                "text": 0.2,
                "image": 0.15,
                "ethics": 0.1,
                "privacy": 0.1,
            }
            
            weighted_score = (
                logo_check["compliance_score"] * weights["logo"] +
                color_check["compliance_score"] * weights["color"] +
                text_check["compliance_score"] * weights["text"] +
                image_check["compliance_score"] * weights["image"] +
                ethics_check["compliance_score"] * weights["ethics"] +
                privacy_check["compliance_score"] * weights["privacy"]
            )
            
            # Compile all issues
            all_issues = []
            all_issues.extend(logo_check.get("issues", []))
            all_issues.extend(color_check.get("issues", []))
            all_issues.extend(text_check.get("issues", []))
            all_issues.extend(image_check.get("issues", []))
            all_issues.extend(ethics_check.get("issues", []))
            all_issues.extend(privacy_check.get("issues", []))
            
            # Determine overall compliance status
            overall_compliant = weighted_score >= 0.8 and len(all_issues) <= 2
            
            return {
                "overall_compliant": overall_compliant,
                "overall_score": weighted_score,
                "compliance_breakdown": {
                    "logo_compliance": logo_check,
                    "color_compliance": color_check,
                    "text_compliance": text_check,
                    "image_compliance": image_check,
                    "ethics_compliance": ethics_check,
                    "privacy_compliance": privacy_check,
                },
                "all_issues": all_issues,
                "critical_issues": [issue for issue in all_issues if "prohibited" in issue.lower() or "error" in issue.lower()],
                "warnings": [issue for issue in all_issues if "warning" in issue.lower()],
                "recommendations": self._generate_recommendations(logo_check, color_check, text_check, image_check),
                "metadata": {
                    "check_timestamp": "now",
                    "image_dimensions": image.size if image else None,
                    "text_length": len(text) if text else 0
                }
            }
            
        except Exception as e:
            return {
                "overall_compliant": False,
                "overall_score": 0.0,
                "error": f"Compliance check failed: {str(e)}",
                "all_issues": [f"System error: {str(e)}"],
                "critical_issues": [f"System error: {str(e)}"],
                "warnings": [],
                "recommendations": ["Contact system administrator for technical support"],
                "metadata": {
                    "check_timestamp": "now",
                    "error": str(e)
                }
            }
    
    def _generate_recommendations(self, logo_check: Dict, color_check: Dict, text_check: Dict, image_check: Dict) -> List[str]:
        """Generate actionable recommendations based on compliance check results."""
        recommendations = []
        
        # Logo recommendations
        if not logo_check.get("logo_detected", False):
            recommendations.append("Add brand logo to the image")
        elif not logo_check.get("meets_size_requirement", False):
            recommendations.append("Increase logo size to meet brand guidelines")
        
        # Color recommendations
        if color_check.get("compliance_score", 0.0) < 0.7:
            recommendations.append("Use more brand colors to improve compliance")
        
        # Text recommendations
        if text_check.get("flagged_words"):
            recommendations.append("Remove or replace prohibited words")
        if text_check.get("flagged_symbols"):
            recommendations.append("Remove prohibited symbols")
        
        # Image content recommendations
        if image_check.get("warnings"):
            recommendations.append("Review image content for potential compliance issues")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Image meets all compliance requirements")
        
        return recommendations

# Legacy functions for backward compatibility
def check_banned_words(text: str) -> List[str]:
    """Legacy function - checks for banned words in a given text."""
    checker = LegalContentChecker()
    result = checker.check_text_content(text)
    return result.get("flagged_words", [])

def check_logo_presence(image: Image.Image) -> bool:
    """Legacy function - checks if a logo is present in the image."""
    checker = BrandComplianceChecker()
    result = checker.check_logo_presence(image)
    return result.get("logo_detected", False)

# New comprehensive compliance function
def run_compliance_check(image: Image.Image, text: str = "") -> Dict[str, any]:
    """Run comprehensive compliance check on image and text."""
    engine = ComplianceEngine()
    return engine.run_comprehensive_check(image, text)
class EthicsChecker:
    """Basic ethical content checks for sensitive or biased language."""

    def __init__(self):
        # Simplified keyword sets; in production, use robust moderation models/APIs
        self.protected_classes = [
            "race", "ethnicity", "religion", "gender", "sexual orientation",
            "disability", "age", "nationality",
        ]
        self.disallowed_bias_terms = [
            "stereotype", "inferior", "superior", "primitive", "uncivilized",
            "illegal alien", "oriental", "retarded",
        ]

    def check_ethics(self, text: str) -> Dict[str, any]:
        if not text:
            return {"ethical": True, "compliance_score": 1.0, "issues": []}
        tl = text.lower()
        issues: List[str] = []
        for term in self.disallowed_bias_terms:
            if term in tl:
                issues.append(f"Potential biased term detected: {term}")
        for pc in self.protected_classes:
            if pc in tl:
                issues.append(
                    f"Sensitive topic referenced: {pc} (ensure neutral, respectful framing)"
                )
        score = 1.0 if not issues else max(0.6, 1.0 - 0.1 * len(issues))
        return {"ethical": len(issues) == 0, "compliance_score": score, "issues": issues}
