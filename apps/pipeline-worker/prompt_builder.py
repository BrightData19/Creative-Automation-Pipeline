# /apps/pipeline-worker/prompt_builder.py

import os
from typing import Dict, List, Optional
import json

class LocalizationEngine:
    """Engine for handling localized messaging and cultural adaptation."""
    
    def __init__(self):
        # Regional and cultural configurations
        self.regional_configs = self._load_regional_configs()
        self.language_support = self._load_language_support()
        self.cultural_adaptations = self._load_cultural_adaptations()
    
    def _load_regional_configs(self) -> Dict[str, Dict]:
        """Load regional configuration data."""
        return {
            "US": {
                "language": "en",
                "currency": "USD",
                "date_format": "MM/DD/YYYY",
                "cultural_sensitivity": "moderate",
                "marketing_style": "direct",
                "color_preferences": ["blue", "red", "white"],
                "emoji_usage": "moderate"
            },
            "US West Coast": {
                "language": "en",
                "currency": "USD",
                "date_format": "MM/DD/YYYY",
                "cultural_sensitivity": "high",
                "marketing_style": "progressive",
                "color_preferences": ["green", "blue", "earth_tones"],
                "emoji_usage": "high"
            },
            "US East Coast": {
                "language": "en",
                "currency": "USD",
                "date_format": "MM/DD/YYYY",
                "cultural_sensitivity": "moderate",
                "marketing_style": "professional",
                "color_preferences": ["blue", "navy", "gray"],
                "emoji_usage": "low"
            },
            "UK": {
                "language": "en",
                "currency": "GBP",
                "date_format": "DD/MM/YYYY",
                "cultural_sensitivity": "high",
                "marketing_style": "sophisticated",
                "color_preferences": ["navy", "red", "cream"],
                "emoji_usage": "low"
            },
            "Germany": {
                "language": "de",
                "currency": "EUR",
                "date_format": "DD.MM.YYYY",
                "cultural_sensitivity": "moderate",
                "marketing_style": "precise",
                "color_preferences": ["black", "red", "gold"],
                "emoji_usage": "very_low"
            },
            "France": {
                "language": "fr",
                "currency": "EUR",
                "date_format": "DD/MM/YYYY",
                "cultural_sensitivity": "high",
                "marketing_style": "elegant",
                "color_preferences": ["blue", "white", "red"],
                "emoji_usage": "low"
            },
            "Japan": {
                "language": "ja",
                "currency": "JPY",
                "date_format": "YYYY/MM/DD",
                "cultural_sensitivity": "very_high",
                "marketing_style": "respectful",
                "color_preferences": ["red", "white", "black"],
                "emoji_usage": "very_high"
            },
            "Brazil": {
                "language": "pt",
                "currency": "BRL",
                "date_format": "DD/MM/YYYY",
                "cultural_sensitivity": "moderate",
                "marketing_style": "warm",
                "color_preferences": ["green", "yellow", "blue"],
                "emoji_usage": "high"
            },
            "India": {
                "language": "en",
                "currency": "INR",
                "date_format": "DD/MM/YYYY",
                "cultural_sensitivity": "very_high",
                "marketing_style": "respectful",
                "color_preferences": ["orange", "green", "saffron"],
                "emoji_usage": "moderate"
            },
            "Australia": {
                "language": "en",
                "currency": "AUD",
                "date_format": "DD/MM/YYYY",
                "cultural_sensitivity": "moderate",
                "marketing_style": "casual",
                "color_preferences": ["green", "gold", "blue"],
                "emoji_usage": "moderate"
            }
        }
    
    def _load_language_support(self) -> Dict[str, Dict]:
        """Load language-specific configurations."""
        return {
            "en": {
                "formal_tone": ["professional", "business", "corporate"],
                "casual_tone": ["friendly", "approachable", "relaxed"],
                "marketing_terms": ["offer", "deal", "sale", "discount", "limited time"],
                "cultural_phrases": ["exclusive", "premium", "quality", "value"]
            },
            "de": {
                "formal_tone": ["professionell", "geschäftlich", "unternehmerisch"],
                "casual_tone": ["freundlich", "zugänglich", "entspannt"],
                "marketing_terms": ["Angebot", "Deal", "Verkauf", "Rabatt", "begrenzte Zeit"],
                "cultural_phrases": ["exklusiv", "Premium", "Qualität", "Wert"]
            },
            "fr": {
                "formal_tone": ["professionnel", "commercial", "d'entreprise"],
                "casual_tone": ["amical", "accessible", "décontracté"],
                "marketing_terms": ["offre", "bonne affaire", "vente", "réduction", "durée limitée"],
                "cultural_phrases": ["exclusif", "premium", "qualité", "valeur"]
            },
            "ja": {
                "formal_tone": ["プロフェッショナル", "ビジネス", "企業"],
                "casual_tone": ["フレンドリー", "親しみやすい", "リラックス"],
                "marketing_terms": ["オファー", "お得", "セール", "割引", "期間限定"],
                "cultural_phrases": ["エクスクルーシブ", "プレミアム", "品質", "価値"]
            },
            "pt": {
                "formal_tone": ["profissional", "comercial", "empresarial"],
                "casual_tone": ["amigável", "acessível", "relaxado"],
                "marketing_terms": ["oferta", "negócio", "venda", "desconto", "tempo limitado"],
                "cultural_phrases": ["exclusivo", "premium", "qualidade", "valor"]
            }
        }
    
    def _load_cultural_adaptations(self) -> Dict[str, Dict]:
        """Load cultural adaptation rules."""
        return {
            "US West Coast": {
                "sustainability_focus": True,
                "inclusivity_emphasis": True,
                "tech_savvy": True,
                "outdoor_lifestyle": True,
                "avoid_terms": ["traditional", "conventional", "old-fashioned"]
            },
            "Japan": {
                "respect_hierarchy": True,
                "group_harmony": True,
                "quality_emphasis": True,
                "avoid_terms": ["individual", "aggressive", "direct"],
                "preferred_terms": ["harmony", "quality", "tradition"]
            },
            "Germany": {
                "precision_emphasis": True,
                "quality_focus": True,
                "efficiency_priority": True,
                "avoid_terms": ["vague", "approximate", "maybe"],
                "preferred_terms": ["precise", "quality", "efficient"]
            },
            "Brazil": {
                "warmth_emphasis": True,
                "family_oriented": True,
                "social_connection": True,
                "avoid_terms": ["cold", "impersonal", "distant"],
                "preferred_terms": ["warm", "friendly", "connected"]
            }
        }
    
    def get_regional_config(self, target_market: str) -> Dict:
        """Get configuration for a specific target market."""
        # Try exact match first
        if target_market in self.regional_configs:
            return self.regional_configs[target_market]
        
        # Try partial matching
        for region, config in self.regional_configs.items():
            if region.lower() in target_market.lower() or target_market.lower() in region.lower():
                return config
        
        # Default to US configuration
        return self.regional_configs["US"]
    
    def adapt_message_for_region(self, message: str, target_market: str) -> str:
        """Adapt a message for a specific target market."""
        config = self.get_regional_config(target_market)
        language = config["language"]
        
        # Get language-specific terms
        lang_config = self.language_support.get(language, self.language_support["en"])
        
        # Get cultural adaptations
        cultural_config = self.cultural_adaptations.get(target_market, {})
        
        # Apply cultural adaptations
        adapted_message = message
        
        # Replace terms based on cultural preferences
        if cultural_config.get("avoid_terms"):
            for term in cultural_config["avoid_terms"]:
                if term.lower() in adapted_message.lower():
                    # Find a suitable replacement
                    replacement = self._find_cultural_replacement(term, cultural_config, lang_config)
                    adapted_message = adapted_message.replace(term, replacement)
        
        # Add cultural context if needed
        if cultural_config.get("sustainability_focus") and "sustainable" not in adapted_message.lower():
            adapted_message += " (Sustainable and eco-friendly)"
        
        if cultural_config.get("quality_emphasis") and "quality" not in adapted_message.lower():
            adapted_message += " (Premium quality)"
        
        return adapted_message
    
    def _find_cultural_replacement(self, term: str, cultural_config: Dict, lang_config: Dict) -> str:
        """Find a culturally appropriate replacement for a term."""
        if cultural_config.get("preferred_terms"):
            for preferred in cultural_config["preferred_terms"]:
                if preferred not in term.lower():
                    return preferred
        
        # Fallback to language-appropriate terms
        if "traditional" in term.lower():
            return "classic" if "en" in lang_config else "classic"
        elif "aggressive" in term.lower():
            return "confident" if "en" in lang_config else "confident"
        elif "cold" in term.lower():
            return "professional" if "en" in lang_config else "professional"
        
        return term

class PromptBuilder:
    """Enhanced prompt builder with localization support."""
    
    def __init__(self):
        self.localization_engine = LocalizationEngine()
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load prompt templates for different product categories."""
        return {
            "beverage": "Create a refreshing and appealing image of {product} that conveys {message}. "
                       "Target audience: {audience}. Style: {style}. "
                       "Include elements that suggest refreshment and satisfaction.",
            
            "clothing": "Design a stylish and fashionable image featuring {product} that communicates {message}. "
                       "Target audience: {audience}. Style: {style}. "
                       "Show the product in an attractive, lifestyle-oriented context.",
            
            "electronics": "Generate a modern and innovative image showcasing {product} that highlights {message}. "
                          "Target audience: {audience}. Style: {style}. "
                          "Emphasize technology, innovation, and user experience.",
            
            "food": "Create an appetizing and delicious image of {product} that conveys {message}. "
                    "Target audience: {audience}. Style: {style}. "
                    "Focus on taste, freshness, and culinary appeal.",
            
            "beauty": "Design a beautiful and aspirational image featuring {product} that communicates {message}. "
                     "Target audience: {audience}. Style: {style}. "
                     "Emphasize beauty, confidence, and self-expression.",
            
            "sports": "Generate a dynamic and energetic image showcasing {product} that highlights {message}. "
                     "Target audience: {audience}. Style: {style}. "
                     "Capture movement, energy, and athletic performance.",
            
            "home": "Create a cozy and inviting image featuring {product} that conveys {message}. "
                    "Target audience: {audience}. Style: {style}. "
                    "Show the product in a comfortable, home environment.",
            
            "automotive": "Design a sleek and powerful image showcasing {product} that communicates {message}. "
                         "Target audience: {audience}. Style: {style}. "
                         "Emphasize performance, design, and innovation.",
            
            "default": "Create a professional and engaging marketing image for {product} that conveys {message}. "
                      "Target audience: {audience}. Style: {style}. "
                      "Focus on quality, appeal, and brand alignment."
        }
    
    def _categorize_product(self, product_name: str) -> str:
        """Categorize a product to select appropriate prompt template."""
        product_lower = product_name.lower()
        
        if any(word in product_lower for word in ["water", "bottle", "drink", "beverage", "juice", "soda"]):
            return "beverage"
        elif any(word in product_lower for word in ["shirt", "dress", "pants", "jacket", "hat", "cap", "shoes"]):
            return "clothing"
        elif any(word in product_lower for word in ["phone", "laptop", "computer", "tablet", "camera", "headphones"]):
            return "electronics"
        elif any(word in product_lower for word in ["food", "snack", "meal", "dessert", "fruit", "vegetable"]):
            return "food"
        elif any(word in product_lower for word in ["makeup", "skincare", "perfume", "cosmetic", "beauty"]):
            return "beauty"
        elif any(word in product_lower for word in ["ball", "racket", "equipment", "fitness", "exercise"]):
            return "sports"
        elif any(word in product_lower for word in ["furniture", "decor", "kitchen", "bathroom", "bedroom"]):
            return "home"
        elif any(word in product_lower for word in ["car", "truck", "motorcycle", "vehicle", "automotive"]):
            return "automotive"
        else:
            return "default"
    
    def _determine_style(self, target_market: str, audience: str) -> str:
        """Determine the appropriate visual style based on target market and audience."""
        config = self.localization_engine.get_regional_config(target_market)
        
        # Base style on cultural preferences
        if config["cultural_sensitivity"] == "very_high":
            base_style = "respectful and culturally appropriate"
        elif config["cultural_sensitivity"] == "high":
            base_style = "modern and inclusive"
        else:
            base_style = "contemporary and appealing"
        
        # Add audience-specific styling
        if "young" in audience.lower() or "18-30" in audience:
            base_style += ", vibrant and energetic"
        elif "professional" in audience.lower() or "business" in audience:
            base_style += ", sophisticated and professional"
        elif "family" in audience.lower() or "parents" in audience:
            base_style += ", warm and trustworthy"
        
        # Add regional color preferences
        if config["color_preferences"]:
            color_style = f" using {', '.join(config['color_preferences'][:2])} tones"
            base_style += color_style
        
        return base_style
    
    def build_image_prompt(self, product_name: str, campaign_message: str, target_audience: str, 
                          target_market: str = "US", brand_name: Optional[str] = None, asset_names: Optional[List[str]] = None,
                          brand_palette: Optional[List[str]] = None) -> str:
        """Build a localized image generation prompt."""
        
        # Categorize the product
        category = self._categorize_product(product_name)
        
        # Get appropriate template
        template = self.prompt_templates.get(category, self.prompt_templates["default"])
        
        # Determine visual style
        style = self._determine_style(target_market, target_audience)
        
        # Localize the campaign message
        localized_message = self.localization_engine.adapt_message_for_region(campaign_message, target_market)
        
        # Build the prompt
        prompt = template.format(
            product=product_name,
            message=localized_message,
            audience=target_audience,
            style=style
        )

        # Brand guidance
        if brand_name:
            prompt += (
                f" Adhere to {brand_name} brand aesthetics and design language;"
                f" keep composition brand-safe, reserve subtle logo space,"
                f" and avoid off-brand motifs."
            )

        # Asset-based cues (filenames from inbox like patterns, textures, props)
        if asset_names:
            # Limit to a few distinct hints to avoid overloading prompt
            hints = ", ".join(asset_names[:3])
            prompt += f" Consider visual cues inspired by provided assets: {hints}."

        # Explicit brand palette (hex codes or color names)
        if brand_palette:
            palette_display = ", ".join(brand_palette[:4])
            prompt += f" Favor color palette: {palette_display}."
        
        # Add regional context
        config = self.localization_engine.get_regional_config(target_market)
        if config["language"] != "en":
            prompt += f" Note: This image will be used in {target_market} market."

        return prompt
    
    def build_text_prompt(self, product_name: str, campaign_message: str, target_audience: str,
                         target_market: str = "US", max_length: int = 100) -> str:
        """Build a localized text prompt for copy generation."""
        
        # Localize the campaign message
        localized_message = self.localization_engine.adapt_message_for_region(campaign_message, target_market)
        
        # Get regional configuration
        config = self.localization_engine.get_regional_config(target_market)
        language_config = self.localization_engine.language_support.get(config["language"], 
                                                                     self.localization_engine.language_support["en"])
        
        # Build text prompt
        prompt = f"Create compelling marketing copy for {product_name} with the message: '{localized_message}'. "
        prompt += f"Target audience: {target_audience}. "
        prompt += f"Style: {config['marketing_style']}. "
        prompt += f"Maximum length: {max_length} characters. "
        
        # Add cultural considerations
        if config["cultural_sensitivity"] == "very_high":
            prompt += "Ensure cultural sensitivity and respect for local customs. "
        
        # Add language-specific guidance
        if config["language"] != "en":
            prompt += f"Consider {config['language']} language nuances and cultural context. "
        
        return prompt
    
    def build_localization_report(self, original_message: str, target_markets: List[str]) -> Dict:
        """Generate a report showing how a message would be adapted for different markets."""
        report = {
            "original_message": original_message,
            "localized_versions": {},
            "cultural_considerations": {},
            "recommendations": []
        }
        
        for market in target_markets:
            config = self.localization_engine.get_regional_config(market)
            localized = self.localization_engine.adapt_message_for_region(original_message, market)
            
            report["localized_versions"][market] = {
                "message": localized,
                "language": config["language"],
                "cultural_sensitivity": config["cultural_sensitivity"],
                "marketing_style": config["marketing_style"]
            }
            
            # Add cultural considerations
            cultural_config = self.localization_engine.cultural_adaptations.get(market, {})
            if cultural_config:
                report["cultural_considerations"][market] = cultural_config
        
        # Generate recommendations
        for market, config in report["localized_versions"].items():
            if config["cultural_sensitivity"] == "very_high":
                report["recommendations"].append(
                    f"Consider local cultural review for {market} market"
                )
            
            if config["language"] != "en":
                report["recommendations"].append(
                    f"Ensure professional translation for {market} market"
                )
        
        return report

# Legacy function for backward compatibility
def build_image_prompt(product_name: str, campaign_message: str, target_audience: str) -> str:
    """Legacy function - builds a basic image generation prompt."""
    builder = PromptBuilder()
    return builder.build_image_prompt(product_name, campaign_message, target_audience)
