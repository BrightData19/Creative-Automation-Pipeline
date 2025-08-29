# /apps/pipeline-worker/genai_adapter.py

import os
import requests
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import json

class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        pass

class StubGenerator(BaseGenerator):
    """A stub generator that creates a placeholder image with text."""
    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generates a solid color image with the prompt text drawn on it."""
        img = Image.new('RGB', (width, height), color = (230, 230, 255))
        d = ImageDraw.Draw(img)
        
        try:
            # Use a common font, fallback to default
            font = ImageFont.truetype("Arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()

        # Simple text wrapping
        lines = []
        words = prompt.split()
        current_line = ""
        for word in words:
            if len(current_line + word) < (width // (font.size // 2)):
                current_line += f" {word}"
            else:
                lines.append(current_line.strip())
                current_line = word
        lines.append(current_line.strip())

        text_y = (height - len(lines) * font.size) / 2
        for line in lines:
            text_width = d.textlength(line, font=font)
            text_x = (width - text_width) / 2
            d.text((text_x, text_y), line, fill=(0,0,0), font=font)
            text_y += font.size
            
        return img


def _parse_variation_directives(text: str):
    """Extract variation directives appended by the pipeline and return (clean_text, directives).

    Looks for sections like:
    "Variation directives: a; b; c. Ensure this attempt differs ..."
    """
    marker = "Variation directives:"
    ensure_marker = "Ensure this attempt differs"
    directives = []
    cleaned = text

    if marker in text:
        before, after = text.split(marker, 1)
        cleaned = before.strip()
        # Remove any retry hint from the directives region
        if ensure_marker in after:
            directives_region, _ = after.split(ensure_marker, 1)
        else:
            directives_region = after
        # Split on semicolons and periods
        parts = [p.strip(" .") for p in directives_region.split(";")]
        directives = [p for p in parts if p]

    # Remove trailing retry hint if it leaked into the base text
    if ensure_marker in cleaned:
        cleaned = cleaned.split(ensure_marker, 1)[0].strip()

    return cleaned, directives


def _enhance_prompt(raw_prompt: str, width: int, height: int) -> str:
    """Compose a richer, brand-safe generation prompt for providers.

    Adds composition, lighting, color and constraints, and folds in any
    agent-provided variation directives detected in the raw prompt.
    """
    base, directives = _parse_variation_directives(raw_prompt)

    variation_block = ""
    if directives:
        bullets = "\n".join([f"- {d}" for d in directives])
        variation_block = f"\nVariation goals:\n{bullets}\n"

    return (
        "Create a brand-safe, high-quality marketing image.\n"
        f"Subject and goal: {base}\n\n"
        "Composition:\n"
        "- Keep the primary subject centered and large enough that key details remain inside the central safe area.\n"
        "- Ensure all critical elements fit within the middle 60% of the frame (crop-safe for 1:1, 16:9, 9:16).\n"
        "- Maintain 10–15% padding from all edges; avoid placing small or important elements near edges or corners.\n"
        "- Clean, uncluttered background; allow negative space around the centered subject.\n"
        "- Reserve subtle negative space near a corner (e.g., top-right) for a future brand mark; do not place any text or logo.\n\n"
        "Style and lighting:\n"
        "- Photorealistic, professional marketing style with natural or soft studio light, realistic shadows, high detail.\n"
        "- Sharp focus on the subject; tasteful depth-of-field; avoid visual noise.\n\n"
        "Color:\n"
        "- Harmonize with brand-appropriate palettes; avoid neon oversaturation and clashing tones.\n\n"
        "Constraints:\n"
        "- No on-image text, captions, watermarks, QR codes, or trademarks.\n"
        "- No unsafe content (nudity, violence, hate symbols).\n\n"
        "Output:\n"
        f"- Social-ad ready, {width}x{height} px, high resolution, clean edges; centered-subject crop-safe for 1:1, 16:9, 9:16.\n"
        + variation_block
    )

class GoogleGeminiGenerator(BaseGenerator):
    """Google Gemini 2.5 Flash Image generator implementation."""
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent"
        
        if not self.api_key:
            print("GOOGLE_GEMINI_API_KEY not found. Gemini generator will not be available.")
            self.api_key = None

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        if not self.api_key:
            print("Gemini API key not available. Falling back to stub generation.")
            return StubGenerator().generate(prompt, width, height)

        try:
            # Gemini 2.0 Flash Image supports specific dimensions
            # Map our dimensions to supported Gemini sizes
            gemini_width, gemini_height = self._map_dimensions_to_gemini(width, height)
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": _enhance_prompt(prompt, gemini_width, gemini_height)
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                ]
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract image data from Gemini response
                # Note: This is a simplified implementation - actual Gemini 2.0 Flash Image
                # response structure may differ and needs to be adapted based on actual API
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                                image_data = base64.b64decode(part["inlineData"]["data"])
                                img = Image.open(io.BytesIO(image_data))
                                # Resize to requested dimensions
                                img = img.resize((width, height), Image.Resampling.LANCZOS)
                                return img
                
                print("No image data found in Gemini response. Falling back to stub generation.")
                return StubGenerator().generate(prompt, width, height)
            else:
                print(f"Gemini API request failed: {response.status_code} - {response.text}")
                return StubGenerator().generate(prompt, width, height)
                
        except Exception as e:
            print(f"Error generating image with Gemini: {e}")
            return StubGenerator().generate(prompt, width, height)

    def generate_from_image(self, base_image: Image.Image, instructions: str, width: int, height: int) -> Image.Image:
        """Edit/enhance an existing image using Gemini 2.5 Flash Image preview.

        If the API isn't available, simply return the original (resized) image.
        """
        if not self.api_key:
            return base_image.resize((width, height), Image.Resampling.LANCZOS)
        try:
            from base64 import b64encode
            import io
            buf = io.BytesIO()
            base_image.save(buf, format="JPEG", quality=92)
            buf.seek(0)
            img_b64 = b64encode(buf.read()).decode("utf-8")

            gemini_width, gemini_height = self._map_dimensions_to_gemini(width, height)

            payload = {
                "contents": [{
                    "parts": [
                        {"text": _enhance_prompt(instructions, gemini_width, gemini_height)},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": img_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.5,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json=payload,
                headers=headers,
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                                image_data = base64.b64decode(part["inlineData"]["data"])
                                img = Image.open(io.BytesIO(image_data))
                                return img.resize((width, height), Image.Resampling.LANCZOS)
            # fallback: return original resized
            return base_image.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Gemini image edit failed: {e}")
            return base_image.resize((width, height), Image.Resampling.LANCZOS)
    
    def _map_dimensions_to_gemini(self, width: int, height: int) -> tuple[int, int]:
        """Map requested dimensions to Gemini-supported sizes."""
        # Gemini 2.0 Flash Image supports various dimensions
        # For now, we'll use the closest supported size
        if width == 1080 and height == 1080:
            return 1024, 1024
        elif width == 1920 and height == 1080:
            return 1792, 1024
        elif width == 1080 and height == 1920:
            return 1024, 1792
        else:
            # Default to 1024x1024 and let the system resize
            return 1024, 1024

class AdobeFireflyGenerator(BaseGenerator):
    """Adobe Firefly generator implementation."""
    def __init__(self):
        self.client_id = os.getenv("ADOBE_FIREFLY_CLIENT_ID")
        self.client_secret = os.getenv("ADOBE_FIREFLY_CLIENT_SECRET")
        self.access_token = None
        
        if not self.client_id or not self.client_secret:
            print("ADOBE_FIREFLY_CLIENT_ID or ADOBE_FIREFLY_CLIENT_SECRET not found. Firefly generator will not be available.")
            self.client_id = None
            self.client_secret = None

    def _get_access_token(self) -> str:
        """Get Adobe access token using client credentials."""
        if not self.client_id or not self.client_secret:
            raise Exception("Adobe credentials not configured")
        
        if self.access_token:
            return self.access_token
        
        token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid,AdobeID,firefly_api"
        }
        
        response = requests.post(token_url, data=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            self.access_token = result["access_token"]
            return self.access_token
        else:
            raise Exception(f"Failed to get Adobe access token: {response.status_code}")

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        if not self.client_id or not self.client_secret:
            print("Adobe Firefly credentials not available. Falling back to stub generation.")
            return StubGenerator().generate(prompt, width, height)
        
        try:
            access_token = self._get_access_token()
            
            # Adobe Firefly API endpoint
            api_url = "https://api.adobe.com/firefly/v1/images/generate"
            
            # Map dimensions to Firefly-supported sizes
            firefly_width, firefly_height = self._map_dimensions_to_firefly(width, height)
            
            payload = {
                "prompt": _enhance_prompt(prompt, firefly_width, firefly_height),
                "width": firefly_width,
                "height": firefly_height,
                "contentClass": "photo",
                "style": "photographic",
                "n": 1
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "x-api-key": self.client_id
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if "outputs" in result and len(result["outputs"]) > 0:
                    output = result["outputs"][0]
                    if "image" in output:
                        image_url = output["image"]["url"]
                        # Download the generated image
                        img_response = requests.get(image_url, timeout=30)
                        if img_response.status_code == 200:
                            img = Image.open(io.BytesIO(img_response.content))
                            # Resize to requested dimensions
                            img = img.resize((width, height), Image.Resampling.LANCZOS)
                            return img
                
                print("No image data found in Firefly response. Falling back to stub generation.")
                return StubGenerator().generate(prompt, width, height)
            else:
                print(f"Adobe Firefly API request failed: {response.status_code} - {response.text}")
                return StubGenerator().generate(prompt, width, height)
                
        except Exception as e:
            print(f"Error generating image with Adobe Firefly: {e}")
            return StubGenerator().generate(prompt, width, height)
    
    def _map_dimensions_to_firefly(self, width: int, height: int) -> tuple[int, int]:
        """Map requested dimensions to Firefly-supported sizes."""
        # Firefly supports various dimensions, but let's use standard sizes
        if width == 1080 and height == 1080:
            return 1024, 1024
        elif width == 1920 and height == 1080:
            return 1792, 1024
        elif width == 1080 and height == 1920:
            return 1024, 1792
        else:
            # Default to 1024x1024 and let the system resize
            return 1024, 1024

class OpenAIGenerator(BaseGenerator):
    """OpenAI DALL-E 3 generator implementation."""
    def __init__(self):
        # This will fail if the openai library isn't installed or API key is missing
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except (ImportError, KeyError):
            print("Could not initialize OpenAIGenerator. Make sure 'openai' is installed and OPENAI_API_KEY is set.")
            self.client = None

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        if not self.client:
            print("OpenAI client not available. Falling back to stub generation.")
            return StubGenerator().generate(prompt, width, height)
        
        # DALL-E 3 requires specific sizes
        # This is a simplification; a real implementation would handle this better
        size_str = "1024x1024" # Default
        if width == 1920 and height == 1080:
            size_str = "1792x1024"
        elif width == 1080 and height == 1920:
            size_str = "1024x1792"

        enhanced = _enhance_prompt(prompt, width, height)
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=enhanced,
            size=size_str,
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        # Download the image from the URL
        import requests
        from PIL import Image
        import io
        
        res = requests.get(image_url)
        img = Image.open(io.BytesIO(res.content))
        return img

class IntelligentGenerator(BaseGenerator):
    """Intelligent generator that selects the best available provider and implements fallback logic."""
    
    def __init__(self):
        self.providers = []
        self.provider_weights = {}
        
        # Initialize available providers with weights
        if os.getenv("GOOGLE_GEMINI_API_KEY"):
            self.providers.append(("gemini", GoogleGeminiGenerator(), 0.4))
            print("Google Gemini 2.5 Flash Image generator available")
        
        if os.getenv("ADOBE_FIREFLY_CLIENT_ID") and os.getenv("ADOBE_FIREFLY_CLIENT_SECRET"):
            self.providers.append(("firefly", AdobeFireflyGenerator(), 0.35))
            print("Adobe Firefly generator available")
        
        if os.getenv("OPENAI_API_KEY"):
            self.providers.append(("openai", OpenAIGenerator(), 0.25))
            print("OpenAI DALL-E 3 generator available")
        
        # Always add stub generator as fallback
        self.providers.append(("stub", StubGenerator(), 0.0))
        
        if len(self.providers) == 1:  # Only stub available
            print("Warning: Only stub generator available. Please configure at least one GenAI provider.")
        else:
            print(f"Initialized {len(self.providers)-1} GenAI providers with intelligent fallback")

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generate image using the best available provider with fallback logic."""
        
        # Try providers in order of preference (excluding stub)
        for provider_name, provider, weight in self.providers[:-1]:
            try:
                print(f"Attempting generation with {provider_name}...")
                result = provider.generate(prompt, width, height)
                if result and result.size == (width, height):
                    print(f"Successfully generated image with {provider_name}")
                    return result
                else:
                    print(f"{provider_name} returned invalid image, trying next provider...")
            except Exception as e:
                print(f"Error with {provider_name}: {e}, trying next provider...")
                continue
        
        # Fallback to stub generator
        print("All GenAI providers failed, using stub generator")
        return self.providers[-1][1].generate(prompt, width, height)

def get_generator(name: str = "intelligent") -> BaseGenerator:
    """Get a generator instance. Defaults to intelligent provider selection."""
    if name.lower() == "gemini":
        return GoogleGeminiGenerator()
    elif name.lower() == "firefly":
        return AdobeFireflyGenerator()
    elif name.lower() == "openai":
        return OpenAIGenerator()
    elif name.lower() == "stub":
        return StubGenerator()
    elif name.lower() == "intelligent":
        return IntelligentGenerator()
    else:
        print(f"Unknown generator '{name}', using intelligent selection")
        return IntelligentGenerator()
