from opspilot.models.schemas import WorkItem


VALID_SOURCE_TYPES = {"email", "task", "support_request"}


def normalize_items(raw_items: list[dict]) -> list[WorkItem]:
    normalized: list[WorkItem] = []
    for item in raw_items:
        source_type = str(item["source_type"]).strip().lower()
        if source_type not in VALID_SOURCE_TYPES:
            source_type = "task"

        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        normalized.append(
            WorkItem(
                id=str(item["id"]),
                source_type=source_type,
                subject_or_title=str(item["subject_or_title"]).strip(),
                body_or_description=str(item["body_or_description"]).strip(),
                sender_or_requester=str(item["sender_or_requester"]).strip(),
                received_at=str(item["received_at"]).strip(),
                tags=[str(tag).strip().lower() for tag in tags],
            )
        )

    return normalized
