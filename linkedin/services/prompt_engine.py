"""
PromptEngine: All GPT-4o and DALL-E 3 prompts for LinkedIn content.
This is the core intellectual property of the product.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserContext:
    goal: str                    # get_job, get_clients, build_brand, grow_business
    industry: str
    role: str
    skills: list[str]
    bio: str
    location: str
    brand_primary_color: str     # hex e.g. #1B4F72
    brand_secondary_color: str   # hex e.g. #F39C12


@dataclass
class PostBrief:
    post_type: str
    core_message: str
    target_audience: str
    tone: str
    avoid: str = ""


# ─────────────────────────────────────────────
# EMOTION → COLOR PALETTE MAPPING
# ─────────────────────────────────────────────
EMOTION_PALETTES = {
    "confidence":   {"bg": "#1B2631", "accent": "#F39C12", "mid": "#2C3E50"},
    "reflection":   {"bg": "#2C3E50", "accent": "#85929E", "mid": "#566573"},
    "energy":       {"bg": "#1A1A2E", "accent": "#0F3460", "mid": "#16213E"},
    "trust":        {"bg": "#1B4F35", "accent": "#A9DFBF", "mid": "#196F3D"},
    "authority":    {"bg": "#0D0D0D", "accent": "#E8E8E8", "mid": "#1C1C1C"},
    "warmth":       {"bg": "#2E1A0E", "accent": "#E67E22", "mid": "#6E2F1A"},
    "ambition":     {"bg": "#1A0033", "accent": "#9B59B6", "mid": "#6C3483"},
    "clarity":      {"bg": "#0A2342", "accent": "#2E86AB", "mid": "#1B4F72"},
}

# ─────────────────────────────────────────────
# POST TYPE → EMOTION MAPPING
# ─────────────────────────────────────────────
POST_EMOTION_MAP = {
    "thought_leadership": "authority",
    "personal_story":     "warmth",
    "industry_insight":   "clarity",
    "achievement":        "confidence",
    "tip_framework":      "trust",
    "hot_take":           "energy",
    "case_study":         "confidence",
}

# ─────────────────────────────────────────────
# IMAGE FORMAT → VISUAL RULES
# ─────────────────────────────────────────────
IMAGE_FORMAT_RULES = {
    "abstract_scene": {
        "instruction": "A symbolic scene rendered in flat geometric shapes. "
                       "One or two abstract figures or forms that communicate the emotion. "
                       "No text in image. No realistic faces or human anatomy.",
        "style": "flat geometric shapes, bold contrast, minimalist, symbolic",
    },
    "bold_statement": {
        "instruction": "An abstract gradient or textured background with powerful geometric forms. "
                       "NO text in the image itself. The background should feel electric and bold.",
        "style": "bold abstract background, high contrast, electric energy",
    },
    "before_after": {
        "instruction": "Split composition. Left half: dark, chaotic, fragmented geometric shapes "
                       "representing struggle or the old state. Right half: clean, ordered, "
                       "luminous geometric shapes representing the solution or new state. "
                       "A subtle dividing line in the center.",
        "style": "split composition, dark-to-light transition, geometric contrast",
    },
    "infographic_art": {
        "instruction": "Abstract data visualization art. Numbers, bars, or circles "
                       "used as pure design elements — not real data. Beautiful and ordered. "
                       "Conveys structure, progress, or ranking through visual hierarchy.",
        "style": "data visualization art, ordered hierarchy, geometric precision",
    },
    "symbolic_object": {
        "instruction": "A single iconic object rendered in flat abstract style, centered in frame. "
                       "The object should be a universal symbol relevant to the post message. "
                       "Examples: a key, compass, bridge, seed, mountain peak, lighthouse. "
                       "Surrounded by minimal geometric environment.",
        "style": "single centered symbolic object, flat abstract, iconic",
    },
}


class PromptEngine:

    # ─────────────────────────────────────────────
    # POST GENERATION PROMPTS
    # ─────────────────────────────────────────────

    @classmethod
    def get_system_prompt(cls, ctx: UserContext) -> str:
        goal_context = {
            "get_job": "attract recruiters and hiring managers, demonstrate expertise, and get noticed for opportunities",
            "get_clients": "attract ideal clients, demonstrate value, and generate inbound leads",
            "build_brand": "establish thought leadership, grow followers, and become a recognized voice in your industry",
            "grow_business": "drive business growth, attract partners, clients, and talent",
        }
        return f"""You are a world-class LinkedIn content strategist and ghostwriter.

Your client's profile:
- Goal: {goal_context.get(ctx.goal, ctx.goal)}
- Industry: {ctx.industry}
- Role: {ctx.role}
- Key Skills: {', '.join(ctx.skills)}
- Bio: {ctx.bio}
- Location: {ctx.location}

Your writing rules:
1. Always start with a scroll-stopping hook (first line must create curiosity or strong emotion)
2. Write in short paragraphs — maximum 3 lines per paragraph
3. Use line breaks liberally for readability
4. Write in first person, authentic voice — never corporate speak
5. End with a clear, specific call to action or question
6. Include 3-5 relevant hashtags at the end
7. Total length: 150-300 words
8. NEVER use: "I'm excited to share", "In today's world", "Thrilled to announce", "Game-changer"
9. Write like a human who has lived the experience — specific details, real emotions
10. The post must serve the reader first, the author second"""

    @classmethod
    def get_post_generation_prompt(cls, post_type: str, recent_topics: list[str] = None) -> str:
        avoid_topics = ""
        if recent_topics:
            avoid_topics = f"\n\nAVOID these topics (already posted recently): {', '.join(recent_topics)}"

        type_instructions = {
            "thought_leadership": "Share a contrarian or non-obvious insight about your industry. "
                                  "Challenge conventional wisdom with a specific example.",
            "personal_story":     "Share a specific moment of failure, learning, or transformation. "
                                  "Be vulnerable. Include what you learned and how it changed you.",
            "industry_insight":   "Share a data point, trend, or observation that your target audience "
                                  "would find surprising and immediately useful.",
            "achievement":        "Share a specific win — for yourself or a client. "
                                  "Lead with the result, then explain the process.",
            "tip_framework":      "Share a 3-5 step framework or tip that your audience can apply immediately. "
                                  "Make it ultra-specific and actionable.",
            "hot_take":           "Share a strong opinion that goes against common advice in your field. "
                                  "Back it up with your specific reasoning.",
            "case_study":         "Walk through a before/after story. What was the problem, "
                                  "what was the solution, what were the measurable results.",
        }

        return f"""Write a LinkedIn post of type: {post_type.upper()}

Instruction: {type_instructions.get(post_type, '')}
{avoid_topics}

Return your response in this exact JSON format:
{{
    "hook": "The first line of the post (scroll-stopper)",
    "post_text": "The full post text including the hook",
    "hashtags": "#hashtag1 #hashtag2 #hashtag3",
    "core_message": "One sentence summary of the post's main message",
    "target_emotion": "The primary emotion this post evokes in the reader"
}}"""

    # ─────────────────────────────────────────────
    # IMAGE GENERATION PROMPTS
    # ─────────────────────────────────────────────

    @classmethod
    def get_visual_brief_prompt(cls, post_text: str, post_type: str) -> str:
        emotion = POST_EMOTION_MAP.get(post_type, "clarity")
        palette = EMOTION_PALETTES.get(emotion, EMOTION_PALETTES["clarity"])

        return f"""Analyze this LinkedIn post and create a visual brief for an abstract image.

POST:
{post_text}

You must return JSON in this exact format:
{{
    "core_emotion": "one word describing the dominant emotion",
    "key_metaphor": "the visual metaphor that best represents the post message",
    "symbolic_element": "one specific object or scene element to anchor the image",
    "color_mood": "the emotional mood for color selection",
    "suggested_palette": {{
        "background": "{palette['bg']}",
        "accent": "{palette['accent']}",
        "midtone": "{palette['mid']}"
    }},
    "image_format": "one of: abstract_scene, bold_statement, before_after, infographic_art, symbolic_object",
    "avoid": "specific things to avoid in the image that would feel wrong for this post"
}}

Rules for your response:
- The metaphor must visually communicate the post message WITHOUT being literal
- Choose image_format based on what will be most impactful for this specific post
- The symbolic element should be universally understood"""

    @classmethod
    def build_dalle_prompt(
        cls,
        visual_brief: dict,
        image_format: str,
        brand_primary: str,
        brand_secondary: str,
        user_watermark: str = ""
    ) -> str:
        format_rules = IMAGE_FORMAT_RULES.get(image_format, IMAGE_FORMAT_RULES["abstract_scene"])
        palette = visual_brief.get("suggested_palette", {})
        bg_color = palette.get("background", brand_primary)
        accent_color = palette.get("accent", brand_secondary)

        prompt = f"""Create a professional LinkedIn post image.

VISUAL CONCEPT:
{format_rules['instruction']}

SUBJECT: {visual_brief.get('key_metaphor', '')}
SYMBOLIC ELEMENT: {visual_brief.get('symbolic_element', '')}
EMOTION: {visual_brief.get('core_emotion', '')}

COLOR PALETTE:
- Background: {bg_color} (use this exact color tone)
- Accent: {accent_color} (use for key elements)
- Style: {format_rules['style']}

CRITICAL RULES:
- NO text, words, or letters in the image
- NO realistic human faces or photographic elements
- NO cartoon or comic book style
- NO clipart or stock photo aesthetic
- YES to: flat geometric shapes, bold color contrast, symbolic and conceptual composition
- YES to: professional, premium, modern design aesthetic
- Format: wide landscape, 16:9 ratio

AVOID: {visual_brief.get('avoid', 'nothing specific')}"""

        return prompt

    # ─────────────────────────────────────────────
    # COMMENT GENERATION PROMPTS
    # ─────────────────────────────────────────────

    @classmethod
    def get_comment_prompt(cls, ctx: UserContext, target_post: str, target_author: str) -> str:
        return f"""You are writing a LinkedIn comment on behalf of a {ctx.role} in {ctx.industry}.

The comment must:
1. Add genuine value — share a specific insight, agree with nuance, or ask a thoughtful question
2. Be 2-4 sentences maximum
3. Feel human and conversational, NOT promotional
4. Reference something specific from the post
5. NEVER mention your own services or expertise in a self-promotional way
6. NEVER use: "Great post!", "Thanks for sharing!", "Totally agree!"

TARGET POST BY {target_author}:
{target_post}

Write ONE comment. Return only the comment text, nothing else."""

    # ─────────────────────────────────────────────
    # CONNECTION MESSAGE PROMPTS
    # ─────────────────────────────────────────────

    @classmethod
    def get_connection_request_prompt(cls, ctx: UserContext, target_name: str,
                                       target_headline: str, target_company: str,
                                       reason: str) -> str:
        return f"""Write a LinkedIn connection request message.

From: {ctx.role} in {ctx.industry}
To: {target_name}, {target_headline} at {target_company}
Reason for connecting: {reason}

Rules:
- Maximum 300 characters (LinkedIn limit)
- Be specific — reference something real about them
- No pitch, no ask — just a genuine reason to connect
- Warm, human tone

Return only the message text."""

    # ─────────────────────────────────────────────
    # COVER LETTER PROMPTS
    # ─────────────────────────────────────────────

    @classmethod
    def get_cover_letter_prompt(cls, ctx: UserContext, job_title: str,
                                 company: str, job_description: str) -> str:
        return f"""Write a compelling LinkedIn Easy Apply cover letter.

Applicant: {ctx.role} with skills in {', '.join(ctx.skills[:5])}
Job: {job_title} at {company}
Job Description: {job_description[:500]}

Rules:
- Maximum 300 words
- Lead with the most relevant achievement or skill
- Show you understand the company/role specifically
- End with a clear, confident call to action
- NO generic openers like "I am writing to express my interest"

Return only the cover letter text."""