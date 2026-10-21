from __future__ import annotations

import pytest
from agent_test_helpers import tenant_ctx
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.events import Event, EventActions
from google.adk.sessions.base_session_service import GetSessionConfig
from google.genai import types

from agent_api.session_service import FirestoreSessionService
from magaza_core.repo import SessionRepo, get_db

pytestmark = pytest.mark.emulator


async def _service(project: str) -> FirestoreSessionService:
    db = get_db(project)
    ctx = await tenant_ctx(project, "yapi-market")
    return FirestoreSessionService(SessionRepo(db, ctx))


async def test_session_roundtrip_with_events_and_state(seeded_project: str) -> None:
    svc = await _service(seeded_project)
    session = await svc.create_session(
        app_name="app", user_id="u", state={"a": 1, "user:lang": "tr", "temp:x": 9}
    )
    assert session.state == {"a": 1, "user:lang": "tr"}
    with pytest.raises(AlreadyExistsError):
        await svc.create_session(app_name="app", user_id="u", session_id=session.id)

    for i in range(3):
        event = Event(
            invocation_id=f"inv{i}",
            author="user" if i % 2 == 0 else "magaza_asistani",
            content=types.Content(role="user", parts=[types.Part(text=f"mesaj {i}")]),
            actions=EventActions(state_delta={"count": i, "app:version": 2, "temp:scratch": True}),
        )
        await svc.append_event(session, event)

    loaded = await svc.get_session(app_name="app", user_id="u", session_id=session.id)
    assert loaded is not None
    assert [e.content.parts[0].text for e in loaded.events] == ["mesaj 0", "mesaj 1", "mesaj 2"]  # type: ignore[union-attr,index]
    assert (
        loaded.state["count"] == 2 and loaded.state["app:version"] == 2 and loaded.state["user:lang"] == "tr"
    )
    assert "temp:scratch" not in loaded.state

    recent = await svc.get_session(
        app_name="app", user_id="u", session_id=session.id, config=GetSessionConfig(num_recent_events=1)
    )
    assert recent is not None and len(recent.events) == 1
    assert await svc.get_session(app_name="app", user_id="someone-else", session_id=session.id) is None

    listed = await svc.list_sessions(app_name="app", user_id="u")
    assert session.id in {s.id for s in listed.sessions}
    await svc.delete_session(app_name="app", user_id="u", session_id=session.id)
    assert await svc.get_session(app_name="app", user_id="u", session_id=session.id) is None
