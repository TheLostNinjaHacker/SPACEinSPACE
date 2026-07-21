"""Tests for the A2A protocol — messages and in-process bus."""

import pytest
from shared.a2a_protocol import A2AMessage, A2ATask, A2ABus


class TestA2AMessage:
    def test_create_minimal(self):
        msg = A2AMessage(thread_id="t1", from_agent="a1")
        assert msg.thread_id == "t1"
        assert msg.from_agent == "a1"
        assert msg.message_id is not None
        assert msg.message_type == "answer"

    def test_is_broadcast(self):
        broadcast = A2AMessage(thread_id="t1", from_agent="a1")
        assert broadcast.is_broadcast()
        directed = A2AMessage(thread_id="t1", from_agent="a1", to_agent="a2")
        assert not directed.is_broadcast()

    def test_short_format(self):
        msg = A2AMessage(thread_id="t1", from_agent="planner", to_agent="blender", message_type="task")
        short = msg.short()
        assert "planner" in short
        assert "blender" in short
        assert "task" in short

    def test_expired(self):
        import time
        msg = A2AMessage(thread_id="t1", from_agent="a1", ttl=0)
        time.sleep(0.01)
        assert msg.is_expired()

    def test_not_expired(self):
        msg = A2AMessage(thread_id="t1", from_agent="a1", ttl=3600)
        assert not msg.is_expired()


class TestA2ATask:
    def test_to_message(self):
        task = A2ATask(
            task_type="blender.create",
            payload={"type": "cube"},
            required_tools=["blender.create_object"],
        )
        msg = task.to_message("t1", "planner", "blender")
        assert msg.thread_id == "t1"
        assert msg.from_agent == "planner"
        assert msg.to_agent == "blender"
        assert msg.message_type == "task"
        assert "blender.create" in msg.content
        assert "required_tools" in msg.context
        assert "payload" in msg.context


class TestA2ABus:
    @pytest.mark.asyncio
    async def test_publish_targeted(self):
        bus = A2ABus(db=None)
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("agent-b", handler)
        msg = A2AMessage(thread_id="t1", from_agent="agent-a", to_agent="agent-b")
        await bus.publish(msg)
        assert len(received) == 1
        assert received[0].from_agent == "agent-a"

    @pytest.mark.asyncio
    async def test_publish_broadcast(self):
        bus = A2ABus(db=None)
        received = []

        async def h1(msg):
            received.append(("b1", msg.from_agent))

        async def h2(msg):
            received.append(("b2", msg.from_agent))

        bus.subscribe("b1", h1)
        bus.subscribe("b2", h2)
        msg = A2AMessage(thread_id="t1", from_agent="sender")
        await bus.publish(msg)
        assert len(received) == 2
        assert ("b1", "sender") in received
        assert ("b2", "sender") in received

    @pytest.mark.asyncio
    async def test_self_broadcast_excluded(self):
        bus = A2ABus(db=None)
        received = []

        async def handler(msg):
            received.append(msg.from_agent)

        bus.subscribe("self", handler)
        msg = A2AMessage(thread_id="t1", from_agent="self")
        await bus.publish(msg)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_request_response(self):
        bus = A2ABus(db=None)

        async def echo_handler(msg):
            reply = A2AMessage(
                thread_id=msg.thread_id,
                from_agent="replier",
                to_agent=msg.from_agent,
                content=f"Echo: {msg.content}",
                parent_id=msg.message_id,
            )
            await bus.publish(reply)

        bus.subscribe("replier", echo_handler)

        request = A2AMessage(
            thread_id="t1", from_agent="asker", to_agent="replier",
            content="hello",
        )
        response = await bus.request(request, timeout=2)
        assert response is not None
        assert response.content == "Echo: hello"

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        bus = A2ABus(db=None)
        request = A2AMessage(thread_id="t1", from_agent="asker", to_agent="silent")
        response = await bus.request(request, timeout=0.1)
        assert response is None

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_block(self):
        bus = A2ABus(db=None)
        received = []

        async def broken(msg):
            raise ValueError("oops")

        async def good(msg):
            received.append(msg)

        bus.subscribe("target", broken)
        bus.subscribe("target", good)
        msg = A2AMessage(thread_id="t1", from_agent="a", to_agent="target")
        await bus.publish(msg)
        assert len(received) == 1
