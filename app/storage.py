import uuid
from dataclasses import dataclass, field


@dataclass
class Draft:
    id: str
    text: str
    product_name: str
    status: str = "awaiting_photo"       # "awaiting_photo" | "ready"
    photo_file_id: str | None = None
    request_message_id: int | None = None  # id сообщения-запроса фото (для сопоставления по reply)


@dataclass
class State:
    drafts: dict[str, Draft] = field(default_factory=dict)
    awaiting_photo_order: list[str] = field(default_factory=list)  # порядок черновиков, ждущих фото
    awaiting_edit_for: str | None = None  # id черновика, для которого ждём новый текст
    recently_posted: set[str] = field(default_factory=set)
    MAX_RECENT: int = 20

    def new_draft(self, text: str, product_name: str) -> Draft:
        draft = Draft(id=uuid.uuid4().hex[:8], text=text, product_name=product_name)
        self.drafts[draft.id] = draft
        self.awaiting_photo_order.append(draft.id)
        return draft

    def pop_awaiting_photo(self, reply_to_message_id: int | None) -> Draft | None:
        """Находит черновик, ожидающий фото: сперва по reply, иначе — самый старый."""
        if reply_to_message_id:
            for draft_id in self.awaiting_photo_order:
                draft = self.drafts.get(draft_id)
                if draft and draft.request_message_id == reply_to_message_id:
                    self.awaiting_photo_order.remove(draft_id)
                    return draft
        while self.awaiting_photo_order:
            draft_id = self.awaiting_photo_order.pop(0)
            draft = self.drafts.get(draft_id)
            if draft and draft.status == "awaiting_photo":
                return draft
        return None

    def remember(self, product_name: str):
        self.recently_posted.add(product_name)
        if len(self.recently_posted) > self.MAX_RECENT:
            self.recently_posted.pop()


state = State()
