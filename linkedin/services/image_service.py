"""
ImageService: Generates and processes images using the AI Router.
"""
import io
import json
import logging
import os
import uuid
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from linkedin.models import LinkedInProfile, GeneratedPost
from linkedin.services.prompt_engine import PromptEngine
from linkedin.services.ai_router import AIRouter

logger = logging.getLogger(__name__)

# Image dimensions optimized for LinkedIn
LINKEDIN_IMAGE_WIDTH = 1200
LINKEDIN_IMAGE_HEIGHT = 628
IMAGES_DIR = Path("media/linkedin/images")


class ImageService:

    def __init__(self):
        self.router = AIRouter()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def generate_for_post(
        self,
        profile: LinkedInProfile,
        post_text: str,
        post_type: str,
        visual_brief: dict = None
    ) -> dict:
        """
        Full pipeline: post text → visual brief → image prompt → image → processed image.
        Returns dict with image_url, image_local_path, image_prompt_used,
                         image_format, image_emotion, image_metaphor, image_color_palette.
        """
        # Step 1: Get visual brief if not provided
        if not visual_brief:
            from linkedin.services.content_service import ContentService
            content_svc = ContentService()
            visual_brief = content_svc.generate_visual_brief(post_text, post_type)

        # Step 2: Build DALL-E prompt
        image_format = visual_brief.get("image_format", "abstract_scene")
        dalle_prompt = PromptEngine.build_dalle_prompt(
            visual_brief=visual_brief,
            image_format=image_format,
            brand_primary=profile.brand_primary_color,
            brand_secondary=profile.brand_secondary_color,
            user_watermark=profile.brand_watermark_text,
        )

        # Step 3: Generate image using AI Router
        response = self.router.generate_image(
            task="image_generation",
            prompt=dalle_prompt,
        )

        image_url = response["image_url"]

        # Step 4: Download and post-process the image
        local_path = self._download_and_process(
            image_url=image_url,
            watermark_text=profile.brand_watermark_text,
            primary_color=profile.brand_primary_color,
        )

        palette = visual_brief.get("suggested_palette", {})
        color_str = f"{palette.get('background', '')} / {palette.get('accent', '')}"

        logger.info(f"Generated image for profile {profile.id}, format: {image_format}")

        return {
            "image_url": image_url,
            "image_local_path": str(local_path),
            "image_prompt_used": dalle_prompt,
            "image_format": image_format,
            "image_emotion": visual_brief.get("core_emotion", ""),
            "image_metaphor": visual_brief.get("key_metaphor", ""),
            "image_color_palette": color_str,
            "image_model_used": response.get("model", ""),
            "image_provider": response.get("provider", ""),
            "cost_usd": response.get("cost_usd", 0),
        }

    def _download_and_process(
        self,
        image_url: str,
        watermark_text: str = "",
        primary_color: str = "#1B4F72"
    ) -> Path:
        """Download DALL-E image, resize to LinkedIn optimal, add subtle watermark."""

        # Download image
        response = httpx.get(image_url, timeout=30)
        response.raise_for_status()

        img = Image.open(io.BytesIO(response.content))

        # Resize to LinkedIn optimal dimensions
        img = img.resize(
            (LINKEDIN_IMAGE_WIDTH, LINKEDIN_IMAGE_HEIGHT),
            Image.Resampling.LANCZOS
        )

        # Add subtle watermark/branding if configured
        if watermark_text:
            img = self._add_watermark(img, watermark_text, primary_color)

        # Save locally
        filename = f"{uuid.uuid4()}.png"
        local_path = IMAGES_DIR / filename
        img.save(local_path, "PNG", optimize=True, quality=95)

        return local_path

    def _add_watermark(self, img: Image.Image, text: str, color: str) -> Image.Image:
        """Add subtle text watermark to bottom-right corner."""
        draw = ImageDraw.Draw(img)

        # Use default font (in production, load a custom font)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except (IOError, OSError):
            font = ImageFont.load_default()

        # Position: bottom-right
        margin = 15
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = img.width - text_width - margin
        y = img.height - text_height - margin

        # Semi-transparent white text
        draw.text((x, y), text, fill=(255, 255, 255, 180), font=font)

        return img