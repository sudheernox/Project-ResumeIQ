"""
AI Service — optional AI API integration with NLP fallback
"""
import os
import re
from typing import Dict, Any, Optional


def get_ai_insights(resume_text: str, analysis: dict) -> Optional[Dict[str, Any]]:
    """
    Get AI-powered insights from Gemini or OpenAI.
    Falls back to None if API is unavailable or not configured.
    """
    use_ai = os.getenv('USE_AI_API', 'false').lower() == 'true'
    if not use_ai:
        return None

    gemini_key = os.getenv('GEMINI_API_KEY', '')
    openai_key = os.getenv('OPENAI_API_KEY', '')

    if gemini_key:
        return _get_gemini_insights(resume_text, analysis, gemini_key)
    elif openai_key:
        return _get_openai_insights(resume_text, analysis, openai_key)

    return None


def _get_gemini_insights(resume_text: str, analysis: dict, api_key: str) -> Optional[Dict[str, Any]]:
    """Get insights from Google Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        skills_str = ', '.join(analysis.get('technical_skills', [])[:10])
        score = analysis.get('scores', {}).get('overall', 0)

        prompt = f"""Analyze this resume and provide exactly 3 specific, actionable career insights.
Resume skills: {skills_str}
Overall resume score: {score}/100

Return a JSON object with this exact structure:
{{
  "summary": "2-sentence professional assessment of the candidate",
  "top_insight": "The single most important career advice",
  "strengths_insight": "One specific strength to highlight",
  "gap_insight": "One critical skill to develop immediately"
}}

Be specific and constructive. Do not repeat generic advice."""

        response = model.generate_content(prompt)
        text = response.text

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())

    except Exception as e:
        print(f"Gemini API error: {e}")

    return None


def _get_openai_insights(resume_text: str, analysis: dict, api_key: str) -> Optional[Dict[str, Any]]:
    """Get insights from OpenAI API."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        skills_str = ', '.join(analysis.get('technical_skills', [])[:10])
        score = analysis.get('scores', {}).get('overall', 0)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional career coach and resume expert."},
                {"role": "user", "content": f"""Resume skills: {skills_str}, Score: {score}/100.
Return JSON: {{"summary": "...", "top_insight": "...", "strengths_insight": "...", "gap_insight": "..."}}"""}
            ],
            max_tokens=300,
            temperature=0.7,
        )

        text = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())

    except Exception as e:
        print(f"OpenAI API error: {e}")

    return None


def generate_nlp_insights(analysis: dict) -> Dict[str, Any]:
    """
    Rule-based NLP insights when AI API is not available.
    Provides meaningful insights based on analysis data.
    """
    scores = analysis.get('scores', {})
    tech_skills = analysis.get('technical_skills', [])
    soft_skills = analysis.get('soft_skills', [])
    strengths = analysis.get('strengths', [])
    weaknesses = analysis.get('weaknesses', [])
    overall = scores.get('overall', 0)

    # Generate summary
    if overall >= 75:
        summary = f"Strong resume with {len(tech_skills)} technical skills. You have a competitive profile for entry to mid-level roles."
    elif overall >= 55:
        summary = f"Decent resume foundation with {len(tech_skills)} technical skills. With targeted improvements, you can significantly increase your job match rates."
    else:
        summary = f"Resume needs development in key areas. Focus on building {max(8 - len(tech_skills), 2)} more core technical skills and adding practical projects."

    # Top insight
    if scores.get('experience', 0) < 30:
        top_insight = "Start with internships, freelance projects, or open-source contributions to build real-world experience — this is the #1 differentiator."
    elif scores.get('projects', 0) < 40:
        top_insight = "Build and publish 2-3 end-to-end projects on GitHub. Projects compensate for lack of professional experience."
    elif scores.get('ats', 0) < 60:
        top_insight = "Improve ATS compatibility — your resume may be auto-rejected before human review. Fix section headers and add more keywords."
    else:
        top_insight = "You have a solid foundation. Now focus on customizing your resume for each application to maximize your match score."

    # Strengths insight
    if tech_skills:
        top_tech = tech_skills[:3]
        strengths_insight = f"Your expertise in {', '.join(top_tech)} is a genuine strength. Deepen these skills and build visible projects around them."
    else:
        strengths_insight = "Focus on building a clear technical skill set — pick 3-4 core technologies and master them completely."

    # Gap insight
    if weaknesses:
        gap_insight = weaknesses[0] if weaknesses else "Continue expanding your technical and soft skill repertoire."
    else:
        gap_insight = "You are on the right track! Keep building projects and expanding your skill portfolio."

    return {
        'summary': summary,
        'top_insight': top_insight,
        'strengths_insight': strengths_insight,
        'gap_insight': gap_insight,
        'ai_powered': False,
    }
