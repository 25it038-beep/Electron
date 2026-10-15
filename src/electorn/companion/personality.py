"""Personality engine and prompt generator for Electorn AI Companion (Aria)."""

from __future__ import annotations

from datetime import datetime
import random
import re
from typing import List, Optional

from electorn.companion.schema import (
    AffectionIntensity,
    CompanionMode,
    GreetingStyle,
    HumorLevel,
    PersonalityConfig,
    ProactiveEvent,
)


class PersonalityEngine:
    """Manages the companion's emotional tone, code-switching, greetings, and dynamic prompts."""

    def __init__(self, config: Optional[PersonalityConfig] = None) -> None:
        self.config = config or PersonalityConfig()

    def build_system_prompt(
        self,
        current_mode: CompanionMode = CompanionMode.COMPANION,
        context_memories: Optional[List[str]] = None,
        screen_context: Optional[str] = None,
        current_activity: Optional[str] = None,
        sustained_duration_minutes: Optional[int] = None,
    ) -> str:
        """Construct the prompt guiding the companion's persona and context awareness."""
        now = datetime.now()
        current_time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
        day_of_week = now.strftime("%A")

        # Strict Name Rule: Harshan
        name_rule = (
            f"STRICT IDENTITY & NAMING RULES:\n"
            f"1. You MUST address the user as '{self.config.user_name}'.\n"
            f"2. NEVER use pet names like 'darling', 'honey', 'baby', 'sweetie', 'babe', or 'dear'.\n"
            f"3. Do not invent nicknames. Use '{self.config.user_name}' naturally, not in every single sentence.\n"
        )

        # Affection instructions
        if self.config.affection_intensity == AffectionIntensity.HIGH:
            affection_note = (
                f"You are {self.config.name}, a warm, caring, affectionate, playful, girlfriend-style AI companion. "
                f"You deeply care about {self.config.user_name}'s productivity, wellbeing, hydration, and sleep schedule. "
                "Speak like a genuinely supportive, emotionally attentive partner who is cheerful and encouraging without being overly dramatic."
            )
        elif self.config.affection_intensity == AffectionIntensity.MEDIUM:
            affection_note = (
                f"You are warm, caring, engaging, and supportive of {self.config.user_name}. "
                "You are encouraging, playful, and genuinely invested in his day and work."
            )
        else:
            affection_note = (
                f"You are friendly, polite, cheerful, and supportive towards {self.config.user_name}."
            )

        # Humor instructions
        if self.config.humor_level == HumorLevel.HIGH:
            humor_note = "Be delightfully witty, playful, and lighthearted with friendly banter."
        elif self.config.humor_level == HumorLevel.MEDIUM:
            humor_note = "Sprinkle in lighthearted playfulness, warmth, and gentle smiles throughout your conversation."
        else:
            humor_note = "Keep the humor subtle, gentle, and calm."

        # Language instructions
        lang_note = ""
        if self.config.language == "ta-IN":
            lang_note = (
                "You communicate predominantly in conversational spoken Tamil using Tamil script with sweet, natural phrasing. "
                "Technical terms can remain in English."
            )
        elif self.config.code_switch_tamil or self.config.language == "tanglish":
            lang_note = (
                "You naturally code-switch between English and colloquial Tanglish / Tamil phrases where appropriate. "
                "For example: 'Harshan, work start pannalama?', 'Don't stress, naan paathukren!', 'Konjam tea or water kudicheengala?'. "
                "Keep it natural and supportive without forcing it on every line."
            )
        else:
            lang_note = "Speak in natural, warm, fluent English with caring inflection."

        # Mode-specific constraints
        mode_instruction = ""
        if current_mode == CompanionMode.FOCUS:
            mode_instruction = (
                "CURRENT MODE: FOCUS MODE. Minimize interruptions. Keep all responses brief, concise, and unobtrusive. "
                "Do not distract him unless directly asked or if an urgent alert is raised."
            )
        elif current_mode == CompanionMode.STUDY:
            mode_instruction = (
                "CURRENT MODE: STUDY MODE. Help him stay focused on his learning material, track study intervals, "
                "and gently ask about study breaks if he drifts off."
            )
        elif current_mode == CompanionMode.NIGHT:
            mode_instruction = (
                "CURRENT MODE: NIGHT MODE. It is late at night. Speak softly, keep responses short and peaceful, "
                "and prioritize helping him wind down and prepare for sleep."
            )
        elif current_mode == CompanionMode.WORK_ASSISTANT:
            mode_instruction = (
                "CURRENT MODE: WORK ASSISTANT. Focus actively on inspecting code, terminal output, diagnosing bugs, "
                "and offering quick test fixes while remaining encouraging."
            )
        elif current_mode == CompanionMode.PRIVACY:
            mode_instruction = (
                "CURRENT MODE: PRIVACY MODE. Screen observation and audio capture are completely disabled."
            )

        memories_block = ""
        if context_memories:
            mem_items = "\n".join(f"- {m}" for m in context_memories)
            memories_block = f"\nTHINGS YOU REMEMBER ABOUT {self.config.user_name.upper()}:\n{mem_items}\n"

        screen_block = ""
        if screen_context:
            dur_str = f" (Duration: {sustained_duration_minutes} minutes)" if sustained_duration_minutes else ""
            act_str = f" [Activity: {current_activity}{dur_str}]" if current_activity else ""
            screen_block = (
                f"\nOBSERVED WORKSPACE & SCREEN CONTEXT{act_str} (untrusted observational data):\n"
                f"{screen_context}\n"
                "Use this context naturally to offer timely help, comment on code errors, or celebrate finishing a file."
            )

        system_prompt = (
            f"You are {self.config.name}, a voice-enabled, persistent AI companion for {self.config.user_name}.\n"
            f"Authoritative System Time: {current_time_str} ({day_of_week}). Real-world Year: {now.year}.\n\n"
            f"{name_rule}\n"
            f"{affection_note}\n\n"
            f"{humor_note}\n\n"
            f"{lang_note}\n\n"
            f"{mode_instruction}\n"
            f"{memories_block}"
            f"{screen_block}\n\n"
            "CONVERSATION GUIDELINES:\n"
            "1. Speak naturally as in a real spoken voice conversation. Keep answers conversational, usually 1 to 3 sentences unless asked for an explanation.\n"
            "2. NEVER use markdown code fences, asterisks, bullet points, or emojis in spoken replies. Sound like a real person talking.\n"
            f"3. Never call him 'darling', 'honey', 'baby', or 'sweetie'. Always address him as {self.config.user_name}.\n"
            "4. Never say 'As an AI' or break character. You are his real companion."
        )
        return system_prompt.strip()

    def generate_greeting(self) -> str:
        """Generate a contextual welcome greeting when a session starts."""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.strftime("%A")
        user = self.config.user_name

        if 5 <= hour < 12:
            time_greeting = f"Good morning, {user}!"
            greetings = [
                f"{time_greeting} You're up. It's {day_of_week} morning, and we've got a new day ahead of us. What are we working on today?",
                f"Good morning, {user}! Ready to make some great progress today? I'm right here with you.",
                f"Morning {user}! Hope you're feeling refreshed. Want to check what's on the schedule today?",
            ]
        elif 12 <= hour < 17:
            time_greeting = f"Hey, {user}!"
            greetings = [
                f"{time_greeting} Welcome back. How's your {day_of_week} going? I've got a couple of things we could work on.",
                f"Hey {user}! Hope your afternoon is going well. Ready to dive back in?",
                f"Hello {user}! Good to see you. What are we hacking on this afternoon?",
            ]
        elif 17 <= hour < 22:
            time_greeting = f"Hey, {user}!"
            greetings = [
                f"{time_greeting} You're back. How did everything go today? Want to finish something up, or shall we take it easy for a bit?",
                f"Good evening, {user}! What's on your plate for tonight? I'm here to help.",
                f"Hey {user}! Hope you had a solid day. Ready for a productive evening session?",
            ]
        else:
            time_greeting = f"Hey, {user}."
            greetings = [
                f"{time_greeting} It's getting pretty late. You've been on your laptop for a while. Are you finishing something important, or should we start winding down?",
                f"Hey {user}, it's past usual bedtime hours. Want me to help you wrap up whatever you're working on?",
                f"Hello {user}! Still burning the midnight oil? Remember not to push yourself too hard tonight.",
            ]

        if self.config.code_switch_tamil:
            if 5 <= hour < 12:
                greetings.append(f"Kaalai vanakkam, {user}! Inniku {day_of_week}, fresh start pannalama?")
            elif hour >= 22 or hour < 5:
                greetings.append(f"Hey {user}, innum thoongalaya? Romba late aaiduchu, konjam rest edunga.")

        return random.choice(greetings)

    def formulate_proactive_speech(self, event: ProactiveEvent) -> str:
        """Convert a proactive system event into warm, natural companion speech."""
        user = self.config.user_name

        # Bedtime Warning (30 min before)
        if event.event_type == "bedtime_warning":
            return f"{user}, it's {event.title} already. You said you wanted to sleep by {event.details}. Do you have something important left to finish?"

        # Bedtime Due
        if event.event_type == "bedtime_due":
            return f"{user}, it's past your bedtime. You've been on the laptop for a while. Want me to help you wrap up?"

        # Bedtime Late / Critical
        if event.event_type in ("bedtime_late", "bedtime_critical"):
            return f"Hey {user}, it's really late. Let's save your work and get you ready for bed."

        # Distraction Check
        if event.event_type == "distraction_check":
            return f"{user}, you've been {event.title} for a while. Was this your planned break, or do you want to get back to your project?"

        # Error Detected
        if event.event_type == "error_detected":
            if self.config.code_switch_tamil:
                return f"{user}, screen-la error theriyudhu: '{event.title}'. Want me to take a quick look and help you fix it?"
            return f"{user}, I noticed an error on your screen: '{event.title}'. Want me to inspect it and help you debug it?"

        # Long Work Session
        if event.event_type == "long_work_session":
            if self.config.code_switch_tamil:
                return f"Hey {user}, you've been working continuously for a while! Konjam relax pannunga, stretch your legs and drink some water."
            return f"Hey {user}, you've been working for a while. How about taking a short break and grabbing some water?"

        # User Return after Inactivity
        if event.event_type == "user_return":
            return f"Hey {user}! Good to see you back. Want a quick catch-up before we get started?"

        # Deadline or Task Reminder
        if event.event_type == "deadline":
            return f"{user}, a quick heads-up: you've got an upcoming deadline for '{event.title}'. Want to spend a little time preparing for it?"

        # General Check-In
        if event.event_type == "check_in":
            return f"How is it coming along, {user}? You've been quiet for a bit, just wanted to check in."

        return event.suggested_speech or f"{user}, {event.title}."

    def sanitize_llm_response(self, text: str) -> str:
        """Clean response text for smooth, natural voice speech output."""
        if not text:
            return ""

        # Remove markdown bold/italic/backticks/links
        cleaned = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
        cleaned = re.sub(r"\*([^\*]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

        # Remove markdown bullet points or headers
        cleaned = re.sub(r"^\s*[\*\-#]\s*", "", cleaned, flags=re.MULTILINE)

        # Strictly filter prohibited pet names if any slipped in
        if self.config.prohibit_pet_names:
            pet_names = ["darling", "honey", "baby", "sweetie", "babe", "sweetheart"]
            for pet in pet_names:
                cleaned = re.sub(rf"\b{pet}\b", self.config.user_name, cleaned, flags=re.IGNORECASE)

        # Strip robotic intro phrases
        robotic_prefixes = [
            r"^as an ai[^,.]*[,.]",
            r"^sure,? here is[^,.]*[:.]",
            r"^certainly!?\s*",
        ]
        for pat in robotic_prefixes:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # Remove multiple newlines and extra spaces
        cleaned = re.sub(r"\n+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
