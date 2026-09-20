from app.schemas.assistant import AssistantContext, AssistantProviderResult
from app.services.assistant.providers.base import AssistantProvider


class ContextAssistantProvider(AssistantProvider):
    """Deterministic assistant that answers only from retrieved project records."""

    def generate_answer(
        self, question: str, context: AssistantContext
    ) -> AssistantProviderResult:
        records = context.records
        source_ids = [source.id for source in context.sources]
        activities = [record for record in records if record.get("type") == "Activity"]
        disruptions = [record for record in records if record.get("type") == "SiteDisruption"]
        materials = [record for record in records if record.get("type") == "MaterialItem"]
        if context.intent in {"DELAY", "RISK", "RECOVERY"}:
            affected = ", ".join(
                str(item.get("name"))
                for item in activities
                if item.get("status") in {"DELAYED", "AT_RISK", "BLOCKED"}
            )
            causes = "; ".join(
                str(item.get("description") or item.get("type_name"))
                for item in disruptions[:3]
            )
            answer = (
                f"Activities requiring attention: {affected or 'No delayed activity was found'}."
                f" {f'Recorded disruptions: {causes}.' if causes else 'No recorded disruption was found.'}"
            )
        elif context.intent == "MATERIAL":
            low_stock = [
                item for item in materials
                if item.get("minimum") is not None
                and item.get("quantity") is not None
                and item["quantity"] <= item["minimum"]
            ]
            answer = (
                "Low-stock materials: "
                + ", ".join(str(item.get("name")) for item in low_stock)
                if low_stock
                else "No material is currently below its configured minimum stock level."
            )
        elif activities:
            answer = (
                f"{len(activities)} project activities were found. "
                f"The latest activity is {activities[0].get('name', 'unnamed')} "
                f"at {activities[0].get('reported_progress', 'unknown')}% reported progress."
            )
        else:
            answer = "The project context does not contain enough records to answer this question."

        return AssistantProviderResult(
            answer=answer,
            source_ids=source_ids,
            confidence="SUPPORTED" if records else "INSUFFICIENT_DATA",
        )


MockAssistantProvider = ContextAssistantProvider
