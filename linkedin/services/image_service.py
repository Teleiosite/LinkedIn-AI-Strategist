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
        try:
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
            image_model_used = response.get("model", "")
            image_provider = response.get("provider", "")
            cost_usd = response.get("cost_usd", 0)

        except Exception as e:
            logger.warning(
                f"[ImageService] AI image generation failed: {e}. "
                f"Generating a beautiful local branded fallback graphic."
            )
            local_path = self.generate_local_fallback_graphic(
                profile=profile,
                visual_brief=visual_brief,
                image_format=image_format
            )
            image_url = f"/media/linkedin/images/{local_path.name}"
            image_model_used = "pillow-fallback-v1"
            image_provider = "local"
            cost_usd = 0.0

        palette = visual_brief.get("suggested_palette", {})
        color_str = f"{palette.get('background', '')} / {palette.get('accent', '')}"

        logger.info(f"Generated visual for profile {profile.id}, format: {image_format} (Provider: {image_provider})")

        return {
            "image_url": image_url,
            "image_local_path": str(local_path),
            "image_prompt_used": dalle_prompt,
            "image_format": image_format,
            "image_emotion": visual_brief.get("core_emotion", ""),
            "image_metaphor": visual_brief.get("key_metaphor", ""),
            "image_color_palette": color_str,
            "image_model_used": image_model_used,
            "image_provider": image_provider,
            "cost_usd": cost_usd,
        }

    def generate_local_fallback_graphic(
        self,
        profile: LinkedInProfile,
        visual_brief: dict,
        image_format: str
    ) -> Path:
        """
        Generates a visually stunning, custom-branded abstract image locally using Pillow
        as a fallback when no external image generation API keys are available.
        """
        from PIL import ImageColor
        import re

        # Determine colors from visual brief palette or profile branding
        palette = visual_brief.get("suggested_palette", {})

        def clean_hex(color_str, default):
            if not color_str:
                return default
            color_str = str(color_str).strip()
            if not color_str.startswith("#"):
                color_str = "#" + color_str
            if re.match(r"^#[0-9a-fA-F]{3,8}$", color_str):
                return color_str
            return default

        bg_hex = clean_hex(palette.get("background") or profile.brand_primary_color, "#1B2631")
        accent_hex = clean_hex(palette.get("accent") or profile.brand_secondary_color, "#F39C12")
        mid_hex = clean_hex(palette.get("midtone") or profile.brand_secondary_color, "#2C3E50")

        c1 = ImageColor.getrgb(bg_hex)
        c2 = ImageColor.getrgb(mid_hex)
        c_accent = ImageColor.getrgb(accent_hex)

        # 1. Create linear gradient background
        img = Image.new("RGBA", (LINKEDIN_IMAGE_WIDTH, LINKEDIN_IMAGE_HEIGHT))
        draw = ImageDraw.Draw(img)

        # Draw gradient from top-left to bottom-right (horizontal lines is fast enough for vertical gradient)
        for y in range(LINKEDIN_IMAGE_HEIGHT):
            t = y / LINKEDIN_IMAGE_HEIGHT
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            draw.line([(0, y), (LINKEDIN_IMAGE_WIDTH, y)], fill=(r, g, b, 255))

        # 2. Draw modern abstract shapes based on image_format rules
        overlay = Image.new("RGBA", (LINKEDIN_IMAGE_WIDTH, LINKEDIN_IMAGE_HEIGHT), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        if image_format == "before_after":
            # Draw vertical separation and contrast
            # Left half: chaotic/dark overlay
            draw_ov.rectangle([0, 0, LINKEDIN_IMAGE_WIDTH // 2, LINKEDIN_IMAGE_HEIGHT], fill=(0, 0, 0, 60))
            # Right half: bright geometric shapes
            draw_ov.ellipse([LINKEDIN_IMAGE_WIDTH * 0.6, LINKEDIN_IMAGE_HEIGHT * 0.2, LINKEDIN_IMAGE_WIDTH * 0.9, LINKEDIN_IMAGE_HEIGHT * 0.8], fill=(c_accent[0], c_accent[1], c_accent[2], 80))
            draw_ov.line([(LINKEDIN_IMAGE_WIDTH // 2, 0), (LINKEDIN_IMAGE_WIDTH // 2, LINKEDIN_IMAGE_HEIGHT)], fill=(255, 255, 255, 40), width=3)

        elif image_format == "symbolic_object":
            # Draw a sleek centered badge (circle/polygon) acting as a modern icon
            center_x = LINKEDIN_IMAGE_WIDTH // 2
            center_y = LINKEDIN_IMAGE_HEIGHT // 2
            r = 120
            # Outer ring
            draw_ov.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], outline=(255, 255, 255, 120), width=4)
            # Inner circle
            draw_ov.ellipse([center_x - r + 15, center_y - r + 15, center_x + r - 15, center_y + r - 15], fill=(c_accent[0], c_accent[1], c_accent[2], 120))

        elif image_format == "infographic_art":
            # Draw abstract charts/bar graphics
            start_y = LINKEDIN_IMAGE_HEIGHT - 100
            bar_width = 80
            gap = 40
            x_offset = (LINKEDIN_IMAGE_WIDTH - (4 * bar_width + 3 * gap)) // 2
            heights = [180, 280, 220, 350]
            for idx, h in enumerate(heights):
                bx = x_offset + idx * (bar_width + gap)
                # Draw rounded bar
                draw_ov.rectangle([bx, start_y - h, bx + bar_width, start_y], fill=(c_accent[0], c_accent[1], c_accent[2], 150))
                draw_ov.rectangle([bx, start_y - h, bx + bar_width, start_y - h + 15], fill=(255, 255, 255, 100))

        elif image_format == "bold_statement":
            # Draw bold diagonal stripe layout
            draw_ov.polygon([
                (LINKEDIN_IMAGE_WIDTH * 0.4, 0),
                (LINKEDIN_IMAGE_WIDTH * 0.8, 0),
                (LINKEDIN_IMAGE_WIDTH * 0.6, LINKEDIN_IMAGE_HEIGHT),
                (LINKEDIN_IMAGE_WIDTH * 0.2, LINKEDIN_IMAGE_HEIGHT)
            ], fill=(c_accent[0], c_accent[1], c_accent[2], 90))

        else: # default "abstract_scene"
            # Draw floating geometric circles and triangles
            draw_ov.ellipse([LINKEDIN_IMAGE_WIDTH * 0.1, LINKEDIN_IMAGE_HEIGHT * 0.1, LINKEDIN_IMAGE_WIDTH * 0.4, LINKEDIN_IMAGE_HEIGHT * 0.7], fill=(c_accent[0], c_accent[1], c_accent[2], 60))
            draw_ov.polygon([
                (LINKEDIN_IMAGE_WIDTH * 0.5, LINKEDIN_IMAGE_HEIGHT * 0.2),
                (LINKEDIN_IMAGE_WIDTH * 0.85, LINKEDIN_IMAGE_HEIGHT * 0.1),
                (LINKEDIN_IMAGE_WIDTH * 0.7, LINKEDIN_IMAGE_HEIGHT * 0.75)
            ], fill=(255, 255, 255, 25))

        # Combine image and overlay
        img = Image.alpha_composite(img, overlay)
        img = img.convert("RGB")

        # Add watermark
        if profile.brand_watermark_text:
            img = self._add_watermark(img, profile.brand_watermark_text, profile.brand_primary_color)

        # Add a subtle label
        draw_label = ImageDraw.Draw(img)
        try:
            label_font = ImageFont.truetype("arial.ttf", 14)
        except (IOError, OSError):
            label_font = ImageFont.load_default()
        draw_label.text((30, 30), f"STRATEGY VISUAL // {visual_brief.get('core_emotion', 'clarity').upper()}", fill=(255, 255, 255, 120), font=label_font)

        # Save locally
        filename = f"fallback_{uuid.uuid4()}.png"
        local_path = IMAGES_DIR / filename
        img.save(local_path, "PNG", optimize=True, quality=95)

        return local_path

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