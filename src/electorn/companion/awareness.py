"""
Aria World & Cultural Awareness Engine.
Dynamically tracks real-world time, calendar dates, Indian & global festivals,
proactive greetings, and festival safety intelligence.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set


class FestivalEvent:
    def __init__(
        self,
        event_id: str,
        name: str,
        greeting_text: str,
        tamil_greeting: Optional[str] = None,
        safety_advice: Optional[List[str]] = None,
        date_check_fn=None,
    ) -> None:
        self.event_id = event_id
        self.name = name
        self.greeting_text = greeting_text
        self.tamil_greeting = tamil_greeting
        self.safety_advice = safety_advice or []
        self.date_check_fn = date_check_fn

    def is_active(self, dt: datetime) -> bool:
        if self.date_check_fn:
            return self.date_check_fn(dt)
        return False


class AwarenessEngine:
    def __init__(self, user_name: str = "Harshan") -> None:
        self.user_name = user_name
        self._greeting_history: Set[str] = set()
        self.festivals: List[FestivalEvent] = []
        self._init_festivals()

    def _init_festivals(self) -> None:
        self.festivals = [
            FestivalEvent(
                event_id="new_year",
                name="New Year",
                greeting_text=f"Happy New Year, {self.user_name}! Wishing you a year filled with breakthrough opportunities, joy, and achievements.",
                tamil_greeting=f"இனிய புத்தாண்டு நல்வாழ்த்துகள் {self.user_name}!",
                date_check_fn=lambda d: d.month == 1 and d.day == 1,
            ),
            FestivalEvent(
                event_id="pongal",
                name="Pongal",
                greeting_text=f"Iniya Pongal Nalvazhthukkal, {self.user_name}! Wishing you and your family abundant happiness, prosperity, and sweet moments.",
                tamil_greeting=f"இனிய பொங்கல் நல்வாழ்த்துகள் {self.user_name}! தை பிறந்தால் வழி பிறக்கும்.",
                date_check_fn=lambda d: d.month == 1 and 14 <= d.day <= 17,
            ),
            FestivalEvent(
                event_id="republic_day",
                name="Republic Day",
                greeting_text=f"Happy Republic Day, {self.user_name}! Celebrating the spirit, unity, and democracy of our nation.",
                date_check_fn=lambda d: d.month == 1 and d.day == 26,
            ),
            FestivalEvent(
                event_id="tamil_new_year",
                name="Tamil New Year",
                greeting_text=f"Iniya Tamizh Puthandu Nalvazhthukkal, {self.user_name}! May this new year bring endless peace and success.",
                tamil_greeting=f"இனிய தமிழ் புத்தாண்டு நல்வாழ்த்துகள் {self.user_name}!",
                date_check_fn=lambda d: d.month == 4 and (d.day in (14, 15)),
            ),
            FestivalEvent(
                event_id="independence_day",
                name="Independence Day",
                greeting_text=f"Happy Independence Day, {self.user_name}! Celebrating freedom, progress, and unity.",
                date_check_fn=lambda d: d.month == 8 and d.day == 15,
            ),
            FestivalEvent(
                event_id="diwali",
                name="Diwali",
                greeting_text=f"Happy Diwali, {self.user_name}! Wishing you and your family divine happiness, warmth, and prosperity. Have a wonderful celebration!",
                tamil_greeting=f"இனிய தீபாவளி நல்வாழ்த்துகள் {self.user_name}!",
                safety_advice=[
                    "Maintain a safe distance from fireworks while lighting them.",
                    "Always keep a bucket of water, sand, or a fire extinguisher nearby.",
                    "Never light fireworks while holding them in your hands or inside containers.",
                    "Never attempt to relight failed fireworks or duds.",
                    "Keep pets and animals indoors in quiet, comfortable rooms.",
                    "Avoid bursting crackers near hospitals, elderly homes, and quiet zones.",
                    "In case of any emergency in India, dial 112 immediately.",
                ],
                date_check_fn=lambda d: d.month in (10, 11),  # Dynamic autumn window
            ),
            FestivalEvent(
                event_id="christmas",
                name="Christmas",
                greeting_text=f"Merry Christmas, {self.user_name}! Wishing you peace, cheer, and wonderful celebrations with family.",
                date_check_fn=lambda d: d.month == 12 and d.day == 25,
            ),
        ]

    def get_today_context(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        dt = now or datetime.now()
        day_of_week = dt.strftime("%A")
        date_str = dt.strftime("%B %d, %Y")
        time_str = dt.strftime("%I:%M %p")

        active = [f for f in self.festivals if f.is_active(dt)]
        special_event = active[0] if active else None

        return {
            "date_string": date_str,
            "day_of_week": day_of_week,
            "time_string": time_str,
            "special_event": special_event,
        }

    def get_proactive_greeting(self, now: Optional[datetime] = None) -> Optional[str]:
        dt = now or datetime.now()
        ctx = self.get_today_context(dt)
        special: Optional[FestivalEvent] = ctx["special_event"]
        if not special:
            return None

        key = f"{special.event_id}_{dt.year}_{dt.month}_{dt.day}"
        if key in self._greeting_history:
            return None

        self._greeting_history.add(key)
        msg = special.greeting_text
        if special.safety_advice:
            msg += f" Remember to celebrate safely: {special.safety_advice[0]}"
        return msg

    def get_safety_advice(self, topic: str = "diwali") -> List[str]:
        target = topic.lower()
        for f in self.festivals:
            if f.event_id in target or target in f.event_id:
                if f.safety_advice:
                    return f.safety_advice
        return [
            "Maintain safe distances and keep safety equipment accessible.",
            "For any emergency in India, dial 112 immediately.",
        ]
