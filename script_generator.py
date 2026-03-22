import anthropic
import json
from config import config
from research import Study

client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)

SYSTEM_PROMPT = f"""أنت محرر محتوى متخصص في تبسيط الأبحاث الطبية للجمهور العربي العام.
مهمتك: تحويل الدراسات العلمية إلى محتوى سوشيال ميديا جذاب وموثوق بالعربية.

القواعد الصارمة:
- لا تؤلف أي معلومة غير موجودة في الدراسة
- استخدم لغة عامية خليجية بسيطة
- لا تبالغ في الفوائد — كن دقيقاً
- دائماً أشر للمصدر
- المحتوى للتوعية لا للعلاج

البراند: {config.BRAND_NAME}
الإخلاء الثابت: "{config.DISCLAIMER_AR}"
"""

SCRIPT_PROMPT = """بناءً على هذه الدراسة:

العنوان: {title}
المجلة: {journal} ({year})
الملخص: {abstract}

اكتب سكريبت فيديو بالعربية الخليجية بالضبط بهذا الهيكل JSON:

{{
  "hook": "جملة افتتاحية صادمة أو مثيرة للاهتمام (أقل من 10 كلمات)",
  "problem": "تعريف المشكلة بجملتين",
  "study_fact": "الحقيقة الرئيسية من الدراسة بدقة تامة",
  "detail": "تفصيل عملي أو آلية التأثير بجملتين",
  "source_mention": "ذكر المجلة والسنة بشكل طبيعي في الكلام",
  "practical_tip": "نصيحة عملية مباشرة جملة واحدة",
  "disclaimer": "{disclaimer}",
  "caption_hashtags": "5 هاشتاقات عربية مناسبة",
  "duration_estimate_sec": "تقدير مدة القراءة بالثواني (بين 30 و55)"
}}

أرجع JSON فقط بدون أي نص إضافي."""

def generate_script(topic_ar: str, study: Study) -> dict:
    prompt = SCRIPT_PROMPT.format(
        title=study.title,
        journal=study.journal,
        year=study.year,
        abstract=study.abstract,
        disclaimer=config.DISCLAIMER_AR,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # نظّف أي backticks محتملة
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)

def build_full_script(script: dict) -> str:
    """يجمع السكريبت كاملاً للـ voiceover"""
    parts = [
        script.get("hook", ""),
        script.get("problem", ""),
        script.get("study_fact", ""),
        script.get("detail", ""),
        script.get("source_mention", ""),
        script.get("practical_tip", ""),
        script.get("disclaimer", ""),
    ]
    return " ".join(p for p in parts if p)

def build_caption(script: dict, study: Study) -> str:
    """يبني الـ caption للنشر"""
    caption = f"""🔬 {script.get('hook', '')}

{script.get('study_fact', '')}

{script.get('practical_tip', '')}

📚 المصدر: {study.journal} ({study.year})
{f'DOI: {study.doi}' if study.doi else ''}

⚠️ {config.DISCLAIMER_AR}

{script.get('caption_hashtags', '')}
#{config.BRAND_NAME}"""
    return caption
