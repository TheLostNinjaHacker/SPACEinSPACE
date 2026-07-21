"""Tests for the agent world — timeline, goals, blender state, memory."""

import asyncio
import pytest
from shared.agent_timeline import (
    AgentTimeline, TimelineEvent, HumanInputPolicy, Tickable,
)
from shared.world_state import (
    AgentWorld, GoalQueue, Goal, BlenderStateMirror, AgentMemory,
)


class TestHumanInputPolicy:
    def test_values(self):
        assert HumanInputPolicy.BLOCKING.value == "blocking"
        assert HumanInputPolicy.ADVISORY.value == "advisory"
        assert HumanInputPolicy.POST_HOC.value == "post_hoc"
        assert HumanInputPolicy.NONE.value == "none"


class TestTimelineEvent:
    def test_create(self):
        e = TimelineEvent(moment=1, agent_id="planner", event_type="plan_started")
        assert e.moment == 1
        assert e.agent_id == "planner"
        assert e.event_type == "plan_started"
        assert e.id is not None
        assert len(e.id) == 12

    def test_short(self):
        e = TimelineEvent(moment=42, agent_id="blender", event_type="tool_call")
        assert "42" in e.short()
        assert "blender" in e.short()

    def test_to_dict(self):
        e = TimelineEvent(moment=1, agent_id="a", event_type="t", data={"key": "val"})
        d = e.to_dict()
        assert d["moment"] == 1
        assert d["agent_id"] == "a"
        assert d["data"]["key"] == "val"


class TestAgentTimeline:
    @pytest.mark.asyncio
    async def test_tick_increments_moment(self):
        timeline = AgentTimeline(tick_interval_ms=1)
        await timeline.tick()
        assert timeline.current_moment == 1
        await timeline.tick()
        assert timeline.current_moment == 2

    def test_log_event(self):
        timeline = AgentTimeline()
        timeline.current_moment = 5
        e = timeline.log("planner", "plan_started", {"goal": "test"})
        assert e.moment == 5
        assert e.event_type == "plan_started"
        assert len(timeline.events) == 1

    def test_get_events_since(self):
        timeline = AgentTimeline()
        timeline.current_moment = 1
        timeline.log("a", "t1")
        timeline.current_moment = 2
        timeline.log("a", "t2")
        timeline.current_moment = 3
        timeline.log("a", "t3")

        events = timeline.get_events_since(2)
        assert len(events) == 2
        assert events[0].event_type == "t2"
        assert events[1].event_type == "t3"

    def test_mark_human_checkpoint(self):
        timeline = AgentTimeline()
        timeline.current_moment = 100
        cp = timeline.mark_human_checkpoint()
        assert cp == 100
        assert timeline.last_checkpoint() == 100

    def test_get_human_view_empty(self):
        timeline = AgentTimeline()
        view = timeline.get_human_view()
        assert "Inga händelser" in view

    def test_get_human_view_with_events(self):
        timeline = AgentTimeline()
        timeline.current_moment = 10
        timeline.log("blender", "tool_call", {"tool": "create_object"})
        timeline.log("blender", "tool_call", {"tool": "set_material"})
        timeline.log("blender", "error", {"error": "invalid mode"})
        timeline.log("blender", "auto_retry", {})

        view = timeline.get_human_view(0)
        assert "tool" in view
        assert "error" in view or "fel" in view
        assert "blender" in view

    def test_pause_resume(self):
        timeline = AgentTimeline()
        assert not timeline._paused
        timeline.pause()
        assert timeline._paused
        timeline.resume()
        assert not timeline._paused

    def test_human_requested_freeze(self):
        timeline = AgentTimeline()
        timeline.human_requested_freeze = True
        # Simulate a tick that should process the freeze
        asyncio.run(timeline.tick())
        assert timeline._paused
        assert not timeline.human_requested_freeze

    def test_register_agent(self):
        timeline = AgentTimeline()
        agent = DummyTickable("test", interval=1)
        timeline.register_agent(agent)
        assert "test" in timeline.active_agents


class DummyTickable(Tickable):
    def __init__(self, name: str, interval: int = 1):
        self.agent_id = name
        self.tick_interval = interval
        self.tick_count = 0

    async def tick(self, timeline: AgentTimeline):
        self.tick_count += 1


class TestGoalQueue:
    def test_add_and_next(self):
        q = GoalQueue()
        g1 = Goal("first", priority=1)
        g2 = Goal("second", priority=3)
        q.add(g2)
        q.add(g1)

        next_goal = q.next()
        assert next_goal is not None
        assert next_goal.description == "first"  # higher priority

    def test_next_returns_active(self):
        q = GoalQueue()
        g = Goal("test")
        q.add(g)
        q.next()
        assert g.status == "active"
        # Calling next again should return the same active goal
        assert q.next().id == g.id

    def test_complete(self):
        q = GoalQueue()
        g = Goal("test")
        q.add(g)
        q.next()
        q.complete(g.id)
        assert g.status == "completed"
        assert q.next() is None  # no more pending

    def test_fail(self):
        q = GoalQueue()
        g = Goal("test")
        q.add(g)
        q.fail(g.id, "reason")
        assert g.status == "failed"

    def test_rollback(self):
        q = GoalQueue()
        g = Goal("test")
        q.add(g)
        q.rollback(g.id)
        assert g.status == "rolled_back"

    def test_list_active(self):
        q = GoalQueue()
        ga = Goal("a", priority=1)
        gb = Goal("b", priority=2)
        q.add(ga)
        q.add(gb)
        active_goal = q.next()  # ga becomes active
        q.complete(active_goal.id)
        active = q.list_active()
        assert len(active) == 1
        assert active[0].description == "b"


class TestBlenderStateMirror:
    def test_empty(self):
        b = BlenderStateMirror()
        assert b.summary() == "Tom scen"

    def test_add_object(self):
        b = BlenderStateMirror()
        b.add_object("Cube", "cube", [0, 0, 0])
        assert "Cube" in b.objects
        assert b.objects["Cube"]["type"] == "cube"

    def test_remove_object(self):
        b = BlenderStateMirror()
        b.add_object("Cube", "cube")
        b.remove_object("Cube")
        assert len(b.objects) == 0

    def test_modify_object(self):
        b = BlenderStateMirror()
        b.add_object("Cube", "cube")
        b.modify_object("Cube", location=[1, 2, 3])
        assert b.objects["Cube"]["location"] == [1, 2, 3]

    def test_dirty_flag(self):
        b = BlenderStateMirror()
        assert not b.is_dirty()
        b.add_object("Cube")
        assert b.is_dirty()
        b.clean()
        assert not b.is_dirty()

    def test_snapshot(self):
        b = BlenderStateMirror()
        b.add_object("Cube", "cube", [0, 0, 0])
        b.add_object("Sphere", "sphere", [1, 1, 1])
        s = b.snapshot()
        assert s["count"] == 2
        assert "Cube" in s["objects"]
        assert "Sphere" in s["objects"]

    def test_set_mode(self):
        b = BlenderStateMirror()
        b.set_mode("EDIT")
        assert b.mode == "EDIT"

    def test_summary_multi(self):
        b = BlenderStateMirror()
        b.add_object("Cube", "cube")
        b.add_object("Sphere", "sphere")
        b.add_object("Sphere2", "sphere")
        assert "2 sphere" in b.summary()
        assert "1 cube" in b.summary()


class TestAgentMemory:
    @pytest.mark.asyncio
    async def test_store_and_query(self):
        m = AgentMemory()
        mid = await m.store("Skapade en röd kub", "episodic", "blender")
        assert mid is not None

        results = await m.query("kub")
        assert len(results) == 1
        assert results[0]["content"] == "Skapade en röd kub"

    @pytest.mark.asyncio
    async def test_query_no_match(self):
        m = AgentMemory()
        await m.store("Skapade en kub", "episodic", "blender")
        results = await m.query("något annat")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_summary_empty(self):
        m = AgentMemory()
        assert "Tomt" in m.summary()

    @pytest.mark.asyncio
    async def test_summary_with_memories(self):
        m = AgentMemory()
        await m.store("a", "episodic")
        await m.store("b", "semantic")
        s = m.summary()
        assert "episodic" in s
        assert "semantic" in s


class TestAgentWorld:
    def test_add_goal(self):
        w = AgentWorld()
        goal = w.add_goal("Skapa en kub")
        assert goal.description == "Skapa en kub"
        assert len(w.goals.list_active()) == 1

    def test_add_sub_goal(self):
        w = AgentWorld()
        parent = w.add_goal("Build scene")
        sub = w.add_sub_goal(parent.id, "Add cube")
        assert sub is not None
        assert sub.parent_goal_id == parent.id
        assert len(w.goals.list_active()) == 2

    def test_complete_goal(self):
        w = AgentWorld()
        goal = w.add_goal("test")
        w.complete_goal(goal.id)
        assert goal.status == "completed"

    def test_fail_goal(self):
        w = AgentWorld()
        goal = w.add_goal("test")
        w.fail_goal(goal.id, "reason")
        assert goal.status == "failed"

    def test_human_view(self):
        w = AgentWorld()
        w.add_goal("Skapa en kub")
        view = w.human_view()
        assert view is not None
        assert len(view) > 0

    def test_pause_resume(self):
        w = AgentWorld()
        w.pause()
        assert w.timeline._paused
        w.resume()
        assert not w.timeline._paused
