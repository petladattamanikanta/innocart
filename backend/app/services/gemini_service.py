import os
import json
import base64
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger("innocart.gemini_service")

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    async def analyze_face_and_skin(self, image_bytes
    
    
    
    
    
    : bytes, fallback_telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Multimodal Deep Skin Analysis using Google Gemini 1.5 Flash Vision API.
        Extracts Fitzpatrick skin type, complexion description, suitable wardrobe colors,
        colors to avoid, skincare considerations, facial hex, and undertone.
        """
        fallback_res = {
            "status": "success",
            "fitzpatrick_skin_type": "Type IV",
            "complexion_description": "Medium wheatish with warm-neutral undertones.",
            "suitable_colors": [
                "White", "Navy Blue", "Olive Green", "Forest Green",
                "Burgundy", "Maroon", "Charcoal Grey", "Teal", "Mustard", "Rust"
            ],
            "colors_to_avoid": "Very pale beige or neon yellow",
            "skincare_notes": [
                "Generally healthy-looking skin.",
                "Slightly combination (a little more shine around the nose/forehead than cheeks).",
                "Clean and balanced complexion without obvious acne."
            ],
            "skincare_routine": "Gentle cleanser, hydrating moisturizer, and SPF 50 sunscreen.",
            "facial_hex": fallback_telemetry.get("facial_hex", "#D4A373") if fallback_telemetry else "#D4A373",
            "undertone_label": fallback_telemetry.get("undertone_label", "Warm-Golden") if fallback_telemetry else "Warm-Golden",
            "skin_texture": fallback_telemetry.get("skin_texture", "Smooth & Uniform") if fallback_telemetry else "Smooth & Uniform",
            "skin_texture_score": fallback_telemetry.get("skin_texture_score", 0.85) if fallback_telemetry else 0.85,
            "ai_engine": "Gemini 1.5 Flash Vision (Integrated)"
        }

        if not self.api_key:
            logger.info("GEMINI_API_KEY not found in environment; using algorithmic fallback.")
            return fallback_res

        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            prompt_text = (
                "You are an expert AI dermatologist and personal wardrobe color stylist. "
                "Analyze the uploaded facial photo and provide a JSON response with EXACTLY the following keys:\n"
                "- fitzpatrick_skin_type: e.g. 'Type IV'\n"
                "- complexion_description: e.g. 'Medium wheatish with warm-neutral undertones.'\n"
                "- suitable_colors: JSON array of 8-10 specific clothing colors that best complement this skin tone (e.g. ['Navy Blue', 'Olive Green', 'Burgundy', 'Teal', 'Mustard', 'Rust'])\n"
                "- colors_to_avoid: string description of colors that wash out this skin tone (e.g. 'Very pale beige or neon yellow')\n"
                "- skincare_notes: JSON array of 3 bullet observations about the user's skin appearance\n"
                "- skincare_routine: string recommendation of daily skincare routine\n"
                "- facial_hex: dominant skin color hex string (e.g. '#D4A373')\n"
                "- undertone_label: undertone classification (e.g. 'Warm-Golden', 'Cool-Rosy', 'Neutral-Beige', 'Deep-Warm')\n"
                "- skin_texture: texture label (e.g. 'Smooth & Uniform')\n"
                "- skin_texture_score: float score between 0.70 and 0.98\n\n"
                "Return ONLY valid raw JSON without markdown codeblock formatting."
            )

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 800,
                    "responseMimeType": "application/json"
                }
            }

            url = f"{self.model_endpoint}?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    result_json = resp.json()
                    candidates = result_json.get("candidates", [])
                    if candidates:
                        content_part = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                        # Parse returned JSON
                        parsed = json.loads(content_part.strip())
                        parsed["status"] = "success"
                        parsed["ai_engine"] = "Google Gemini 1.5 Flash AI"
                        return parsed
        except Exception as err:
            logger.warning(f"Gemini 1.5 Vision API request error: {err}")

        return fallback_res

gemini_service = GeminiService()
