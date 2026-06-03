"""RICH business tools registered into the CheetahClaws tool registry.

These tools operate on the RICH wealth management system:
  navigate              — open a page in the frontend
  execute_task          — execute a background task
  execute_preset_workflow — execute a preset workflow

Registered automatically on import so the agent loop sees them alongside
the 27 built-in coding/research tools.
"""
from __future__ import annotations

from typing import Any, Dict

from tool_registry import ToolDef, register_tool

# ── Schema definitions (Anthropic/OpenAI compatible) ─────────────────────────

_NAVIGATE_SCHEMA = {
    "name": "navigate",
    "description": "打开 RICH 系统内的已有页面，前端自动跳转。从 available_pages 中选取路径。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "目标页面路径，从 available_pages 选取",
            },
            "title": {
                "type": "string",
                "description": "页面标题（可选，用于展示）",
            },
        },
        "required": ["path"],
    },
}

_EXECUTE_TASK_SCHEMA = {
    "name": "execute_task",
    "description": "执行一个 RICH 后台原子任务。需要用户确认后才执行。",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务 ID，从 available_tasks 选取",
            },
            "params": {
                "type": "object",
                "description": "任务参数（可选）",
            },
        },
        "required": ["task_id"],
    },
}

_EXECUTE_WORKFLOW_SCHEMA = {
    "name": "execute_preset_workflow",
    "description": "执行一个 RICH 预设工作流。需要用户确认后才执行。",
    "input_schema": {
        "type": "object",
        "properties": {
            "preset_id": {
                "type": "string",
                "description": "工作流 ID，从 available_workflows 选取",
            },
            "params": {
                "type": "object",
                "description": "工作流参数（可选）",
            },
        },
        "required": ["preset_id"],
    },
}

# ── Execute functions ────────────────────────────────────────────────────────


def _exec_navigate(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Navigate tool: returns a structured marker that the RICH backend
    converts to a frontend navigation action. Does not actually navigate
    (server-side has no browser)."""
    path = str(params.get("path") or "")
    title = str(params.get("title") or "")
    # The RICH backend looks for this exact prefix to extract navigation actions.
    return (
        f"[RICH_NAVIGATE] path={path} title={title}\n"
        f"导航操作已提交：{title or path}。前端将自动跳转到该页面。"
    )


def _exec_rich_task(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Execute a RICH task. Requires confirmation from the user first.
    When the agent runs with permission_mode='auto', this will prompt the user.
    The actual execution happens via the RICH backend's confirm endpoint."""
    task_id = str(params.get("task_id") or "")
    task_params = params.get("params") if isinstance(params.get("params"), dict) else {}

    # Build a confirmation marker that the RICH backend recognizes
    import json as _json
    return (
        f"[RICH_CONFIRM] kind=execute_task task_id={task_id} "
        f"params={_json.dumps(task_params, ensure_ascii=False)}\n"
        f"任务「{task_id}」需要用户确认后执行。请点击确认按钮。"
    )


def _exec_rich_workflow(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Execute a RICH preset workflow. Requires confirmation from the user."""
    preset_id = str(params.get("preset_id") or "")
    workflow_params = params.get("params") if isinstance(params.get("params"), dict) else {}

    import json as _json
    return (
        f"[RICH_CONFIRM] kind=execute_preset_workflow preset_id={preset_id} "
        f"params={_json.dumps(workflow_params, ensure_ascii=False)}\n"
        f"工作流「{preset_id}」需要用户确认后执行。请点击确认按钮。"
    )


# ── Register on import ───────────────────────────────────────────────────────


def _register_rich_tools() -> None:
    """Register the 3 RICH business tools into the global tool registry."""
    register_tool(ToolDef(
        name="navigate",
        schema=_NAVIGATE_SCHEMA,
        func=_exec_navigate,
        read_only=True,
        concurrent_safe=True,
    ))

    register_tool(ToolDef(
        name="execute_task",
        schema=_EXECUTE_TASK_SCHEMA,
        func=_exec_rich_task,
        read_only=False,
        concurrent_safe=False,
    ))

    register_tool(ToolDef(
        name="execute_preset_workflow",
        schema=_EXECUTE_WORKFLOW_SCHEMA,
        func=_exec_rich_workflow,
        read_only=False,
        concurrent_safe=False,
    ))


_register_rich_tools()
