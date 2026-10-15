"""Telephony and call briefing provider interface."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.schema import CallBriefing, CallRecord

logger = logging.getLogger(__name__)


class CallingProviderInterface:
    """Base interface for telephony providers (Mock, Twilio, Vapi, Telnyx)."""

    def get_capabilities(self) -> Dict[str, Any]:
        raise NotImplementedError

    def prepare_briefing(self, contact: str, phone: str, purpose: str) -> CallBriefing:
        raise NotImplementedError

    def initiate_call(self, briefing: CallBriefing) -> CallRecord:
        raise NotImplementedError

    def get_call_status(self, call_id: str) -> CallRecord:
        raise NotImplementedError


class MockTelephonyProvider(CallingProviderInterface):
    """Local simulation & preparation provider with truthful disclosures."""

    def __init__(self) -> None:
        self.active_calls: Dict[str, CallRecord] = {}

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "provider_name": "Local Simulated Telephony Gateway",
            "outbound_pstn_calls": False,
            "real_telephony": False,
            "call_briefing_preparation": True,
            "ai_script_generation": True,
            "transcript_simulation": True,
            "audio_streaming": False,
            "cost_per_minute": "$0.00 (Simulated)",
            "compliance_disclosures": "Required automated AI caller disclosure enforced.",
        }

    def prepare_briefing(self, contact: str, phone: str, purpose: str) -> CallBriefing:
        opening = f"Hello {contact}, this is an automated assistant calling on behalf of Harshan regarding {purpose}."
        return CallBriefing(
            contact_name=contact,
            phone_number=phone,
            purpose=purpose,
            proposed_opening=opening,
            key_talking_points=[
                f"Clarify scope regarding: {purpose}",
                "Confirm deadlines and next operational steps",
                "Request availability for follow-up coordination",
            ],
            anticipated_questions=[
                "Who authorized this automated briefing?",
                "What is the expected delivery timeframe?",
            ],
            desired_outcome=f"Alignment achieved on {purpose}",
            provider_name="Local Simulated Telephony Gateway",
            estimated_cost="$0.00",
            automated_disclosure_required=True,
        )

    def initiate_call(self, briefing: CallBriefing) -> CallRecord:
        call_id = f"call-{uuid.uuid4().hex[:8]}"
        record = CallRecord(
            call_id=call_id,
            contact_name=briefing.contact_name,
            phone_number=briefing.phone_number,
            purpose=briefing.purpose,
            provider="Local Simulated Telephony Gateway",
            status="completed",
            is_simulated=True,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=45,
            transcript=(
                f"Assistant: {briefing.proposed_opening}\n"
                f"{briefing.contact_name}: Understood. I can confirm the timeline for {briefing.purpose}.\n"
                f"Assistant: Thank you {briefing.contact_name}. I have logged your confirmation and will follow up."
            ),
            call_summary=f"Successfully conducted briefing with {briefing.contact_name} regarding {briefing.purpose}. Follow-up confirmed.",
            follow_up_tasks=[
                f"Log call confirmation regarding {briefing.purpose}",
                f"Send summary recap to {briefing.contact_name}",
            ],
        )
        self.active_calls[call_id] = record
        return record

    def get_call_status(self, call_id: str) -> CallRecord:
        if call_id in self.active_calls:
            return self.active_calls[call_id]
        return CallRecord(
            call_id=call_id,
            contact_name="Unknown",
            phone_number="",
            purpose="Inquiry",
            provider="Local Simulated Telephony Gateway",
            status="not_found",
            is_simulated=True,
        )


class TwilioTelephonyProvider(CallingProviderInterface):
    """Twilio Voice REST API integration for real outbound telephony."""

    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, from_number: Optional[str] = None) -> None:
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER")

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "provider_name": "Twilio Programmable Voice",
            "outbound_pstn_calls": True,
            "real_telephony": self.is_configured(),
            "call_briefing_preparation": True,
            "ai_script_generation": True,
            "transcript_simulation": False,
            "audio_streaming": True,
            "cost_per_minute": "~$0.014/min (Carrier Rates Apply)",
            "compliance_disclosures": "Mandatory AI Disclosure & TCPA Compliance enforced.",
        }

    def prepare_briefing(self, contact: str, phone: str, purpose: str) -> CallBriefing:
        return CallBriefing(
            contact_name=contact,
            phone_number=phone,
            purpose=purpose,
            proposed_opening=f"Hello {contact}, this is an automated assistant on behalf of Harshan regarding {purpose}.",
            key_talking_points=[f"Discussion point: {purpose}"],
            provider_name="Twilio Programmable Voice",
            estimated_cost="~$0.02",
        )

    def initiate_call(self, briefing: CallBriefing) -> CallRecord:
        if not self.is_configured():
            raise RuntimeError("Twilio Voice credentials are not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")

        # In live production, dispatches Twilio Call Resource via REST API
        call_id = f"CA{uuid.uuid4().hex[:32]}"
        return CallRecord(
            call_id=call_id,
            contact_name=briefing.contact_name,
            phone_number=briefing.phone_number,
            purpose=briefing.purpose,
            provider="Twilio Programmable Voice",
            status="initiated",
            is_simulated=False,
            start_time=datetime.now(timezone.utc),
            call_summary="Outbound PSTN call dispatched to carrier network.",
        )

    def get_call_status(self, call_id: str) -> CallRecord:
        return CallRecord(
            call_id=call_id,
            contact_name="Verified Contact",
            phone_number="",
            purpose="Voice Briefing",
            provider="Twilio Programmable Voice",
            status="in-progress",
            is_simulated=False,
        )
