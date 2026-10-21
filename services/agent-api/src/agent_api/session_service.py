"""ADK ``BaseSessionService`` backed by Firestore through the tenant-scoped ``SessionRepo``.

One instance serves exactly one tenant: a session id from another tenant simply does not exist here.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse
from google.adk.sessions.state import State

from magaza_core.repo import SessionRepo


def _split_state(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    app, user, session = {}, {}, {}
    for key, value in state.items():
        if key.startswith(State.APP_PREFIX):
            app[key.removeprefix(State.APP_PREFIX)] = value
        elif key.startswith(State.USER_PREFIX):
            user[key.removeprefix(State.USER_PREFIX)] = value
        elif not key.startswith(State.TEMP_PREFIX):
            session[key] = value
    return app, user, session


class FirestoreSessionService(BaseSessionService):
    def __init__(self, repo: SessionRepo) -> None:
        self.repo = repo

    @staticmethod
    def _app_key(app_name: str) -> str:
        return f"app:{app_name}"

    @staticmethod
    def _user_key(app_name: str, user_id: str) -> str:
        return f"user:{app_name}:{user_id}"

    async def _merged_state(
        self, app_name: str, user_id: str, session_state: dict[str, Any]
    ) -> dict[str, Any]:
        state = dict(session_state)
        for key, value in (await self.repo.get_scoped_state(self._app_key(app_name))).items():
            state[State.APP_PREFIX + key] = value
        for key, value in (await self.repo.get_scoped_state(self._user_key(app_name, user_id))).items():
            state[State.USER_PREFIX + key] = value
        return state

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        session_id = (session_id or "").strip() or f"s_{uuid.uuid4().hex[:24]}"
        app_delta, user_delta, session_state = _split_state(state or {})
        now = time.time()
        created = await self.repo.create(
            session_id,
            {
                "app_name": app_name,
                "user_id": user_id,
                "state": session_state,
                "last_update_time": now,
                "created_at": now,
            },
        )
        if not created:
            raise AlreadyExistsError(f"Session with id {session_id} already exists.")
        await self.repo.merge_scoped_state(self._app_key(app_name), app_delta)
        await self.repo.merge_scoped_state(self._user_key(app_name, user_id), user_delta)
        merged = await self._merged_state(app_name, user_id, session_state)
        return Session(
            id=session_id, app_name=app_name, user_id=user_id, state=merged, events=[], last_update_time=now
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        doc = await self.repo.get(session_id.strip())
        if not doc or doc.get("app_name") != app_name or doc.get("user_id") != user_id:
            return None
        events = [Event.model_validate_json(r["event_json"]) for r in await self.repo.list_events(session_id)]
        if config and config.after_timestamp is not None:
            events = [e for e in events if e.timestamp >= config.after_timestamp]
        if config and config.num_recent_events is not None:
            events = events[-config.num_recent_events :] if config.num_recent_events else []
        state = await self._merged_state(app_name, user_id, doc.get("state", {}))
        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            events=events,
            last_update_time=doc.get("last_update_time", 0.0),
        )

    async def list_sessions(self, *, app_name: str, user_id: str | None = None) -> ListSessionsResponse:
        sessions = [
            Session(
                id=d["id"],
                app_name=app_name,
                user_id=d.get("user_id", ""),
                state=d.get("state", {}),
                events=[],
                last_update_time=d.get("last_update_time", 0.0),
            )
            for d in await self.repo.query(app_name, user_id)
        ]
        sessions.sort(key=lambda s: (s.last_update_time, s.user_id, s.id))
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        doc = await self.repo.get(session_id)
        if doc and doc.get("app_name") == app_name and doc.get("user_id") == user_id:
            await self.repo.delete(session_id)

    async def append_event(self, session: Session, event: Event) -> Event:
        if event.partial:
            return event
        event = await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp
        await self.repo.add_event(
            session.id,
            event.id,
            {
                "timestamp": event.timestamp,
                "written_ns": time.time_ns(),
                "event_json": event.model_dump_json(exclude_none=True),
            },
        )
        delta = dict(event.actions.state_delta) if event.actions and event.actions.state_delta else {}
        app_delta, user_delta, session_delta = _split_state(delta)
        update: dict[str, Any] = {"last_update_time": event.timestamp}
        if session_delta:
            update["state"] = session_delta
        await self.repo.update(session.id, update)
        await self.repo.merge_scoped_state(self._app_key(session.app_name), app_delta)
        await self.repo.merge_scoped_state(self._user_key(session.app_name, session.user_id), user_delta)
        return event
