"""RICH business tools registered into the CheetahClaws tool registry."""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlencode

from tool_registry import ToolDef, register_tool

_RICH_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_RICH_BACKEND = os.path.join(_RICH_ROOT, "web_interface", "backend")
_RICH_APP = os.path.join(_RICH_BACKEND, "app")
_RICH_BUSINESS_TOOLS = [
    "Skill",
    "SkillList",
    "navigate",
    "open_symbol_chart",
    "get_portfolios",
    "get_portfolio_detail",
    "create_portfolio",
    "update_portfolio",
    "delete_portfolio",
    "get_dashboard_summary",
    "get_portfolio_summary",
    "get_asset_types",
    "get_asset_type_preset",
    "create_asset_type",
    "update_asset_type",
    "delete_asset_type",
    "delete_asset_types",
    "cleanup_orphan_assets",
    "get_asset_positions",
    "get_asset_allocation",
    "get_portfolio_assets",
    "get_assets_summary",
    "add_portfolio_asset",
    "update_portfolio_asset",
    "update_portfolio_asset_price",
    "delete_portfolio_asset",
    "get_recent_transactions",
    "get_transactions",
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    "delete_transactions",
    "update_transaction_status",
    "get_transaction_statistics",
    "preview_business_import",
    "execute_business_import",
    "get_asset_groups",
    "get_asset_group_detail",
    "create_asset_group",
    "update_asset_group",
    "delete_asset_group",
    "add_asset_group_member",
    "update_asset_group_member",
    "remove_asset_group_member",
    "validate_asset_group_weights",
    "get_group_value",
    "analyze_portfolio_risk",
    "analyze_portfolio_performance",
    "calculate_rebalance_plan",
    "execute_rebalance",
    "force_recalculate_portfolio",
    "update_portfolio_weights",
    "get_dca_plans",
    "get_dca_plan_detail",
    "delete_dca_plan",
    "preview_dca_allocation",
    "get_pending_dca_plans",
    "get_dca_execution_history",
    "get_dca_statistics",
    "get_dca_groups",
    "get_dca_group_detail",
    "create_dca_group",
    "update_dca_group",
    "delete_dca_group",
    "set_dca_group_members",
    "add_dca_group_member",
    "update_dca_group_member",
    "remove_dca_group_member",
    "validate_dca_group_weights",
    "create_dca_plan",
    "update_dca_plan",
    "toggle_dca_plan",
    "execute_dca_plan",
    "run_due_dca_plans",
    "search_market_symbols",
    "list_market_symbols",
    "get_kline_history",
    "analyze_kline",
    "query_valuation_data",
    "query_factors",
]
# ── Schema definitions (Anthropic/OpenAI compatible) ─────────────────────────

_NAVIGATE_SCHEMA = {
    "name": "navigate",
    "description": (
        "打开 RICH 系统内的已有页面，前端自动跳转。可用页面列表：\n"
        "- / (仪表盘/首页)\n"
        "- /holdings (持仓明细)\n"
        "- /transactions (交易记录)\n"
        "- /cash-accounts (现金账户)\n"
        "- /portfolio (组合配置)\n"
        "- /dca (定投计划)\n"
        "- /calculator (投资计算器)\n"
        "- /analysis (投资分析)\n"
        "- /chart (行情图表/K线图)\n"
        "- /quant/strategies (量化策略管理)\n"
        "- /quant/backtest (回测中心)\n"
        "- /quant/data (数据管理)\n"
        "- /settings (系统设置)\n"
        "- /notifications (通知中心)"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目标页面路径，必须从上方的可用页面列表中选取"},
            "title": {"type": "string", "description": "页面标题（可选，用于展示）"},
        },
        "required": ["path"],
    },
}

_OPEN_SYMBOL_CHART_SCHEMA = {
    "name": "open_symbol_chart",
    "description": "打开指定标的的 K 线图页面。只导航不写入数据。",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "标的代码，例如 000001、sh.000300"},
            "interval": {"type": "string", "description": "周期：1/5/15/30/60/D/W/M，默认 D"},
            "adjust": {"type": "string", "description": "复权类型：空字符串/qfq/hfq，默认空字符串"},
            "from": {"type": "string", "description": "开始日期 YYYYMMDD，可选"},
            "to": {"type": "string", "description": "结束日期 YYYYMMDD，可选"},
        },
        "required": ["symbol"],
    },
}

_PORTFOLIOS_SCHEMA = {
    "name": "get_portfolios",
    "description": "读取当前 RICH 用户的投资组合列表。",
    "input_schema": {"type": "object", "properties": {}},
}

_CREATE_PORTFOLIO_SCHEMA = {
    "name": "create_portfolio",
    "description": "创建投资组合。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "组合名称"},
            "total_assets": {"type": "number", "description": "初始资产，可选，默认 0"},
        },
        "required": ["name"],
    },
}

_UPDATE_PORTFOLIO_SCHEMA = {
    "name": "update_portfolio",
    "description": "更新投资组合名称或初始资产。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID"},
            "name": {"type": "string", "description": "组合名称，可选"},
            "total_assets": {"type": "number", "description": "资产金额，可选"},
        },
        "required": ["portfolio_id"],
    },
}

_DELETE_PORTFOLIO_SCHEMA = {
    "name": "delete_portfolio",
    "description": "删除投资组合及其关联持仓/交易等数据。危险操作，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID"}},
        "required": ["portfolio_id"],
    },
}

_PORTFOLIO_DETAIL_SCHEMA = {
    "name": "get_portfolio_detail",
    "description": "读取当前 RICH 用户某个投资组合的完整配置、持仓和目标权重。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}},
    },
}

_DASHBOARD_SUMMARY_SCHEMA = {
    "name": "get_dashboard_summary",
    "description": "读取仪表盘汇总，包括总资产、收益、平衡度、资产数量和建议月投资额。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "force_recalculate": {"type": "boolean", "description": "是否先强制重算，默认 false"},
            "adjust_type": {"type": "string", "description": "复权类型：空字符串/qfq/hfq"},
        },
    },
}

_PORTFOLIO_SUMMARY_SCHEMA = {
    "name": "get_portfolio_summary",
    "description": "读取当前 RICH 用户的投资组合汇总，包括总资产、成本、收益、收益率和现金/权益资产概览。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用当前用户第一个组合"},
            "display_currency": {"type": "string", "description": "显示货币，默认 CNY"},
            "force_recalculate": {"type": "boolean", "description": "是否先强制重算并绕过缓存，默认 false"},
            "adjust_type": {"type": "string", "description": "复权类型：空字符串/qfq/hfq"},
        },
    },
}

_ASSET_POSITIONS_SCHEMA = {
    "name": "get_asset_positions",
    "description": "读取当前 RICH 用户的持仓明细，包括资产代码、名称、数量、价格、市值、成本、盈亏和权重。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用当前用户第一个组合"},
            "limit": {"type": "integer", "description": "返回条数，默认 50，最多 200"},
        },
    },
}

_ASSET_ALLOCATION_SCHEMA = {
    "name": "get_asset_allocation",
    "description": "读取当前 RICH 用户的资产配置，按当前权重/市值排序，并给出目标权重和偏离。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用当前用户第一个组合"}},
    },
}

_ASSET_TYPE_SCHEMA_FIELDS = {
    "code": {"type": "string", "description": "资产类型代码，交易记录创建前必须存在此代码"},
    "name": {"type": "string", "description": "资产类型名称"},
    "description": {"type": "string", "description": "说明，可选"},
    "category": {"type": "string", "description": "分类，默认 other"},
    "market_type": {"type": "string", "description": "field/external，默认 field"},
    "min_unit": {"type": "integer", "description": "最小交易单位，默认 1"},
    "price_source": {"type": "string", "description": "价格来源，默认 manual"},
    "price_precision": {"type": "integer", "description": "价格精度，默认 2"},
    "quantity_precision": {"type": "integer", "description": "数量精度，默认 4"},
    "use_market_data": {"type": "boolean", "description": "是否使用市场数据自动取价"},
    "linked_symbol": {"type": "string", "description": "关联行情标的代码，可选"},
}

_ASSET_TYPES_SCHEMA = {
    "name": "get_asset_types",
    "description": "读取当前用户资产类型列表。交易记录和持仓资产创建前，资产类型必须先存在。",
    "input_schema": {
        "type": "object",
        "properties": {"active_only": {"type": "boolean", "description": "是否只返回启用类型，默认 true"}},
    },
}

_ASSET_TYPE_PRESET_SCHEMA = {
    "name": "get_asset_type_preset",
    "description": "读取系统预设资产类型模板，用于快速创建资产类型。",
    "input_schema": {"type": "object", "properties": {}},
}

_CREATE_ASSET_TYPE_SCHEMA = {
    "name": "create_asset_type",
    "description": "创建资产类型。交易记录添加之前必须先有对应资产类型；需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": _ASSET_TYPE_SCHEMA_FIELDS,
        "required": ["code", "name"],
    },
}

_UPDATE_ASSET_TYPE_SCHEMA = {
    "name": "update_asset_type",
    "description": "更新资产类型名称、分类、精度、行情关联等信息。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"asset_type_id": {"type": "integer", "description": "资产类型 ID"}, **_ASSET_TYPE_SCHEMA_FIELDS, "is_active": {"type": "boolean", "description": "是否启用"}},
        "required": ["asset_type_id"],
    },
}

_DELETE_ASSET_TYPE_SCHEMA = {
    "name": "delete_asset_type",
    "description": "删除资产类型。若已有持仓或交易引用可能失败；需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"asset_type_id": {"type": "integer", "description": "资产类型 ID"}},
        "required": ["asset_type_id"],
    },
}

_DELETE_ASSET_TYPES_SCHEMA = {
    "name": "delete_asset_types",
    "description": "批量删除多个资产类型，同时清理关联的持仓资产。一次确认即可完成。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"asset_type_ids": {"type": "array", "items": {"type": "integer"}, "description": "资产类型 ID 列表"}},
        "required": ["asset_type_ids"],
    },
}

_CLEANUP_ORPHAN_ASSETS_SCHEMA = {
    "name": "cleanup_orphan_assets",
    "description": "清理当前用户组合中所有孤立持仓资产（即资产类型已被删除但持仓记录仍在的资产），需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}

_PORTFOLIO_ASSETS_SCHEMA = {
    "name": "get_portfolio_assets",
    "description": "读取组合持仓资产明细，等同持仓管理列表。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}, "limit": {"type": "integer", "description": "返回条数，默认 100"}},
    },
}

_ASSETS_SUMMARY_SCHEMA = {
    "name": "get_assets_summary",
    "description": "读取持仓资产摘要，包括资产类型数量、持仓数量、市值与收益概览。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}},
    },
}

_ADD_PORTFOLIO_ASSET_SCHEMA = {
    "name": "add_portfolio_asset",
    "description": "向组合添加持仓资产。资产类型必须先存在；需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "asset_type_code": {"type": "string", "description": "资产类型代码，必须已存在"},
            "target_weight": {"type": "number", "description": "目标权重，0-1 或百分比"},
            "current_quantity": {"type": "number", "description": "当前数量，默认 0"},
            "current_price": {"type": "number", "description": "当前价格，默认 0"},
        },
        "required": ["asset_type_code"],
    },
}

_UPDATE_PORTFOLIO_ASSET_SCHEMA = {
    "name": "update_portfolio_asset",
    "description": "更新组合持仓资产的目标权重、数量、价格等字段。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "asset_id": {"type": "integer", "description": "组合资产 ID"},
            "target_weight": {"type": "number", "description": "目标权重，0-1 或百分比，可选"},
            "current_quantity": {"type": "number", "description": "当前数量，可选"},
            "avg_cost_price": {"type": "number", "description": "平均成本价，可选"},
            "current_price": {"type": "number", "description": "当前价格，可选"},
        },
        "required": ["asset_id"],
    },
}

_UPDATE_PORTFOLIO_ASSET_PRICE_SCHEMA = {
    "name": "update_portfolio_asset_price",
    "description": "快速更新组合资产当前价格并重算市值/收益。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"asset_id": {"type": "integer", "description": "组合资产 ID"}, "current_price": {"type": "number", "description": "当前价格"}},
        "required": ["asset_id", "current_price"],
    },
}

_DELETE_PORTFOLIO_ASSET_SCHEMA = {
    "name": "delete_portfolio_asset",
    "description": "从组合中删除持仓资产记录。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"asset_id": {"type": "integer", "description": "组合资产 ID"}},
        "required": ["asset_id"],
    },
}

_RECENT_TRANSACTIONS_SCHEMA = {
    "name": "get_recent_transactions",
    "description": "读取当前 RICH 用户最近交易记录，可按资产代码筛选。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用当前用户第一个组合"},
            "asset_code": {"type": "string", "description": "资产代码，可选"},
            "limit": {"type": "integer", "description": "返回条数，默认 20，最多 100"},
        },
    },
}

_TRANSACTIONS_SCHEMA = {
    "name": "get_transactions",
    "description": "分页读取交易记录，可按组合、资产代码、交易类型和状态筛选。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "asset_code": {"type": "string", "description": "资产代码，可选"},
            "transaction_type": {"type": "string", "description": "buy/sell/dividend/bonus/rights，可选"},
            "status": {"type": "string", "description": "pending/completed，可选"},
            "limit": {"type": "integer", "description": "返回条数，默认 100，最多 300"},
            "offset": {"type": "integer", "description": "偏移量，默认 0"},
        },
    },
}

_TRANSACTION_FIELDS = {
    "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
    "asset_code": {"type": "string", "description": "资产代码；必须已有同 code 的资产类型"},
    "transaction_type": {"type": "string", "enum": ["buy", "sell", "dividend", "bonus", "rights"], "description": "交易类型"},
    "quantity": {"type": "number", "description": "数量，可选"},
    "price": {"type": "number", "description": "价格，可选"},
    "amount": {"type": "number", "description": "金额；若未传且有 quantity/price 会自动计算"},
    "transaction_date": {"type": "string", "description": "交易日期 YYYY-MM-DD，可选"},
    "reason": {"type": "string", "description": "原因，默认 manual"},
    "notes": {"type": "string", "description": "备注，可选"},
    "commission": {"type": "number", "description": "手续费，可选"},
    "tax": {"type": "number", "description": "税费，可选"},
    "status": {"type": "string", "enum": ["pending", "completed"], "description": "状态，默认 completed"},
    "price_currency": {"type": "string", "description": "计价货币，默认 CNY"},
    "commission_currency": {"type": "string", "description": "手续费货币，默认 CNY"},
    "original_currency": {"type": "string", "description": "原始货币，默认 CNY"},
    "original_amount": {"type": "number", "description": "原始金额，可选"},
    "settlement_currency": {"type": "string", "description": "结算货币，可选"},
    "settlement_amount": {"type": "number", "description": "结算金额，可选"},
    "settlement_rate": {"type": "number", "description": "结算汇率，可选"},
}

_CREATE_TRANSACTION_SCHEMA = {
    "name": "create_transaction",
    "description": "快速记录交易。对应资产类型必须先存在；如不存在，先调用 create_asset_type。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": _TRANSACTION_FIELDS,
        "required": ["asset_code", "transaction_type"],
    },
}

_UPDATE_TRANSACTION_SCHEMA = {
    "name": "update_transaction",
    "description": "更新交易记录的数量、价格、金额、费用、状态、备注等。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"transaction_id": {"type": "integer", "description": "交易记录 ID"}, **_TRANSACTION_FIELDS},
        "required": ["transaction_id"],
    },
}

_DELETE_TRANSACTION_SCHEMA = {
    "name": "delete_transaction",
    "description": "删除交易记录，并重算对应组合持仓。危险操作，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"transaction_id": {"type": "integer", "description": "交易记录 ID"}},
        "required": ["transaction_id"],
    },
}

_DELETE_TRANSACTIONS_SCHEMA = {
    "name": "delete_transactions",
    "description": "批量删除多条交易记录，并重算对应组合持仓。适用于清理大量交易记录，一次确认即可删除全部。危险操作，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"transaction_ids": {"type": "array", "items": {"type": "integer"}, "description": "交易记录 ID 列表"}},
        "required": ["transaction_ids"],
    },
}

_UPDATE_TRANSACTION_STATUS_SCHEMA = {
    "name": "update_transaction_status",
    "description": "快速更新交易状态 pending/completed。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"transaction_id": {"type": "integer", "description": "交易记录 ID"}, "status": {"type": "string", "enum": ["pending", "completed"], "description": "新状态"}},
        "required": ["transaction_id", "status"],
    },
}

_TRANSACTION_STATISTICS_SCHEMA = {
    "name": "get_transaction_statistics",
    "description": "读取交易统计，包括买入/卖出/分红数量和金额汇总。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}, "asset_code": {"type": "string", "description": "资产代码，可选"}},
    },
}

_IMPORT_ASSET_TYPE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "资产类型代码/交易标的代码"},
        "name": {"type": "string", "description": "资产类型名称；未知时可使用 code"},
        "description": {"type": "string", "description": "描述，可选"},
        "category": {"type": "string", "description": "类别，如 equity/fund/cash/bond/commodity/other"},
        "market_type": {"type": "string", "description": "field 或 external，默认 field"},
        "price_source": {"type": "string", "description": "manual 或 market，默认 manual"},
        "min_unit": {"type": "integer", "description": "最小交易单位，默认 1"},
        "price_precision": {"type": "integer", "description": "价格精度，默认 2"},
        "quantity_precision": {"type": "integer", "description": "数量精度，默认 4"},
        "use_market_data": {"type": "boolean", "description": "是否使用行情数据，默认 false"},
        "linked_symbol": {"type": "string", "description": "关联行情标的代码，可选"},
    },
    "required": ["code"],
}

_IMPORT_TRANSACTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": _TRANSACTION_FIELDS,
    "required": ["asset_code", "transaction_type"],
}

_PREVIEW_BUSINESS_IMPORT_SCHEMA = {
    "name": "preview_business_import",
    "description": "预览从用户上传表格中抽取的业务导入计划，只校验不写入。支持资产类型和交易记录，AI 应先从附件内容解析成 asset_types/transactions 后调用。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "source_name": {"type": "string", "description": "来源文件名或说明，可选"},
            "asset_types": {"type": "array", "items": _IMPORT_ASSET_TYPE_ITEM_SCHEMA, "description": "待导入/补全的资产类型列表，可为空"},
            "transactions": {"type": "array", "items": _IMPORT_TRANSACTION_ITEM_SCHEMA, "description": "待导入的交易记录列表，可为空"},
            "auto_create_asset_types": {"type": "boolean", "description": "交易引用不存在资产类型时是否在执行时自动创建，默认 true"},
            "duplicate_check": {"type": "boolean", "description": "是否检查疑似重复交易，默认 true"},
        },
    },
}

_EXECUTE_BUSINESS_IMPORT_SCHEMA = {
    "name": "execute_business_import",
    "description": "按预览过的导入计划批量创建资产类型和交易记录，并重算组合。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": _PREVIEW_BUSINESS_IMPORT_SCHEMA["input_schema"]["properties"],
    },
}

_PORTFOLIO_RISK_SCHEMA = {
    "name": "analyze_portfolio_risk",
    "description": "基于当前持仓和权重偏离分析组合集中度、再平衡风险和平衡度。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}},
    },
}

_PORTFOLIO_PERFORMANCE_SCHEMA = {
    "name": "analyze_portfolio_performance",
    "description": "读取组合收益表现摘要，包括收益、收益率、分红和近期交易概览。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "display_currency": {"type": "string", "description": "显示货币，默认 CNY"},
            "transaction_limit": {"type": "integer", "description": "附带最近交易数量，默认 10，最多 50"},
        },
    },
}

_REBALANCE_PLAN_SCHEMA = {
    "name": "calculate_rebalance_plan",
    "description": "根据当前权重与目标权重计算再平衡候选项，只预览不写入。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "threshold": {"type": "number", "description": "偏离阈值，默认 0.02，代表 2%"},
        },
    },
}

_EXECUTE_REBALANCE_SCHEMA = {
    "name": "execute_rebalance",
    "description": "执行投资组合再平衡重算。会写入组合资产计算结果，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "rebalancing_type": {"type": "string", "description": "再平衡类型，默认 forced"},
            "adjust_type": {"type": "string", "description": "复权类型：空字符串/qfq/hfq"},
        },
    },
}

_FORCE_RECALCULATE_SCHEMA = {
    "name": "force_recalculate_portfolio",
    "description": "强制重算投资组合持仓、市值、收益和权重。会写入计算结果，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "adjust_type": {"type": "string", "description": "复权类型：空字符串/qfq/hfq"},
        },
    },
}

_UPDATE_WEIGHTS_SCHEMA = {
    "name": "update_portfolio_weights",
    "description": "更新投资组合目标权重。target_weights 使用 0-1 小数；如果传 30 会自动按 30% 处理。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "target_weights": {
                "type": "object",
                "description": "资产代码到目标权重的映射，例如 {\"510300\": 0.4, \"518880\": 0.2}",
            },
        },
        "required": ["target_weights"],
    },
}

_DCA_PLANS_SCHEMA = {
    "name": "get_dca_plans",
    "description": "读取当前 RICH 用户的定投计划列表，包括金额、频率、状态、下次执行日和累计投入。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID，可选"},
            "enabled_only": {"type": "boolean", "description": "是否只返回启用计划，默认 false"},
        },
    },
}

_DCA_PLAN_DETAIL_SCHEMA = {
    "name": "get_dca_plan_detail",
    "description": "读取单个定投计划详情，包括资产分组成员。",
    "input_schema": {
        "type": "object",
        "properties": {"plan_id": {"type": "integer", "description": "定投计划 ID"}},
        "required": ["plan_id"],
    },
}

_DCA_ALLOCATION_SCHEMA = {
    "name": "preview_dca_allocation",
    "description": "预览定投计划本期分配结果，只计算不写入。",
    "input_schema": {
        "type": "object",
        "properties": {"plan_id": {"type": "integer", "description": "定投计划 ID"}},
        "required": ["plan_id"],
    },
}

_PENDING_DCA_SCHEMA = {
    "name": "get_pending_dca_plans",
    "description": "读取当前用户已到期、待执行的定投计划。",
    "input_schema": {"type": "object", "properties": {}},
}

_DCA_HISTORY_SCHEMA = {
    "name": "get_dca_execution_history",
    "description": "读取定投计划执行历史。",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": "定投计划 ID"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD，可选"},
        },
        "required": ["plan_id"],
    },
}

_DCA_STATISTICS_SCHEMA = {
    "name": "get_dca_statistics",
    "description": "读取定投计划执行统计，包括累计投入、执行次数、跳过次数和平均每期投入。",
    "input_schema": {
        "type": "object",
        "properties": {"plan_id": {"type": "integer", "description": "定投计划 ID"}},
        "required": ["plan_id"],
    },
}

_DCA_MEMBER_SCHEMA = {
    "type": "array",
    "description": "定投资产成员列表，可自动创建/更新计划专属分组",
    "items": {
        "type": "object",
        "properties": {
            "asset_type_code": {"type": "string", "description": "资产代码"},
            "asset_name": {"type": "string", "description": "资产名称，可选"},
            "target_weight": {"type": "number", "description": "目标权重，0-1 小数或百分比数值"},
        },
        "required": ["asset_type_code", "target_weight"],
    },
}

_CREATE_DCA_SCHEMA = {
    "name": "create_dca_plan",
    "description": "创建定投计划，可同时传入资产成员自动创建定投分组。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "name": {"type": "string", "description": "计划名称"},
            "description": {"type": "string", "description": "计划说明，可选"},
            "amount": {"type": "number", "description": "每期定投金额"},
            "frequency": {"type": "string", "enum": ["weekly", "bi-weekly", "monthly"], "description": "执行频率"},
            "allocation_strategy": {"type": "string", "enum": ["equal", "target_weight", "rebalance"], "description": "分配策略，默认 target_weight"},
            "high_price_strategy": {"type": "string", "enum": ["redistribute", "accumulate"], "description": "高价资产处理策略，默认 redistribute"},
            "dca_group_id": {"type": "integer", "description": "已有定投分组 ID，可选"},
            "members": _DCA_MEMBER_SCHEMA,
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
            "execution_day": {"type": "integer", "description": "月频为 1-31；周频为 0-6"},
        },
        "required": ["name", "amount", "frequency"],
    },
}

_UPDATE_DCA_SCHEMA = {
    "name": "update_dca_plan",
    "description": "更新定投计划的金额、频率、策略、分组成员或描述。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": "定投计划 ID"},
            "name": {"type": "string", "description": "计划名称，可选"},
            "description": {"type": "string", "description": "计划说明，可选"},
            "amount": {"type": "number", "description": "每期定投金额，可选"},
            "frequency": {"type": "string", "enum": ["weekly", "bi-weekly", "monthly"], "description": "执行频率，可选"},
            "allocation_strategy": {"type": "string", "enum": ["equal", "target_weight", "rebalance"], "description": "分配策略，可选"},
            "high_price_strategy": {"type": "string", "enum": ["redistribute", "accumulate"], "description": "高价资产策略，可选"},
            "dca_group_id": {"type": "integer", "description": "定投分组 ID，可选"},
            "members": _DCA_MEMBER_SCHEMA,
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
            "execution_day": {"type": "integer", "description": "执行日，可选"},
        },
        "required": ["plan_id"],
    },
}

_TOGGLE_DCA_SCHEMA = {
    "name": "toggle_dca_plan",
    "description": "启用或暂停定投计划。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": "定投计划 ID"},
            "enabled": {"type": "boolean", "description": "true 启用，false 暂停"},
        },
        "required": ["plan_id", "enabled"],
    },
}

_EXECUTE_DCA_SCHEMA = {
    "name": "execute_dca_plan",
    "description": "记录一次定投执行；默认生成待确认执行记录，不自动创建交易。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": "定投计划 ID"},
            "execution_date": {"type": "string", "description": "执行日期 YYYY-MM-DD，默认今天"},
            "status": {"type": "string", "enum": ["executed", "skipped", "partial", "pending_confirmation"], "description": "执行状态，默认 pending_confirmation"},
            "skip_reason": {"type": "string", "description": "跳过原因，可选"},
            "actual_allocations": {"type": "array", "items": {"type": "object"}, "description": "实际成交分配，可选"},
            "create_transactions": {"type": "boolean", "description": "是否创建交易记录，默认 false"},
        },
        "required": ["plan_id"],
    },
}

_RUN_DUE_DCA_SCHEMA = {
    "name": "run_due_dca_plans",
    "description": "扫描并为到期定投计划生成待确认执行记录。需要用户授权。",
    "input_schema": {"type": "object", "properties": {}},
}

_DELETE_DCA_PLAN_SCHEMA = {
    "name": "delete_dca_plan",
    "description": "删除定投计划及其执行记录。危险操作，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"plan_id": {"type": "integer", "description": "定投计划 ID"}},
        "required": ["plan_id"],
    },
}

_ASSET_GROUP_MEMBER_FIELDS = {
    "member_type": {"type": "string", "enum": ["asset_type", "asset_group"], "description": "成员类型"},
    "asset_type_code": {"type": "string", "description": "资产类型代码，member_type=asset_type 时必填"},
    "asset_group_id": {"type": "integer", "description": "嵌套分组 ID，member_type=asset_group 时必填"},
    "target_weight": {"type": "number", "description": "组内目标权重，0-1 或百分比"},
    "display_order": {"type": "integer", "description": "显示顺序，默认 0"},
}

_ASSET_GROUPS_SCHEMA = {
    "name": "get_asset_groups",
    "description": "读取投资组合资产分组列表。",
    "input_schema": {
        "type": "object",
        "properties": {"portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}, "parent_group_id": {"type": "integer", "description": "父分组 ID，可选"}},
    },
}

_ASSET_GROUP_DETAIL_SCHEMA = {
    "name": "get_asset_group_detail",
    "description": "读取资产分组详情及成员。",
    "input_schema": {
        "type": "object",
        "properties": {"group_id": {"type": "integer", "description": "资产分组 ID"}},
        "required": ["group_id"],
    },
}

_CREATE_ASSET_GROUP_SCHEMA = {
    "name": "create_asset_group",
    "description": "创建投资组合资产分组。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"},
            "name": {"type": "string", "description": "分组名称"},
            "description": {"type": "string", "description": "说明，可选"},
            "target_weight": {"type": "number", "description": "目标权重，0-1 或百分比，默认 0"},
            "parent_group_id": {"type": "integer", "description": "父分组 ID，可选"},
            "display_order": {"type": "integer", "description": "显示顺序，默认 0"},
            "group_type": {"type": "string", "enum": ["weighted", "unweighted"], "description": "分组类型，默认 weighted"},
        },
        "required": ["name"],
    },
}

_UPDATE_ASSET_GROUP_SCHEMA = {
    "name": "update_asset_group",
    "description": "更新资产分组名称、权重、父级或类型。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {
            "group_id": {"type": "integer", "description": "资产分组 ID"},
            "name": {"type": "string", "description": "分组名称，可选"},
            "description": {"type": "string", "description": "说明，可选"},
            "target_weight": {"type": "number", "description": "目标权重，可选"},
            "parent_group_id": {"type": "integer", "description": "父分组 ID，可选"},
            "display_order": {"type": "integer", "description": "显示顺序，可选"},
            "group_type": {"type": "string", "enum": ["weighted", "unweighted"], "description": "分组类型，可选"},
        },
        "required": ["group_id"],
    },
}

_DELETE_ASSET_GROUP_SCHEMA = {
    "name": "delete_asset_group",
    "description": "删除资产分组及其成员。危险操作，需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"group_id": {"type": "integer", "description": "资产分组 ID"}},
        "required": ["group_id"],
    },
}

_ADD_ASSET_GROUP_MEMBER_SCHEMA = {
    "name": "add_asset_group_member",
    "description": "向资产分组添加资产类型或嵌套分组成员。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"group_id": {"type": "integer", "description": "资产分组 ID"}, **_ASSET_GROUP_MEMBER_FIELDS},
        "required": ["group_id", "member_type", "target_weight"],
    },
}

_UPDATE_ASSET_GROUP_MEMBER_SCHEMA = {
    "name": "update_asset_group_member",
    "description": "更新资产分组成员权重或显示顺序。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"member_id": {"type": "integer", "description": "分组成员 ID"}, "target_weight": {"type": "number", "description": "目标权重，可选"}, "display_order": {"type": "integer", "description": "显示顺序，可选"}},
        "required": ["member_id"],
    },
}

_REMOVE_ASSET_GROUP_MEMBER_SCHEMA = {
    "name": "remove_asset_group_member",
    "description": "移除资产分组成员。需要用户授权。",
    "input_schema": {
        "type": "object",
        "properties": {"member_id": {"type": "integer", "description": "分组成员 ID"}},
        "required": ["member_id"],
    },
}

_VALIDATE_ASSET_GROUP_WEIGHTS_SCHEMA = {
    "name": "validate_asset_group_weights",
    "description": "校验资产分组成员权重是否合理。",
    "input_schema": {
        "type": "object",
        "properties": {"group_id": {"type": "integer", "description": "资产分组 ID"}},
        "required": ["group_id"],
    },
}

_GROUP_VALUE_SCHEMA = {
    "name": "get_group_value",
    "description": "计算资产分组当前市值、成本和收益。",
    "input_schema": {
        "type": "object",
        "properties": {"group_id": {"type": "integer", "description": "资产分组 ID"}, "portfolio_id": {"type": "integer", "description": "投资组合 ID；不传则使用第一个组合"}},
        "required": ["group_id"],
    },
}

_DCA_GROUP_MEMBER_FIELDS = {
    "asset_type_code": {"type": "string", "description": "资产类型代码"},
    "asset_name": {"type": "string", "description": "资产名称，可选"},
    "target_weight": {"type": "number", "description": "目标权重，0-1 或百分比"},
    "display_order": {"type": "integer", "description": "显示顺序，默认 0"},
}

_DCA_GROUPS_SCHEMA = {"name": "get_dca_groups", "description": "读取定投资产分组列表。", "input_schema": {"type": "object", "properties": {}}}
_DCA_GROUP_DETAIL_SCHEMA = {"name": "get_dca_group_detail", "description": "读取定投资产分组详情及成员。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}}, "required": ["group_id"]}}
_CREATE_DCA_GROUP_SCHEMA = {"name": "create_dca_group", "description": "创建定投资产分组。需要用户授权。", "input_schema": {"type": "object", "properties": {"name": {"type": "string", "description": "分组名称"}, "description": {"type": "string", "description": "说明，可选"}, "display_order": {"type": "integer", "description": "显示顺序，默认 0"}}, "required": ["name"]}}
_UPDATE_DCA_GROUP_SCHEMA = {"name": "update_dca_group", "description": "更新定投资产分组。需要用户授权。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}, "name": {"type": "string", "description": "分组名称，可选"}, "description": {"type": "string", "description": "说明，可选"}, "display_order": {"type": "integer", "description": "显示顺序，可选"}}, "required": ["group_id"]}}
_DELETE_DCA_GROUP_SCHEMA = {"name": "delete_dca_group", "description": "删除定投资产分组。危险操作，需要用户授权。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}}, "required": ["group_id"]}}
_SET_DCA_GROUP_MEMBERS_SCHEMA = {"name": "set_dca_group_members", "description": "整体替换定投分组成员。需要用户授权。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}, "members": _DCA_MEMBER_SCHEMA}, "required": ["group_id", "members"]}}
_ADD_DCA_GROUP_MEMBER_SCHEMA = {"name": "add_dca_group_member", "description": "向定投分组添加成员。需要用户授权。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}, **_DCA_GROUP_MEMBER_FIELDS}, "required": ["group_id", "asset_type_code", "target_weight"]}}
_UPDATE_DCA_GROUP_MEMBER_SCHEMA = {"name": "update_dca_group_member", "description": "更新定投分组成员。需要用户授权。", "input_schema": {"type": "object", "properties": {"member_id": {"type": "integer", "description": "成员 ID"}, "asset_name": {"type": "string", "description": "资产名称，可选"}, "target_weight": {"type": "number", "description": "目标权重，可选"}, "display_order": {"type": "integer", "description": "显示顺序，可选"}}, "required": ["member_id"]}}
_REMOVE_DCA_GROUP_MEMBER_SCHEMA = {"name": "remove_dca_group_member", "description": "移除定投分组成员。需要用户授权。", "input_schema": {"type": "object", "properties": {"member_id": {"type": "integer", "description": "成员 ID"}}, "required": ["member_id"]}}
_VALIDATE_DCA_GROUP_WEIGHTS_SCHEMA = {"name": "validate_dca_group_weights", "description": "校验定投分组成员权重是否合计为 100%。", "input_schema": {"type": "object", "properties": {"group_id": {"type": "integer", "description": "定投分组 ID"}}, "required": ["group_id"]}}

_MARKET_SYMBOL_SEARCH_SCHEMA = {
    "name": "search_market_symbols",
    "description": "搜索市场标的，用于打开 K 线或查询行情数据前确认代码。",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "标的代码或名称关键词"}, "limit": {"type": "integer", "description": "返回条数，默认 20"}},
        "required": ["query"],
    },
}

_MARKET_SYMBOL_LIST_SCHEMA = {
    "name": "list_market_symbols",
    "description": "列出已有市场标的配置，可按类型/关键词筛选。",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "关键词，可选"}, "symbol_type": {"type": "string", "description": "标的类型，可选"}, "limit": {"type": "integer", "description": "返回条数，默认 50"}},
    },
}

_KLINE_HISTORY_SCHEMA = {
    "name": "get_kline_history",
    "description": "读取指定标的 K 线历史数据。",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "标的代码"},
            "interval": {"type": "string", "description": "daily/weekly/monthly/1min/5min/15min/30min/60min，默认 daily"},
            "adjust_type": {"type": "string", "description": "复权类型：空字符串/qfq/hfq，默认空字符串"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD，可选"},
            "limit": {"type": "integer", "description": "返回条数，默认 120，最多 500"},
        },
        "required": ["symbol"],
    },
}

_ANALYZE_KLINE_SCHEMA = {
    "name": "analyze_kline",
    "description": "分析指定标的 K 线走势、涨跌幅、波动率、均线、成交量和估值摘要。",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "标的代码"},
            "interval": {"type": "string", "description": "周期，默认 daily"},
            "adjust_type": {"type": "string", "description": "复权类型，默认空字符串"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD，可选"},
            "limit": {"type": "integer", "description": "分析最近 N 根 K 线，默认 120，最多 500"},
        },
        "required": ["symbol"],
    },
}

_VALUATION_DATA_SCHEMA = {
    "name": "query_valuation_data",
    "description": "查询标的估值指标历史，包括 PE/PB/PS/PCF 和市值。",
    "input_schema": {
        "type": "object",
        "properties": {"symbol": {"type": "string", "description": "标的代码"}, "limit": {"type": "integer", "description": "返回条数，默认 120"}},
        "required": ["symbol"],
    },
}

_FACTOR_QUERY_SCHEMA = {
    "name": "query_factors",
    "description": "查询标的历史因子/技术指标摘要，目前返回换手率、涨跌幅和交易状态。",
    "input_schema": {
        "type": "object",
        "properties": {"symbol": {"type": "string", "description": "标的代码"}, "limit": {"type": "integer", "description": "返回条数，默认 120"}},
        "required": ["symbol"],
    },
}

# ── Execute functions ────────────────────────────────────────────────────────


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _json_result(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=_json_default, indent=2)


def _add_rich_backend_path() -> None:
    for path in (_RICH_BACKEND, _RICH_APP):
        if path not in sys.path:
            sys.path.insert(0, path)


@contextmanager
def _rich_db_session() -> Iterator[Any]:
    _add_rich_backend_path()
    from app.core.database.connection import SessionLocal  # type: ignore

    if SessionLocal is None:
        raise RuntimeError("RICH database session factory is not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _rich_user_id(config: Dict[str, Any]) -> int:
    raw_user_id = (config or {}).get("rich_user_id") or os.getenv("RICH_AGENT_USER_ID")
    if raw_user_id in (None, ""):
        raise ValueError("RICH Agent 尚未绑定当前登录用户，不能读取或修改业务数据。请先通过 RICH 登录态进入 Agent，或设置 RICH_AGENT_USER_ID。")
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("RICH Agent 用户上下文无效，不能读取或修改业务数据。") from exc
    if user_id <= 0:
        raise ValueError("RICH Agent 用户上下文无效，不能读取或修改业务数据。")
    return user_id


def _business_error(message: str) -> str:
    return _json_result({"success": False, "error": message})


def _with_business_error(func):
    def _wrapped(params: Dict[str, Any], config: Dict[str, Any]) -> str:
        try:
            return func(params, config)
        except Exception as exc:
            return _business_error(str(exc))
    return _wrapped


def _optional_int(params: Dict[str, Any], name: str) -> Optional[int]:
    value = params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _required_int(params: Dict[str, Any], name: str) -> int:
    value = _optional_int(params, name)
    if value is None:
        raise ValueError(f"缺少必要参数: {name}")
    return value


def _limit(params: Dict[str, Any], default: int, maximum: int) -> int:
    value = _optional_int(params, "limit")
    if value is None:
        return default
    return max(1, min(value, maximum))


def _bool_param(params: Dict[str, Any], name: str, default: bool = False) -> bool:
    value = params.get(name)
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "t"}
    return bool(value)


def _decimal_param(params: Dict[str, Any], name: str, default: Optional[Decimal] = None) -> Optional[Decimal]:
    value = params.get(name)
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"参数 {name} 必须是数字") from exc


def _parse_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(f"日期格式无效: {value}，应为 YYYY-MM-DD") from exc


def _normalize_weight(value: Any) -> Decimal:
    weight = Decimal(str(value))
    if weight > 1:
        weight = weight / Decimal("100")
    if weight < 0:
        raise ValueError("目标权重不能为负数")
    return weight


def _normalize_members(members: Any) -> Optional[List[Dict[str, Any]]]:
    if members in (None, ""):
        return None
    if not isinstance(members, list):
        raise ValueError("members 必须是数组")
    normalized: List[Dict[str, Any]] = []
    for item in members:
        if not isinstance(item, dict):
            raise ValueError("members 中的每一项必须是对象")
        code = str(item.get("asset_type_code") or "").strip()
        if not code:
            raise ValueError("members 中缺少 asset_type_code")
        normalized.append({
            "asset_type_code": code,
            "asset_name": str(item.get("asset_name") or code),
            "target_weight": float(_normalize_weight(item.get("target_weight", 0))),
        })
    return normalized


def _resolve_portfolio(db: Any, user_id: int, portfolio_id: Optional[int]) -> Any:
    from app.core.database.models.portfolio import Portfolio  # type: ignore

    query = db.query(Portfolio).filter(Portfolio.user_id == user_id)
    if portfolio_id is not None:
        portfolio = query.filter(Portfolio.id == portfolio_id).first()
    else:
        portfolio = query.order_by(Portfolio.created_at.asc()).first()
    if not portfolio:
        raise ValueError("当前用户没有可访问的投资组合")
    return portfolio


def _asset_name_map(db: Any, user_id: int, codes: list[str]) -> dict[str, str]:
    if not codes:
        return {}
    from app.core.database.models.portfolio import AssetType  # type: ignore

    rows = db.query(AssetType).filter(
        AssetType.user_id == user_id,
        AssetType.code.in_(codes),
    ).all()
    return {str(row.code): str(row.name or row.code) for row in rows}


def _offset(params: Dict[str, Any]) -> int:
    value = _optional_int(params, "offset")
    return max(0, value or 0)


def _parse_datetime(value: Any) -> Optional[datetime]:
    parsed = _parse_date(value)
    if parsed is None:
        return None
    return datetime.combine(parsed, datetime.min.time())


def _row_dict(row: Any, fields: List[str]) -> Dict[str, Any]:
    return {field: getattr(row, field, None) for field in fields}


def _asset_type_dict(row: Any) -> Dict[str, Any]:
    return _row_dict(row, [
        "id", "user_id", "code", "name", "description", "category", "market_type",
        "min_unit", "price_source", "price_precision", "quantity_precision", "use_market_data",
        "linked_symbol", "is_active", "created_at",
    ])


def _portfolio_asset_dict(row: Any, asset_name: Optional[str] = None) -> Dict[str, Any]:
    payload = _row_dict(row, [
        "id", "portfolio_id", "asset_type_code", "target_weight", "current_quantity",
        "avg_cost_price", "current_price", "current_value", "total_cost", "profit_amount",
        "profit_rate", "current_weight", "deviation", "total_dividend", "created_at", "updated_at",
    ])
    payload["asset_name"] = asset_name or payload.get("asset_type_code")
    return payload


def _transaction_dict(row: Any, asset_name: Optional[str] = None) -> Dict[str, Any]:
    payload = _row_dict(row, [
        "id", "portfolio_id", "asset_code", "transaction_type", "quantity", "price", "amount",
        "transaction_date", "reason", "notes", "commission", "tax", "status", "created_at",
        "price_currency", "commission_currency", "original_amount", "original_currency",
        "settlement_currency", "settlement_amount", "settlement_rate",
    ])
    payload["asset_name"] = asset_name or payload.get("asset_code")
    return payload


def _asset_group_member_dict(row: Any) -> Dict[str, Any]:
    return _row_dict(row, ["id", "group_id", "member_type", "asset_type_code", "asset_group_id", "target_weight", "display_order"])


def _asset_group_dict(row: Any, include_members: bool = False) -> Dict[str, Any]:
    payload = _row_dict(row, [
        "id", "portfolio_id", "template_id", "name", "description", "group_type",
        "target_weight", "current_weight", "current_value", "total_cost", "profit_amount",
        "profit_rate", "display_order", "is_expanded", "parent_group_id", "created_at", "updated_at",
    ])
    if include_members:
        payload["members"] = [_asset_group_member_dict(member) for member in getattr(row, "members", [])]
    return payload


def _dca_group_member_dict(row: Any) -> Dict[str, Any]:
    return _row_dict(row, ["id", "group_id", "asset_type_code", "asset_name", "target_weight", "display_order", "created_at"])


def _dca_group_dict(row: Any, include_members: bool = False) -> Dict[str, Any]:
    payload = _row_dict(row, ["id", "user_id", "name", "description", "display_order", "created_at", "updated_at"])
    if include_members:
        payload["members"] = [_dca_group_member_dict(member) for member in getattr(row, "members", [])]
    return payload


def _ensure_asset_type_exists(db: Any, user_id: int, asset_code: str) -> Any:
    from app.core.database.models.portfolio import AssetType  # type: ignore

    asset_type = db.query(AssetType).filter(AssetType.user_id == user_id, AssetType.code == asset_code).first()
    if not asset_type:
        raise ValueError(f"资产类型 {asset_code} 不存在。交易记录和持仓添加前必须先创建资产类型；请先调用 create_asset_type。")
    return asset_type


def _recalculate_after_asset_change(db: Any, user_id: int, portfolio_id: int, asset_code: Optional[str] = None) -> None:
    try:
        from db_helpers_orm import recalculate_all_portfolio_assets_orm, recalculate_portfolio_asset_orm  # type: ignore
        if asset_code:
            recalculate_portfolio_asset_orm(db, portfolio_id, asset_code, user_id)
        recalculate_all_portfolio_assets_orm(db, portfolio_id, user_id)
    except TypeError:
        from db_helpers_orm import recalculate_all_portfolio_assets_orm  # type: ignore
        recalculate_all_portfolio_assets_orm(db, portfolio_id, user_id, "")


def _kline_interval(value: Any) -> str:
    raw = str(value or "daily").strip()
    mapping = {"D": "daily", "1D": "daily", "W": "weekly", "M": "monthly", "1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "60min"}
    return mapping.get(raw.upper(), raw.lower())


def _historical_query(db: Any, params: Dict[str, Any]) -> Any:
    from app.plugins.quant.database.models.backtest_historical_data import BacktestHistoricalData  # type: ignore

    symbol = str(params.get("symbol") or "").strip()
    if not symbol:
        raise ValueError("symbol 不能为空")
    query = db.query(BacktestHistoricalData).filter(
        BacktestHistoricalData.symbol == symbol,
        BacktestHistoricalData.interval == _kline_interval(params.get("interval")),
        BacktestHistoricalData.adjust_type == str(params.get("adjust_type") or ""),
    )
    start_date = _parse_date(params.get("start_date"))
    end_date = _parse_date(params.get("end_date"))
    if start_date:
        query = query.filter(BacktestHistoricalData.date >= start_date)
    if end_date:
        query = query.filter(BacktestHistoricalData.date <= end_date)
    return query.order_by(BacktestHistoricalData.timestamp.desc())


def _kline_dict(row: Any) -> Dict[str, Any]:
    return _row_dict(row, [
        "id", "symbol", "timestamp", "date", "interval", "adjust_type", "open_price", "high_price",
        "low_price", "close_price", "preclose_price", "volume", "amount", "tradestatus", "is_st",
        "is_delisted", "is_suspended", "turn", "pct_chg", "pe_ttm", "pb_mrq", "ps_ttm",
        "pcf_ncf_ttm", "total_market_cap", "circulating_market_cap",
    ])


def _portfolio_context(portfolio: Any) -> dict[str, Any]:
    return {
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "currency": getattr(portfolio, "currency", "CNY"),
    }


def _allocation_result_dict(result: Any) -> Dict[str, Any]:
    return {
        "asset_type_code": result.asset_type_code,
        "asset_name": result.asset_name,
        "target_weight": result.target_weight,
        "allocated_amount": result.allocated_amount,
        "allocated_quantity": result.allocated_quantity,
        "current_price": result.current_price,
        "market_type": result.market_type,
        "min_unit": result.min_unit,
        "suggested_quantity": result.suggested_quantity,
        "suggested_amount": result.suggested_amount,
        "deviation": result.deviation,
        "accumulated_amount": result.accumulated_amount,
        "periods_to_buy": result.periods_to_buy,
        "can_buy_now": result.can_buy_now,
        "status": result.status,
    }


def _execution_dict(execution: Any) -> Dict[str, Any]:
    return {
        "id": execution.id,
        "plan_id": execution.plan_id,
        "execution_date": execution.execution_date,
        "planned_amount": execution.planned_amount,
        "actual_amount": execution.actual_amount,
        "status": execution.status,
        "skip_reason": execution.skip_reason,
        "planned_allocations": json.loads(execution.planned_allocations or "[]"),
        "actual_allocations": json.loads(execution.actual_allocations or "[]") if execution.actual_allocations else None,
        "created_at": execution.created_at,
    }


def _exec_navigate(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    path = str(params.get("path") or "")
    title = str(params.get("title") or "")
    return (
        f"[RICH_NAVIGATE] path={path} title={title}\n"
        f"导航操作已提交：{title or path}。前端将自动跳转到该页面。"
    )


def _exec_portfolios(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.portfolio_service import PortfolioService  # type: ignore

        portfolios = PortfolioService(db).get_all_portfolios(user_id)
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "portfolios": portfolios, "count": len(portfolios)})


def _exec_open_symbol_chart(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    symbol = str(params.get("symbol") or "").strip()
    if not symbol:
        raise ValueError("symbol 不能为空")
    interval = str(params.get("interval") or "D").strip() or "D"
    adjust = str(params.get("adjust") or "").strip()
    query: Dict[str, str] = {"symbol": symbol, "interval": interval}
    if adjust:
        query["adjust"] = adjust
    if params.get("from"):
        query["from"] = str(params.get("from"))
    if params.get("to"):
        query["to"] = str(params.get("to"))
    path = "/chart?" + urlencode(query)
    return f"[RICH_NAVIGATE] path={path} title=K线图 {symbol}\n已打开 {symbol} 的 K 线图。"


def _exec_create_portfolio(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    name = str(params.get("name") or "").strip()
    if not name:
        raise ValueError("name 不能为空")
    total_assets = float(_decimal_param(params, "total_assets", Decimal("0")) or 0)
    with _rich_db_session() as db:
        from app.services.portfolio_service import PortfolioService  # type: ignore
        portfolio = PortfolioService(db).create_portfolio(user_id, name, total_assets)
        return _json_result({"success": True, "message": "投资组合已创建", "portfolio": _portfolio_context(portfolio)})


def _exec_update_portfolio(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    portfolio_id = _required_int(params, "portfolio_id")
    with _rich_db_session() as db:
        from app.services.portfolio_service import PortfolioService  # type: ignore
        total_assets = _decimal_param(params, "total_assets") if "total_assets" in params else None
        portfolio = PortfolioService(db).update_portfolio(
            user_id,
            portfolio_id,
            name=str(params.get("name")).strip() if params.get("name") not in (None, "") else None,
            total_assets=float(total_assets) if total_assets is not None else None,
        )
        return _json_result({"success": True, "message": "投资组合已更新", "portfolio": _portfolio_context(portfolio)})


def _exec_delete_portfolio(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    portfolio_id = _required_int(params, "portfolio_id")
    with _rich_db_session() as db:
        from app.services.portfolio_service import PortfolioService  # type: ignore
        PortfolioService(db).delete_portfolio(user_id, portfolio_id)
        return _json_result({"success": True, "message": "投资组合已删除", "portfolio_id": portfolio_id})


def _exec_portfolio_detail(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.services.portfolio_service import PortfolioService  # type: ignore

        detail = PortfolioService(db).get_portfolio(user_id, portfolio.id)
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "portfolio": _portfolio_context(portfolio), "data": detail})


def _exec_dashboard_summary(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.services.portfolio_service import PortfolioService  # type: ignore

        summary = PortfolioService(db).get_dashboard_summary(
            user_id,
            portfolio.id,
            str(params.get("adjust_type") or ""),
            _bool_param(params, "force_recalculate"),
        )
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "portfolio": _portfolio_context(portfolio), "data": summary})


def _exec_portfolio_summary(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    portfolio_id = _optional_int(params, "portfolio_id")
    display_currency = str(params.get("display_currency") or "CNY").upper()
    force_recalculate = _bool_param(params, "force_recalculate", False)
    adjust_type = str(params.get("adjust_type") or "")
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, portfolio_id)
        from app.services.currency_service import CurrencyService  # type: ignore

        if force_recalculate:
            from app.services.cache_service import cache_clear_portfolio  # type: ignore
            from db_helpers_orm import recalculate_all_portfolio_assets_orm  # type: ignore
            recalculate_all_portfolio_assets_orm(db, portfolio.id, user_id, adjust_type)
            cache_clear_portfolio(portfolio.id)

        summary = CurrencyService(db).get_portfolio_summary_with_currency(portfolio.id, display_currency, use_cache=not force_recalculate)
        summary["pnl_terms"] = {
            "summary.total_profit": "组合口径：当前权益市值 - 净投入 + 累计分红",
            "equity_assets[].profit": "单项当前持仓口径：当前市值 - 当前剩余持仓成本，不含分红",
            "summary.total_cost": "净投入：历史买入金额 - 历史卖出金额",
            "summary.holding_cost": "当前剩余持仓成本",
        }
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "portfolio": _portfolio_context(portfolio),
            "display_currency": display_currency,
            "data": summary,
        })


def _position_rows(db: Any, user_id: int, portfolio_id: int, limit: int, active_only: bool = False) -> list[dict[str, Any]]:
    from app.core.database.models.portfolio import PortfolioAsset  # type: ignore

    query = db.query(PortfolioAsset).filter(
        PortfolioAsset.portfolio_id == portfolio_id,
    )
    if active_only:
        query = query.filter(PortfolioAsset.current_quantity > 0)
    rows = query.order_by(PortfolioAsset.current_value.desc()).limit(limit).all()
    names = _asset_name_map(db, user_id, [str(row.asset_type_code) for row in rows])
    return [
        {
            "asset_code": row.asset_type_code,
            "asset_name": names.get(str(row.asset_type_code), str(row.asset_type_code)),
            "target_weight": row.target_weight,
            "current_weight": row.current_weight,
            "deviation": row.deviation,
            "current_quantity": row.current_quantity,
            "avg_cost_price": row.avg_cost_price,
            "current_price": row.current_price,
            "current_value": row.current_value,
            "holding_cost": row.total_cost,
            "unrealized_profit": (row.current_value or Decimal("0")) - (row.total_cost or Decimal("0")),
            "unrealized_profit_rate": (((row.current_value or Decimal("0")) - (row.total_cost or Decimal("0"))) / row.total_cost * Decimal("100")) if row.total_cost and row.total_cost > 0 else Decimal("0"),
            "cumulative_profit_amount": row.profit_amount,
            "cumulative_profit_rate": row.profit_rate,
            "total_dividend": row.total_dividend,
        }
        for row in rows
    ]


def _exec_asset_positions(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        positions = _position_rows(db, user_id, portfolio.id, _limit(params, 50, 200), active_only=True)
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "portfolio": _portfolio_context(portfolio),
            "positions": positions,
            "count": len(positions),
            "position_scope": "current_quantity > 0",
            "pnl_terms": {
                "unrealized_profit": "当前市值 - 当前剩余持仓成本，不含已清仓标的和分红",
                "cumulative_profit_amount": "当前市值 + 历史卖出收入/分红 - 历史买入成本，包含已实现部分",
                "holding_cost": "当前剩余持仓成本",
            },
        })


def _exec_asset_allocation(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        positions = _position_rows(db, user_id, portfolio.id, 200)
        allocation = [
            {
                "asset_code": item["asset_code"],
                "asset_name": item["asset_name"],
                "current_value": item["current_value"],
                "current_weight": item["current_weight"],
                "target_weight": item["target_weight"],
                "deviation": item["deviation"],
            }
            for item in positions
        ]
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "portfolio": _portfolio_context(portfolio),
            "allocation": allocation,
            "count": len(allocation),
        })


def _exec_asset_types(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    active_only = _bool_param(params, "active_only", True)
    with _rich_db_session() as db:
        from app.services.asset_service import AssetService  # type: ignore
        rows = AssetService(db).get_asset_types(user_id, is_active=True if active_only else None)
        return _json_result({"success": True, "asset_types": rows, "count": len(rows), "transaction_prerequisite": "创建交易前必须先存在对应资产类型 code"})


def _exec_asset_type_preset(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    return _json_result({
        "success": True,
        "presets": [
            {"code": "CASH", "name": "现金", "category": "cash", "market_type": "field", "price_source": "manual"},
            {"code": "STOCK", "name": "股票", "category": "equity", "market_type": "external", "price_source": "market", "use_market_data": True},
            {"code": "FUND", "name": "基金", "category": "fund", "market_type": "external", "price_source": "market", "use_market_data": True},
            {"code": "BOND", "name": "债券", "category": "fixed_income", "market_type": "field", "price_source": "manual"},
            {"code": "GOLD", "name": "黄金", "category": "commodity", "market_type": "external", "price_source": "market", "use_market_data": True},
        ],
    })


def _exec_create_asset_type(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    code = str(params.get("code") or "").strip()
    name = str(params.get("name") or "").strip()
    if not code or not name:
        raise ValueError("code 和 name 不能为空")
    with _rich_db_session() as db:
        from app.services.asset_service import AssetService  # type: ignore
        row = AssetService(db).create_asset_type(
            user_id=user_id,
            code=code,
            name=name,
            description=params.get("description"),
            category=params.get("category") or "other",
            market_type=params.get("market_type") or "field",
            min_unit=int(params.get("min_unit") or 1),
            price_source=params.get("price_source") or "manual",
            price_precision=int(params.get("price_precision") or 2),
            quantity_precision=int(params.get("quantity_precision") or 4),
            use_market_data=_bool_param(params, "use_market_data", False),
            linked_symbol=params.get("linked_symbol"),
        )
        return _json_result({"success": True, "message": "资产类型已创建，现在可以用该 code 记录交易或添加持仓", "asset_type": _asset_type_dict(row)})


def _exec_update_asset_type(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_type_id = _required_int(params, "asset_type_id")
    allowed = {"code", "name", "description", "category", "market_type", "min_unit", "price_source", "price_precision", "quantity_precision", "use_market_data", "linked_symbol", "is_active"}
    data = {key: params[key] for key in allowed if key in params and params[key] is not None}
    with _rich_db_session() as db:
        from app.services.asset_service import AssetService  # type: ignore
        row = AssetService(db).update_asset_type(user_id, asset_type_id, **data)
        return _json_result({"success": True, "message": "资产类型已更新", "asset_type": _asset_type_dict(row)})


def _exec_delete_asset_type(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_type_id = _required_int(params, "asset_type_id")
    with _rich_db_session() as db:
        from app.services.asset_service import AssetService  # type: ignore
        AssetService(db).delete_asset_type(user_id, asset_type_id)
        return _json_result({"success": True, "message": "资产类型已删除", "asset_type_id": asset_type_id})


def _exec_delete_asset_types(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    raw_ids = params.get("asset_type_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) == 0:
        raise ValueError("asset_type_ids 必须是非空数组")
    ids: List[int] = []
    for item in raw_ids:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            raise ValueError(f"asset_type_ids 包含无效的整数: {item}")
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import AssetType, Portfolio, PortfolioAsset  # type: ignore

        rows = db.query(AssetType).filter(
            AssetType.id.in_(ids),
            AssetType.user_id == user_id,
        ).all()
        codes = [str(row.code) for row in rows]

        deleted_asset_count = 0
        if codes:
            portfolio_assets = db.query(PortfolioAsset).join(
                Portfolio, PortfolioAsset.portfolio_id == Portfolio.id
            ).filter(
                PortfolioAsset.asset_type_code.in_(codes),
                Portfolio.user_id == user_id,
            ).all()
            for pa in portfolio_assets:
                db.delete(pa)
            deleted_asset_count = len(portfolio_assets)
            db.flush()

        for row in rows:
            db.delete(row)

        db.commit()

        msg = f"已批量删除 {len(rows)} 个资产类型"
        if deleted_asset_count:
            msg += f"，同时清理了 {deleted_asset_count} 条关联持仓资产"

        return _json_result({
            "success": True,
            "message": msg,
            "deleted_type_ids": [row.id for row in rows],
            "cleaned_assets": deleted_asset_count,
            "type_count": len(rows),
        })


def _exec_cleanup_orphan_assets(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import AssetType, Portfolio, PortfolioAsset  # type: ignore

        valid_codes = {row.code for row in db.query(AssetType.code).filter(AssetType.user_id == user_id).all()}
        orphaned = db.query(PortfolioAsset).join(
            Portfolio, PortfolioAsset.portfolio_id == Portfolio.id
        ).filter(
            Portfolio.user_id == user_id,
            ~PortfolioAsset.asset_type_code.in_(valid_codes) if valid_codes else True,
        ).all()

        if not orphaned:
            return _json_result({"success": True, "message": "没有孤立持仓资产需要清理", "cleaned": 0})

        for pa in orphaned:
            db.delete(pa)
        db.commit()

        return _json_result({
            "success": True,
            "message": f"已清理 {len(orphaned)} 条孤立持仓资产",
            "cleaned": len(orphaned),
            "cleaned_codes": list({str(pa.asset_type_code) for pa in orphaned}),
        })


def _exec_portfolio_assets(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import PortfolioAsset  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        rows = db.query(PortfolioAsset).filter(PortfolioAsset.portfolio_id == portfolio.id).order_by(PortfolioAsset.current_value.desc()).limit(_limit(params, 100, 300)).all()
        names = _asset_name_map(db, user_id, [str(row.asset_type_code) for row in rows])
        assets = [_portfolio_asset_dict(row, names.get(str(row.asset_type_code))) for row in rows]
        return _json_result({"success": True, "portfolio": _portfolio_context(portfolio), "assets": assets, "count": len(assets)})


def _exec_assets_summary(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        positions = _position_rows(db, user_id, portfolio.id, 300, active_only=True)
        total_value = sum(Decimal(str(item.get("current_value") or 0)) for item in positions)
        holding_cost = sum(Decimal(str(item.get("holding_cost") or 0)) for item in positions)
        unrealized_profit = sum(Decimal(str(item.get("unrealized_profit") or 0)) for item in positions)
        cumulative_profit = sum(Decimal(str(item.get("cumulative_profit_amount") or 0)) for item in positions)
        return _json_result({
            "success": True,
            "portfolio": _portfolio_context(portfolio),
            "asset_count": len(positions),
            "position_scope": "current_quantity > 0",
            "total_value": total_value,
            "holding_cost": holding_cost,
            "unrealized_profit": unrealized_profit,
            "cumulative_profit": cumulative_profit,
            "pnl_terms": {
                "unrealized_profit": "当前市值 - 当前剩余持仓成本，不含已清仓标的和分红",
                "cumulative_profit": "当前持仓维度的累计收益字段，不等同组合净投入收益",
            },
        })


def _exec_add_portfolio_asset(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_code = str(params.get("asset_type_code") or "").strip()
    if not asset_code:
        raise ValueError("asset_type_code 不能为空")
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import PortfolioAsset  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        asset_type = _ensure_asset_type_exists(db, user_id, asset_code)
        existing = db.query(PortfolioAsset).filter(PortfolioAsset.portfolio_id == portfolio.id, PortfolioAsset.asset_type_code == asset_code).first()
        if existing:
            raise ValueError(f"组合中已存在资产 {asset_code}，请使用 update_portfolio_asset 更新")
        quantity = _decimal_param(params, "current_quantity", Decimal("0")) or Decimal("0")
        price = _decimal_param(params, "current_price", Decimal("0")) or Decimal("0")
        target = _normalize_weight(params.get("target_weight", 0))
        row = PortfolioAsset(
            portfolio_id=portfolio.id,
            asset_type_code=asset_code,
            target_weight=target,
            current_quantity=quantity,
            current_price=price,
            current_value=quantity * price,
            current_weight=Decimal("0"),
            deviation=-target,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        _recalculate_after_asset_change(db, user_id, portfolio.id, asset_code)
        return _json_result({"success": True, "message": "组合资产已添加", "asset": _portfolio_asset_dict(row, asset_type.name)})


def _exec_update_portfolio_asset(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_id = _required_int(params, "asset_id")
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import PortfolioAsset  # type: ignore
        row = db.query(PortfolioAsset).filter(PortfolioAsset.id == asset_id).first()
        if not row:
            raise ValueError("组合资产不存在")
        portfolio = _resolve_portfolio(db, user_id, row.portfolio_id)
        if "target_weight" in params and params.get("target_weight") is not None:
            row.target_weight = _normalize_weight(params.get("target_weight"))
        for field in ("current_quantity", "avg_cost_price", "current_price"):
            value = _decimal_param(params, field) if field in params else None
            if value is not None:
                setattr(row, field, value)
        row.current_value = Decimal(str(row.current_quantity or 0)) * Decimal(str(row.current_price or 0))
        row.total_cost = Decimal(str(row.current_quantity or 0)) * Decimal(str(row.avg_cost_price or 0))
        row.profit_amount = Decimal(str(row.current_value or 0)) - Decimal(str(row.total_cost or 0))
        row.profit_rate = (row.profit_amount / row.total_cost) if row.total_cost else Decimal("0")
        db.commit()
        db.refresh(row)
        _recalculate_after_asset_change(db, user_id, portfolio.id, str(row.asset_type_code))
        names = _asset_name_map(db, user_id, [str(row.asset_type_code)])
        return _json_result({"success": True, "message": "组合资产已更新", "asset": _portfolio_asset_dict(row, names.get(str(row.asset_type_code)))})


def _exec_update_portfolio_asset_price(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    params = {**params, "current_price": params.get("current_price")}
    return _exec_update_portfolio_asset(params, config)


def _exec_delete_portfolio_asset(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_id = _required_int(params, "asset_id")
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import PortfolioAsset  # type: ignore
        row = db.query(PortfolioAsset).filter(PortfolioAsset.id == asset_id).first()
        if not row:
            raise ValueError("组合资产不存在")
        portfolio = _resolve_portfolio(db, user_id, row.portfolio_id)
        asset_code = str(row.asset_type_code)
        db.delete(row)
        db.commit()
        _recalculate_after_asset_change(db, user_id, portfolio.id, asset_code)
        return _json_result({"success": True, "message": "组合资产已删除", "asset_id": asset_id})


def _exec_recent_transactions(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    return _exec_transactions({**params, "limit": min(_limit(params, 20, 100), 100)}, config)


def _exec_transactions(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_code = str(params.get("asset_code") or "").strip()
    transaction_type = str(params.get("transaction_type") or "").strip()
    status = str(params.get("status") or "").strip()
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.core.database.models.transaction import Transaction  # type: ignore

        query = db.query(Transaction).filter(Transaction.portfolio_id == portfolio.id)
        if asset_code:
            query = query.filter(Transaction.asset_code == asset_code)
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        if status:
            query = query.filter(Transaction.status == status)
        total = query.count()
        rows = query.order_by(Transaction.transaction_date.desc()).offset(_offset(params)).limit(_limit(params, 100, 300)).all()
        names = _asset_name_map(db, user_id, [str(row.asset_code) for row in rows if row.asset_code])
        transactions = [_transaction_dict(row, names.get(str(row.asset_code))) for row in rows]
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "portfolio": _portfolio_context(portfolio), "transactions": transactions, "count": len(transactions), "total": total})


def _transaction_kwargs(params: Dict[str, Any], include_identity: bool = True) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if include_identity and params.get("asset_code") not in (None, ""):
        kwargs["asset_code"] = str(params.get("asset_code")).strip()
    if include_identity and params.get("transaction_type") not in (None, ""):
        kwargs["transaction_type"] = str(params.get("transaction_type")).strip()
    for field in ("quantity", "price", "amount", "commission", "tax", "original_amount", "settlement_amount", "settlement_rate"):
        if field in params and params.get(field) not in (None, ""):
            kwargs[field] = float(_decimal_param(params, field) or 0)
    dt = _parse_datetime(params.get("transaction_date"))
    if dt is not None:
        kwargs["transaction_date"] = dt
    for field in ("reason", "notes", "status", "price_currency", "commission_currency", "original_currency", "settlement_currency"):
        if field in params and params.get(field) not in (None, ""):
            kwargs[field] = str(params.get(field)).strip()
    return kwargs


def _exec_create_transaction(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_code = str(params.get("asset_code") or "").strip()
    transaction_type = str(params.get("transaction_type") or "").strip()
    if not asset_code or not transaction_type:
        raise ValueError("asset_code 和 transaction_type 不能为空")
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        _ensure_asset_type_exists(db, user_id, asset_code)
        from app.services.transaction_service import TransactionService  # type: ignore
        transaction = TransactionService(db).create_transaction(
            portfolio_id=portfolio.id,
            asset_code=asset_code,
            transaction_type=transaction_type,
            **{key: value for key, value in _transaction_kwargs(params, include_identity=False).items() if key != "portfolio_id"},
        )
        db.commit()
        _recalculate_after_asset_change(db, user_id, portfolio.id, asset_code)
        names = _asset_name_map(db, user_id, [asset_code])
        return _json_result({"success": True, "message": "交易记录已创建并已重算组合", "transaction": _transaction_dict(transaction, names.get(asset_code))})


def _exec_update_transaction(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    transaction_id = _required_int(params, "transaction_id")
    with _rich_db_session() as db:
        from app.core.database.models.transaction import Transaction  # type: ignore
        row = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not row:
            raise ValueError("交易记录不存在")
        portfolio = _resolve_portfolio(db, user_id, row.portfolio_id)
        old_asset_code = str(row.asset_code or "")
        if params.get("asset_code") not in (None, ""):
            _ensure_asset_type_exists(db, user_id, str(params.get("asset_code")).strip())
        updates = _transaction_kwargs(params)
        updates.pop("portfolio_id", None)
        for key, value in updates.items():
            setattr(row, key, value)
        if row.amount is None and row.quantity is not None and row.price is not None:
            row.amount = Decimal(str(row.quantity)) * Decimal(str(row.price))
        db.commit()
        db.refresh(row)
        _recalculate_after_asset_change(db, user_id, portfolio.id, old_asset_code)
        if row.asset_code and str(row.asset_code) != old_asset_code:
            _recalculate_after_asset_change(db, user_id, portfolio.id, str(row.asset_code))
        names = _asset_name_map(db, user_id, [str(row.asset_code)])
        return _json_result({"success": True, "message": "交易记录已更新并已重算组合", "transaction": _transaction_dict(row, names.get(str(row.asset_code)))})


def _exec_delete_transaction(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    transaction_id = _required_int(params, "transaction_id")
    with _rich_db_session() as db:
        from app.core.database.models.transaction import Transaction  # type: ignore
        row = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not row:
            raise ValueError("交易记录不存在")
        portfolio = _resolve_portfolio(db, user_id, row.portfolio_id)
        asset_code = str(row.asset_code or "")
        db.delete(row)
        db.commit()
        _recalculate_after_asset_change(db, user_id, portfolio.id, asset_code)
        return _json_result({"success": True, "message": "交易记录已删除并已重算组合", "transaction_id": transaction_id})


def _exec_delete_transactions(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    raw_ids = params.get("transaction_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) == 0:
        raise ValueError("transaction_ids 必须是非空数组")
    ids: List[int] = []
    for item in raw_ids:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            raise ValueError(f"transaction_ids 包含无效的整数: {item}")
    with _rich_db_session() as db:
        from app.core.database.models.transaction import Transaction  # type: ignore
        rows = db.query(Transaction).filter(Transaction.id.in_(ids)).all()
        found_ids = {row.id for row in rows}
        missing = [i for i in ids if i not in found_ids]
        if missing:
            raise ValueError(f"以下交易记录不存在: {missing}")
        portfolio_ids = {row.portfolio_id for row in rows}
        for pid in portfolio_ids:
            _resolve_portfolio(db, user_id, pid)
        asset_codes: Dict[int, str] = {}
        for row in rows:
            asset_codes[row.portfolio_id] = str(row.asset_code or "")
            db.delete(row)
        db.commit()
        for pid, code in asset_codes.items():
            _recalculate_after_asset_change(db, user_id, pid, code)
        return _json_result({"success": True, "message": f"已批量删除 {len(ids)} 条交易记录", "deleted_ids": ids, "count": len(ids)})


def _exec_update_transaction_status(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    status = str(params.get("status") or "").strip()
    if status not in {"pending", "completed"}:
        raise ValueError("status 必须是 pending 或 completed")
    return _exec_update_transaction({"transaction_id": _required_int(params, "transaction_id"), "status": status}, config)


def _exec_transaction_statistics(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_code = str(params.get("asset_code") or "").strip()
    with _rich_db_session() as db:
        from sqlalchemy import func  # type: ignore
        from app.core.database.models.transaction import Transaction  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        query = db.query(Transaction.transaction_type, func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.portfolio_id == portfolio.id)
        if asset_code:
            query = query.filter(Transaction.asset_code == asset_code)
        rows = query.group_by(Transaction.transaction_type).all()
        stats = {str(row[0] or "unknown"): {"count": int(row[1] or 0), "amount": row[2] or 0} for row in rows}
        return _json_result({"success": True, "portfolio": _portfolio_context(portfolio), "asset_code": asset_code or None, "statistics": stats})


def _normalize_import_asset_type(item: Dict[str, Any]) -> Dict[str, Any]:
    code = str(item.get("code") or item.get("asset_code") or item.get("symbol") or "").strip()
    if not code:
        raise ValueError("资产类型缺少 code")
    name = str(item.get("name") or item.get("asset_name") or code).strip() or code
    return {
        "code": code,
        "name": name,
        "description": item.get("description") or "",
        "category": item.get("category") or "other",
        "market_type": item.get("market_type") or "field",
        "price_source": item.get("price_source") or "manual",
        "min_unit": int(item.get("min_unit") or 1),
        "price_precision": int(item.get("price_precision") or 2),
        "quantity_precision": int(item.get("quantity_precision") or 4),
        "use_market_data": _bool_param(item, "use_market_data", False),
        "linked_symbol": item.get("linked_symbol") or None,
    }


def _normalize_import_transaction(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(item)
    payload["asset_code"] = str(payload.get("asset_code") or payload.get("code") or payload.get("symbol") or "").strip()
    payload["transaction_type"] = str(payload.get("transaction_type") or payload.get("type") or "buy").strip().lower()
    if not payload["asset_code"]:
        raise ValueError("交易记录缺少 asset_code")
    if payload["transaction_type"] not in {"buy", "sell", "dividend", "bonus", "rights"}:
        raise ValueError(f"交易类型无效: {payload['transaction_type']}")
    if payload.get("quantity") in (None, "") and payload.get("amount") in (None, ""):
        raise ValueError("交易记录至少需要 quantity 或 amount")
    if payload.get("price") in (None, "") and payload.get("amount") in (None, ""):
        payload["price"] = 0
    return payload


def _build_import_plan(db: Any, user_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    from app.core.database.models.portfolio import AssetType  # type: ignore
    from app.core.database.models.transaction import Transaction  # type: ignore

    portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
    raw_asset_types = params.get("asset_types") if isinstance(params.get("asset_types"), list) else []
    raw_transactions = params.get("transactions") if isinstance(params.get("transactions"), list) else []
    auto_create = _bool_param(params, "auto_create_asset_types", True)
    duplicate_check = _bool_param(params, "duplicate_check", True)

    errors: List[Dict[str, Any]] = []
    asset_types: List[Dict[str, Any]] = []
    asset_by_code: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(raw_asset_types, start=1):
        if not isinstance(item, dict):
            errors.append({"kind": "asset_type", "index": index, "error": "资产类型行必须是对象"})
            continue
        try:
            normalized = _normalize_import_asset_type(item)
            asset_by_code[normalized["code"]] = normalized
        except Exception as exc:
            errors.append({"kind": "asset_type", "index": index, "error": str(exc), "row": item})

    transactions: List[Dict[str, Any]] = []
    referenced_codes: set[str] = set()
    for index, item in enumerate(raw_transactions, start=1):
        if not isinstance(item, dict):
            errors.append({"kind": "transaction", "index": index, "error": "交易行必须是对象"})
            continue
        try:
            normalized = _normalize_import_transaction(item)
            referenced_codes.add(normalized["asset_code"])
            transactions.append({"index": index, "data": normalized})
        except Exception as exc:
            errors.append({"kind": "transaction", "index": index, "error": str(exc), "row": item})

    existing_asset_rows = db.query(AssetType).filter(AssetType.user_id == user_id).all()
    existing_assets = {str(row.code): row for row in existing_asset_rows}
    missing_codes = sorted(code for code in referenced_codes if code not in existing_assets and code not in asset_by_code)
    if auto_create:
        for code in missing_codes:
            asset_by_code[code] = {
                "code": code,
                "name": code,
                "description": "由导入交易记录自动补全",
                "category": "other",
                "market_type": "field",
                "price_source": "manual",
                "min_unit": 1,
                "price_precision": 2,
                "quantity_precision": 4,
                "use_market_data": False,
                "linked_symbol": None,
            }
    else:
        for code in missing_codes:
            errors.append({"kind": "transaction", "asset_code": code, "error": "交易引用的资产类型不存在"})

    for code, item in asset_by_code.items():
        asset_types.append({
            **item,
            "action": "exists" if code in existing_assets else "create",
            "existing_id": getattr(existing_assets.get(code), "id", None),
        })

    duplicates: List[Dict[str, Any]] = []
    valid_transactions: List[Dict[str, Any]] = []
    for entry in transactions:
        data = entry["data"]
        code = str(data.get("asset_code") or "")
        if code not in existing_assets and code not in asset_by_code:
            errors.append({"kind": "transaction", "index": entry["index"], "asset_code": code, "error": "资产类型不存在且未计划创建"})
            continue
        duplicate_ids: List[int] = []
        tx_date = _parse_datetime(data.get("transaction_date"))
        if duplicate_check and tx_date is not None:
            query = db.query(Transaction).filter(
                Transaction.portfolio_id == portfolio.id,
                Transaction.asset_code == code,
                Transaction.transaction_type == str(data.get("transaction_type") or ""),
                Transaction.transaction_date == tx_date,
            )
            if data.get("quantity") not in (None, ""):
                query = query.filter(Transaction.quantity == _decimal_param(data, "quantity"))
            if data.get("price") not in (None, ""):
                query = query.filter(Transaction.price == _decimal_param(data, "price"))
            duplicate_ids = [int(row.id) for row in query.limit(5).all()]
            if duplicate_ids:
                duplicates.append({"index": entry["index"], "asset_code": code, "existing_transaction_ids": duplicate_ids})
        valid_transactions.append({"index": entry["index"], "data": data, "duplicate_transaction_ids": duplicate_ids})

    create_asset_count = len([item for item in asset_types if item["action"] == "create"])
    return {
        "success": True,
        "source_name": params.get("source_name") or None,
        "portfolio": _portfolio_context(portfolio),
        "asset_types": asset_types,
        "transactions": valid_transactions,
        "summary": {
            "asset_types_total": len(asset_types),
            "asset_types_to_create": create_asset_count,
            "asset_types_existing": len(asset_types) - create_asset_count,
            "transactions_valid": len(valid_transactions),
            "errors": len(errors),
            "possible_duplicates": len(duplicates),
        },
        "errors": errors,
        "possible_duplicates": duplicates,
        "can_execute": len(valid_transactions) > 0 and not errors,
        "execution_note": "执行时会先创建缺失资产类型，再批量创建交易记录，最后重算组合。",
    }


def _exec_preview_business_import(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        return _json_result(_build_import_plan(db, user_id, params))


def _exec_execute_business_import(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.asset_service import AssetService  # type: ignore
        from app.services.transaction_service import TransactionService  # type: ignore

        plan = _build_import_plan(db, user_id, params)
        if plan["errors"]:
            return _json_result({**plan, "success": False, "message": "导入计划存在错误，未执行写入"})
        portfolio_id = int(plan["portfolio"]["portfolio_id"])
        created_assets: List[Dict[str, Any]] = []
        existing_assets: List[Dict[str, Any]] = []
        for item in plan["asset_types"]:
            if item["action"] == "create":
                row = AssetService(db).create_asset_type(
                    user_id=user_id,
                    code=item["code"],
                    name=item["name"],
                    description=item.get("description"),
                    category=item.get("category") or "other",
                    market_type=item.get("market_type") or "field",
                    min_unit=int(item.get("min_unit") or 1),
                    price_source=item.get("price_source") or "manual",
                    price_precision=int(item.get("price_precision") or 2),
                    quantity_precision=int(item.get("quantity_precision") or 4),
                    use_market_data=bool(item.get("use_market_data")),
                    linked_symbol=item.get("linked_symbol"),
                )
                created_assets.append(_asset_type_dict(row))
            else:
                existing_assets.append({"code": item["code"], "id": item.get("existing_id")})

        imported_transactions: List[Dict[str, Any]] = []
        failed_transactions: List[Dict[str, Any]] = []
        affected_codes: set[str] = set()
        service = TransactionService(db)
        for entry in plan["transactions"]:
            data = entry["data"]
            try:
                tx = service.create_transaction(
                    portfolio_id=portfolio_id,
                    asset_code=str(data.get("asset_code") or ""),
                    transaction_type=str(data.get("transaction_type") or "buy"),
                    **{key: value for key, value in _transaction_kwargs(data, include_identity=False).items() if key != "portfolio_id"},
                )
                affected_codes.add(str(data.get("asset_code") or ""))
                imported_transactions.append({"source_index": entry["index"], "transaction": _transaction_dict(tx)})
            except Exception as exc:
                failed_transactions.append({"source_index": entry["index"], "asset_code": data.get("asset_code"), "error": str(exc)})
        for code in sorted(code for code in affected_codes if code):
            _recalculate_after_asset_change(db, user_id, portfolio_id, code)
        return _json_result({
            "success": len(failed_transactions) == 0,
            "message": f"导入完成：创建资产类型 {len(created_assets)} 个，导入交易 {len(imported_transactions)} 条，失败 {len(failed_transactions)} 条。",
            "portfolio": plan["portfolio"],
            "created_asset_types": created_assets,
            "existing_asset_types": existing_assets,
            "imported_transactions": imported_transactions,
            "failed_transactions": failed_transactions,
            "possible_duplicates": plan["possible_duplicates"],
        })


def _rebalance_items(positions: List[Dict[str, Any]], threshold: Decimal) -> List[Dict[str, Any]]:
    items = []
    for item in positions:
        target = Decimal(str(item.get("target_weight") or 0))
        current = Decimal(str(item.get("current_weight") or 0))
        if target > 1:
            target = target / Decimal("100")
        if current > 1:
            current = current / Decimal("100")
        deviation = current - target
        abs_deviation = abs(deviation)
        action = "hold"
        if abs_deviation >= threshold:
            action = "reduce" if deviation > 0 else "increase"
        items.append({
            "asset_code": item.get("asset_code"),
            "asset_name": item.get("asset_name"),
            "current_value": item.get("current_value"),
            "current_weight": current,
            "target_weight": target,
            "deviation": deviation,
            "abs_deviation": abs_deviation,
            "suggested_action": action,
        })
    return sorted(items, key=lambda row: row["abs_deviation"], reverse=True)


def _exec_rebalance_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    threshold = _decimal_param(params, "threshold", Decimal("0.02")) or Decimal("0.02")
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        positions = _position_rows(db, user_id, portfolio.id, 200)
        items = _rebalance_items(positions, threshold)
        actionable = [item for item in items if item["suggested_action"] != "hold"]
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "portfolio": _portfolio_context(portfolio),
            "threshold": threshold,
            "needs_rebalance": bool(actionable),
            "items": items,
            "actionable_count": len(actionable),
        })


def _exec_portfolio_risk(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        positions = _position_rows(db, user_id, portfolio.id, 200)
        items = _rebalance_items(positions, Decimal("0.02"))
        current_weights = [abs(Decimal(str(item["current_weight"] or 0))) for item in items]
        max_weight = max(current_weights) if current_weights else Decimal(0)
        top_weight_sum = sum(current_weights[:5]) if current_weights else Decimal(0)
        avg_deviation = sum((item["abs_deviation"] for item in items), Decimal(0)) / Decimal(len(items) or 1)
        balance_score = max(Decimal(0), Decimal(100) - avg_deviation * Decimal(100))
        risk_level = "low"
        if max_weight > Decimal("0.5") or balance_score < 60:
            risk_level = "high"
        elif max_weight > Decimal("0.3") or balance_score < 80:
            risk_level = "medium"
        return _json_result({
            "success": True,
            "portfolio": _portfolio_context(portfolio),
            "risk_level": risk_level,
            "balance_score": balance_score,
            "max_single_asset_weight": max_weight,
            "top5_weight_sum": top_weight_sum,
            "largest_deviations": items[:10],
            "position_count": len(items),
        })


def _exec_portfolio_performance(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    display_currency = str(params.get("display_currency") or "CNY").upper()
    tx_limit = max(1, min(_optional_int(params, "transaction_limit") or 10, 50))
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.services.currency_service import CurrencyService  # type: ignore

        summary = CurrencyService(db).get_portfolio_summary_with_currency(portfolio.id, display_currency)
        transactions_raw = json.loads(_exec_recent_transactions({"portfolio_id": portfolio.id, "limit": tx_limit}, config))
        return _json_result({
            "success": True,
            "portfolio": _portfolio_context(portfolio),
            "display_currency": display_currency,
            "summary": summary,
            "recent_transactions": transactions_raw.get("transactions", []),
        })


def _exec_update_portfolio_weights(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    weights = params.get("target_weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError("target_weights 不能为空")
    normalized = {str(code).strip(): _normalize_weight(weight) for code, weight in weights.items() if str(code).strip()}
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.core.database.models.portfolio import PortfolioAsset  # type: ignore
        from app.services.portfolio_service import PortfolioService  # type: ignore

        for asset_code, weight in normalized.items():
            portfolio_asset = db.query(PortfolioAsset).filter(
                PortfolioAsset.portfolio_id == portfolio.id,
                PortfolioAsset.asset_type_code == asset_code,
            ).first()
            if portfolio_asset:
                portfolio_asset.target_weight = weight
                current_weight = Decimal(str(portfolio_asset.current_weight or 0))
                portfolio_asset.deviation = current_weight - weight
            else:
                db.add(PortfolioAsset(
                    portfolio_id=portfolio.id,
                    asset_type_code=asset_code,
                    target_weight=weight,
                    current_weight=Decimal("0"),
                    current_quantity=Decimal("0"),
                    current_price=Decimal("0"),
                    current_value=Decimal("0"),
                    deviation=-weight,
                ))
        portfolio.updated_at = datetime.now().replace(tzinfo=None)
        db.commit()
        detail = PortfolioService(db).get_portfolio(user_id, portfolio.id)
        return _json_result({"success": True, "portfolio": _portfolio_context(portfolio), "updated_weights": normalized, "data": detail})


def _exec_recalculate_portfolio(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    adjust_type = str(params.get("adjust_type") or "")
    rebalancing_type = str(params.get("rebalancing_type") or "forced")
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from db_helpers_orm import recalculate_all_portfolio_assets_orm  # type: ignore
        from app.services.portfolio_service import PortfolioService  # type: ignore

        recalculate_all_portfolio_assets_orm(db, portfolio.id, user_id, adjust_type)
        summary = PortfolioService(db).get_dashboard_summary(user_id, portfolio.id, False, adjust_type)
        return _json_result({
            "success": True,
            "message": "投资组合重算完成",
            "portfolio": _portfolio_context(portfolio),
            "rebalancing_type": rebalancing_type,
            "adjust_type": adjust_type,
            "dashboard_summary": summary,
        })


def _exec_dca_plans(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    portfolio_id = _optional_int(params, "portfolio_id")
    enabled_only = bool(params.get("enabled_only") or False)
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        plans = DCAPlanService(db).get_plans(user_id, portfolio_id)
        if enabled_only:
            plans = [plan for plan in plans if bool(plan.get("enabled"))]
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "portfolio_id": portfolio_id,
            "plans": plans,
            "count": len(plans),
        })


def _exec_dca_plan_detail(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        detail = DCAPlanService(db).get_plan_detail(_required_int(params, "plan_id"), user_id)
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "plan": detail})


def _exec_dca_allocation(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    with _rich_db_session() as db:
        from app.services.allocation_calculator import AllocationCalculator  # type: ignore
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        plan = DCAPlanService(db).get_plan(plan_id, user_id)
        results = AllocationCalculator(db).calculate(plan)
        return _json_result({
            "success": True,
            "user_scope": {"user_id": user_id},
            "plan_id": plan_id,
            "allocations": [_allocation_result_dict(result) for result in results],
            "count": len(results),
        })


def _exec_pending_dca(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        today = date.today().isoformat()
        plans = DCAPlanService(db).get_plans(user_id)
        pending = [plan for plan in plans if bool(plan.get("enabled")) and plan.get("next_execution_date") and plan["next_execution_date"] <= today]
        return _json_result({"success": True, "user_scope": {"user_id": user_id}, "plans": pending, "count": len(pending)})


def _exec_dca_history(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore
        from app.services.execution_recorder import ExecutionRecorder  # type: ignore

        DCAPlanService(db).get_plan(plan_id, user_id)
        rows = ExecutionRecorder(db).get_execution_history(plan_id, _parse_date(params.get("start_date")), _parse_date(params.get("end_date")))
        return _json_result({"success": True, "plan_id": plan_id, "executions": [_execution_dict(row) for row in rows], "count": len(rows)})


def _exec_dca_statistics(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore
        from app.services.execution_recorder import ExecutionRecorder  # type: ignore

        DCAPlanService(db).get_plan(plan_id, user_id)
        stats = ExecutionRecorder(db).get_statistics(plan_id)
        return _json_result({"success": True, "plan_id": plan_id, "statistics": stats})


def _exec_create_dca_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    name = str(params.get("name") or "").strip()
    amount = _decimal_param(params, "amount")
    frequency = str(params.get("frequency") or "monthly").strip()
    if not name or amount is None:
        raise ValueError("name 和 amount 不能为空")
    with _rich_db_session() as db:
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        plan = DCAPlanService(db).create_plan(
            user_id=user_id,
            portfolio_id=portfolio.id,
            name=name,
            description=params.get("description"),
            amount=amount,
            frequency=frequency,
            allocation_strategy=str(params.get("allocation_strategy") or "target_weight"),
            high_price_strategy=str(params.get("high_price_strategy") or "redistribute"),
            dca_group_id=_optional_int(params, "dca_group_id"),
            members=_normalize_members(params.get("members")),
            start_date=_parse_date(params.get("start_date")),
            execution_day=_optional_int(params, "execution_day"),
        )
        detail = DCAPlanService(db).get_plan_detail(plan.id, user_id)
        return _json_result({"success": True, "message": "定投计划已创建", "plan": detail})


def _exec_update_dca_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    allowed = {
        "name",
        "description",
        "frequency",
        "allocation_strategy",
        "high_price_strategy",
        "dca_group_id",
        "execution_day",
    }
    kwargs: Dict[str, Any] = {key: params[key] for key in allowed if key in params and params[key] is not None}
    amount = _decimal_param(params, "amount")
    if amount is not None:
        kwargs["amount"] = amount
    start_date = _parse_date(params.get("start_date"))
    if start_date is not None:
        kwargs["start_date"] = start_date
    members = _normalize_members(params.get("members"))
    if members is not None:
        kwargs["members"] = members
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        service = DCAPlanService(db)
        service.update_plan(plan_id, user_id, **kwargs)
        detail = service.get_plan_detail(plan_id, user_id)
        return _json_result({"success": True, "message": "定投计划已更新", "plan": detail})


def _exec_toggle_dca_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    with _rich_db_session() as db:
        from app.services.dca_plan_service import DCAPlanService  # type: ignore

        service = DCAPlanService(db)
        service.toggle_plan(plan_id, user_id, _bool_param(params, "enabled"))
        detail = service.get_plan_detail(plan_id, user_id)
        return _json_result({"success": True, "message": "定投计划状态已更新", "plan": detail})


def _exec_execute_dca_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    actual_allocations = params.get("actual_allocations") if isinstance(params.get("actual_allocations"), list) else None
    status = str(params.get("status") or "pending_confirmation")
    with _rich_db_session() as db:
        from app.services.allocation_calculator import AllocationCalculator  # type: ignore
        from app.services.dca_plan_service import DCAPlanService  # type: ignore
        from app.services.execution_recorder import ExecutionRecorder  # type: ignore

        plan = DCAPlanService(db).get_plan(plan_id, user_id)
        allocations = AllocationCalculator(db).calculate(plan)
        execution = ExecutionRecorder(db).record_execution(
            plan_id=plan_id,
            execution_date=_parse_date(params.get("execution_date")) or date.today(),
            planned_allocations=allocations,
            actual_allocations=actual_allocations,
            status=status,
            skip_reason=params.get("skip_reason"),
            create_transactions=_bool_param(params, "create_transactions"),
            portfolio_id=plan.portfolio_id,
        )
        return _json_result({"success": True, "message": "定投执行记录已生成", "execution": _execution_dict(execution)})


def _exec_run_due_dca(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.core.database.models.dca_plan import DCAPlan  # type: ignore
        from app.services.allocation_calculator import AllocationCalculator  # type: ignore
        from app.services.dca_plan_service import DCAPlanService  # type: ignore
        from app.services.execution_recorder import ExecutionRecorder  # type: ignore

        service = DCAPlanService(db)
        recorder = ExecutionRecorder(db)
        calculator = AllocationCalculator(db)
        today = date.today()
        plans = db.query(DCAPlan).filter(DCAPlan.user_id == user_id).all()
        results = []
        for plan in plans:
            if not bool(getattr(plan, "enabled", False)):
                continue
            if not plan.next_execution_date or plan.next_execution_date > today:
                continue
            allocations = calculator.calculate(plan)
            execution = recorder.record_execution(
                plan_id=plan.id,
                execution_date=today,
                planned_allocations=allocations,
                actual_allocations=None,
                status="pending_confirmation",
                create_transactions=False,
                portfolio_id=plan.portfolio_id,
            )
            plan.next_execution_date = service._calculate_next_execution(plan)
            db.commit()
            results.append({"plan_id": plan.id, "plan_name": plan.name, "execution_id": execution.id, "status": execution.status})
        return _json_result({"success": True, "message": f"已检查 {len(plans)} 个计划，生成 {len(results)} 条待确认执行记录", "results": results})


def _exec_delete_dca_plan(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    plan_id = _required_int(params, "plan_id")
    with _rich_db_session() as db:
        from app.core.database.models.dca_plan import DCAPlan  # type: ignore
        row = db.query(DCAPlan).filter(DCAPlan.id == plan_id, DCAPlan.user_id == user_id).first()
        if not row:
            raise ValueError("定投计划不存在")
        db.delete(row)
        db.commit()
        return _json_result({"success": True, "message": "定投计划已删除", "plan_id": plan_id})


def _exec_asset_groups(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        rows = AssetGroupService(db).get_groups_by_portfolio(portfolio.id, _optional_int(params, "parent_group_id"))
        return _json_result({"success": True, "portfolio": _portfolio_context(portfolio), "groups": [_asset_group_dict(row, include_members=True) for row in rows], "count": len(rows)})


def _exec_asset_group_detail(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        row = AssetGroupService(db).get_group(_required_int(params, "group_id"))
        return _json_result({"success": True, "group": _asset_group_dict(row, include_members=True)})


def _exec_create_asset_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    name = str(params.get("name") or "").strip()
    if not name:
        raise ValueError("name 不能为空")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        row = AssetGroupService(db).create_group(
            portfolio_id=portfolio.id,
            name=name,
            description=params.get("description"),
            target_weight=float(_normalize_weight(params.get("target_weight", 0))),
            parent_group_id=_optional_int(params, "parent_group_id"),
            display_order=_optional_int(params, "display_order") or 0,
            group_type=str(params.get("group_type") or "weighted"),
        )
        return _json_result({"success": True, "message": "资产分组已创建", "group": _asset_group_dict(row, include_members=True)})


def _exec_update_asset_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    kwargs: Dict[str, Any] = {}
    for key in ("name", "description", "group_type"):
        if key in params and params[key] is not None:
            kwargs[key] = params[key]
    for key in ("display_order",):
        if key in params:
            kwargs[key] = _optional_int(params, key)
    if "target_weight" in params and params.get("target_weight") is not None:
        kwargs["target_weight"] = float(_normalize_weight(params.get("target_weight")))
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        row = AssetGroupService(db).update_group(group_id, **kwargs)
        return _json_result({"success": True, "message": "资产分组已更新", "group": _asset_group_dict(row, include_members=True)})


def _exec_delete_asset_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        AssetGroupService(db).delete_group(group_id)
        return _json_result({"success": True, "message": "资产分组已删除", "group_id": group_id})


def _exec_add_asset_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    member_type = str(params.get("member_type") or "asset_type")
    if member_type == "asset_type" and not str(params.get("asset_type_code") or "").strip():
        raise ValueError("member_type=asset_type 时 asset_type_code 不能为空")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        if member_type == "asset_type":
            _ensure_asset_type_exists(db, user_id, str(params.get("asset_type_code") or "").strip())
        row = AssetGroupService(db).add_member(
            group_id=group_id,
            member_type=member_type,
            asset_type_code=str(params.get("asset_type_code") or "").strip() or None,
            asset_group_id=_optional_int(params, "asset_group_id"),
            target_weight=float(_normalize_weight(params.get("target_weight", 0))),
            display_order=_optional_int(params, "display_order") or 0,
        )
        return _json_result({"success": True, "message": "资产分组成员已添加", "member": _asset_group_member_dict(row)})


def _exec_update_asset_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    member_id = _required_int(params, "member_id")
    with _rich_db_session() as db:
        from app.core.database.models.portfolio import AssetGroupMember  # type: ignore
        row = db.query(AssetGroupMember).filter(AssetGroupMember.id == member_id).first()
        if not row:
            raise ValueError("资产分组成员不存在")
        if "target_weight" in params and params.get("target_weight") is not None:
            row.target_weight = _normalize_weight(params.get("target_weight"))
        if "display_order" in params and params.get("display_order") is not None:
            row.display_order = _optional_int(params, "display_order") or 0
        db.commit()
        db.refresh(row)
        return _json_result({"success": True, "message": "资产分组成员已更新", "member": _asset_group_member_dict(row)})


def _exec_remove_asset_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    member_id = _required_int(params, "member_id")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        AssetGroupService(db).remove_member(member_id)
        return _json_result({"success": True, "message": "资产分组成员已移除", "member_id": member_id})


def _exec_validate_asset_group_weights(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        valid = AssetGroupService(db).validate_group_weights(group_id)
        return _json_result({"success": True, "group_id": group_id, "valid": valid})


def _exec_group_value(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    with _rich_db_session() as db:
        from app.services.asset_group_service import AssetGroupService  # type: ignore
        portfolio = _resolve_portfolio(db, user_id, _optional_int(params, "portfolio_id"))
        value = AssetGroupService(db).calculate_group_value(group_id, portfolio.id)
        return _json_result({"success": True, "portfolio": _portfolio_context(portfolio), "group_id": group_id, "value": value})


def _exec_dca_groups(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        rows = DCAGroupService(db).get_groups(user_id)
        return _json_result({"success": True, "groups": [_dca_group_dict(row, include_members=True) for row in rows], "count": len(rows)})


def _exec_dca_group_detail(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        row = DCAGroupService(db).get_group_with_members(_required_int(params, "group_id"), user_id)
        return _json_result({"success": True, "group": _dca_group_dict(row, include_members=True)})


def _exec_create_dca_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        row = DCAGroupService(db).create_group(user_id, str(params.get("name") or "").strip(), params.get("description"), _optional_int(params, "display_order") or 0)
        return _json_result({"success": True, "message": "定投分组已创建", "group": _dca_group_dict(row, include_members=True)})


def _exec_update_dca_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    kwargs = {key: params[key] for key in ("name", "description") if key in params and params[key] is not None}
    if "display_order" in params:
        kwargs["display_order"] = _optional_int(params, "display_order")
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        row = DCAGroupService(db).update_group(_required_int(params, "group_id"), user_id, **kwargs)
        return _json_result({"success": True, "message": "定投分组已更新", "group": _dca_group_dict(row, include_members=True)})


def _exec_delete_dca_group(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        DCAGroupService(db).delete_group(group_id, user_id)
        return _json_result({"success": True, "message": "定投分组已删除", "group_id": group_id})


def _exec_set_dca_group_members(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    members = _normalize_members(params.get("members")) or []
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        members = DCAGroupService(db).set_members(_required_int(params, "group_id"), user_id, members)
        return _json_result({"success": True, "message": "定投分组成员已替换", "members": [_dca_group_member_dict(member) for member in members], "count": len(members)})


def _exec_add_dca_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    asset_code = str(params.get("asset_type_code") or "").strip()
    with _rich_db_session() as db:
        _ensure_asset_type_exists(db, user_id, asset_code)
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        row = DCAGroupService(db).add_member(_required_int(params, "group_id"), user_id, asset_code, params.get("asset_name"), float(_normalize_weight(params.get("target_weight", 0))), _optional_int(params, "display_order") or 0)
        return _json_result({"success": True, "message": "定投分组成员已添加", "member": _dca_group_member_dict(row)})


def _exec_update_dca_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    kwargs = {"asset_name": params.get("asset_name")} if "asset_name" in params else {}
    if "target_weight" in params and params.get("target_weight") is not None:
        kwargs["target_weight"] = float(_normalize_weight(params.get("target_weight")))
    if "display_order" in params:
        kwargs["display_order"] = _optional_int(params, "display_order")
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        row = DCAGroupService(db).update_member(_required_int(params, "member_id"), user_id, **kwargs)
        return _json_result({"success": True, "message": "定投分组成员已更新", "member": _dca_group_member_dict(row)})


def _exec_remove_dca_group_member(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    user_id = _rich_user_id(config)
    member_id = _required_int(params, "member_id")
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        DCAGroupService(db).remove_member(member_id, user_id)
        return _json_result({"success": True, "message": "定投分组成员已移除", "member_id": member_id})


def _exec_validate_dca_group_weights(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    _rich_user_id(config)
    group_id = _required_int(params, "group_id")
    with _rich_db_session() as db:
        from app.services.dca_group_service import DCAGroupService  # type: ignore
        result = DCAGroupService(db).validate_weights(group_id)
        return _json_result({"success": True, "group_id": group_id, "validation": result})


def _exec_search_market_symbols(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query 不能为空")
    with _rich_db_session() as db:
        from app.services.udf_service import search_symbols  # type: ignore
        results = search_symbols(db, query, _limit(params, 20, 100))
    return _json_result({"success": True, "query": query, "symbols": results, "count": len(results)})


def _exec_list_market_symbols(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    with _rich_db_session() as db:
        from app.plugins.quant.database.models.symbol_config import SymbolConfig  # type: ignore
        query_text = str(params.get("query") or "").strip()
        symbol_type = str(params.get("symbol_type") or "").strip()
        query = db.query(SymbolConfig)
        if query_text:
            query = query.filter((SymbolConfig.symbol.ilike(f"%{query_text}%")) | (SymbolConfig.symbol_name.ilike(f"%{query_text}%")))
        if symbol_type:
            query = query.filter(SymbolConfig.symbol_type == symbol_type)
        rows = query.order_by(SymbolConfig.symbol.asc()).limit(_limit(params, 50, 300)).all()
        symbols = [_row_dict(row, ["id", "symbol", "symbol_name", "symbol_type", "board_type", "is_active", "last_update_time", "last_update_status", "notes"]) for row in rows]
        return _json_result({"success": True, "symbols": symbols, "count": len(symbols)})


def _exec_kline_history(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    with _rich_db_session() as db:
        rows = _historical_query(db, params).limit(_limit(params, 120, 500)).all()
        data = [_kline_dict(row) for row in reversed(rows)]
        return _json_result({"success": True, "symbol": params.get("symbol"), "interval": _kline_interval(params.get("interval")), "data": data, "count": len(data)})


def _moving_average(values: List[Decimal], window: int) -> Optional[Decimal]:
    if len(values) < window:
        return None
    return sum(values[-window:], Decimal("0")) / Decimal(window)


def _exec_analyze_kline(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    with _rich_db_session() as db:
        rows = list(reversed(_historical_query(db, params).limit(_limit(params, 120, 500)).all()))
        if not rows:
            return _json_result({"success": True, "symbol": params.get("symbol"), "message": "没有找到 K 线数据", "analysis": None})
        closes = [Decimal(str(row.close_price)) for row in rows if row.close_price is not None]
        volumes = [Decimal(str(row.volume or 0)) for row in rows]
        first_close = closes[0]
        last_close = closes[-1]
        change = last_close - first_close
        change_pct = (change / first_close * Decimal("100")) if first_close else Decimal("0")
        high = max(Decimal(str(row.high_price)) for row in rows if row.high_price is not None)
        low = min(Decimal(str(row.low_price)) for row in rows if row.low_price is not None)
        max_drawdown = Decimal("0")
        peak = closes[0]
        for close in closes:
            if close > peak:
                peak = close
            if peak:
                max_drawdown = min(max_drawdown, (close - peak) / peak * Decimal("100"))
        avg_volume = sum(volumes, Decimal("0")) / Decimal(len(volumes) or 1)
        latest = rows[-1]
        analysis = {
            "bars": len(rows),
            "start_date": rows[0].date,
            "end_date": rows[-1].date,
            "first_close": first_close,
            "last_close": last_close,
            "change": change,
            "change_pct": change_pct,
            "period_high": high,
            "period_low": low,
            "max_drawdown_pct": max_drawdown,
            "ma5": _moving_average(closes, 5),
            "ma20": _moving_average(closes, 20),
            "ma60": _moving_average(closes, 60),
            "avg_volume": avg_volume,
            "latest_volume": latest.volume,
            "latest_pct_chg": latest.pct_chg,
            "latest_pe_ttm": latest.pe_ttm,
            "latest_pb_mrq": latest.pb_mrq,
            "trend": "up" if _moving_average(closes, 5) and _moving_average(closes, 20) and _moving_average(closes, 5) > _moving_average(closes, 20) else "down_or_sideways",
        }
        return _json_result({"success": True, "symbol": params.get("symbol"), "interval": _kline_interval(params.get("interval")), "analysis": analysis})


def _exec_valuation_data(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    with _rich_db_session() as db:
        rows = _historical_query(db, {**params, "interval": "daily"}).limit(_limit(params, 120, 500)).all()
        data = [{"date": row.date, "pe_ttm": row.pe_ttm, "pb_mrq": row.pb_mrq, "ps_ttm": row.ps_ttm, "pcf_ncf_ttm": row.pcf_ncf_ttm, "total_market_cap": row.total_market_cap, "circulating_market_cap": row.circulating_market_cap} for row in reversed(rows)]
        return _json_result({"success": True, "symbol": params.get("symbol"), "valuation": data, "count": len(data)})


def _exec_query_factors(params: Dict[str, Any], config: Dict[str, Any]) -> str:
    with _rich_db_session() as db:
        rows = _historical_query(db, {**params, "interval": "daily"}).limit(_limit(params, 120, 500)).all()
        data = [{"date": row.date, "turn": row.turn, "pct_chg": row.pct_chg, "tradestatus": row.tradestatus, "is_st": row.is_st, "is_suspended": row.is_suspended, "is_delisted": row.is_delisted} for row in reversed(rows)]
        return _json_result({"success": True, "symbol": params.get("symbol"), "factors": data, "count": len(data)})


# ── Register on import ───────────────────────────────────────────────────────


def _register_rich_tools() -> None:
    for name, schema, func, read_only in (
        ("navigate", _NAVIGATE_SCHEMA, _exec_navigate, True),
        ("open_symbol_chart", _OPEN_SYMBOL_CHART_SCHEMA, _with_business_error(_exec_open_symbol_chart), True),
        ("get_portfolios", _PORTFOLIOS_SCHEMA, _with_business_error(_exec_portfolios), True),
        ("get_portfolio_detail", _PORTFOLIO_DETAIL_SCHEMA, _with_business_error(_exec_portfolio_detail), True),
        ("create_portfolio", _CREATE_PORTFOLIO_SCHEMA, _with_business_error(_exec_create_portfolio), False),
        ("update_portfolio", _UPDATE_PORTFOLIO_SCHEMA, _with_business_error(_exec_update_portfolio), False),
        ("delete_portfolio", _DELETE_PORTFOLIO_SCHEMA, _with_business_error(_exec_delete_portfolio), False),
        ("get_dashboard_summary", _DASHBOARD_SUMMARY_SCHEMA, _with_business_error(_exec_dashboard_summary), True),
        ("get_portfolio_summary", _PORTFOLIO_SUMMARY_SCHEMA, _with_business_error(_exec_portfolio_summary), True),
        ("get_asset_types", _ASSET_TYPES_SCHEMA, _with_business_error(_exec_asset_types), True),
        ("get_asset_type_preset", _ASSET_TYPE_PRESET_SCHEMA, _with_business_error(_exec_asset_type_preset), True),
        ("create_asset_type", _CREATE_ASSET_TYPE_SCHEMA, _with_business_error(_exec_create_asset_type), False),
        ("update_asset_type", _UPDATE_ASSET_TYPE_SCHEMA, _with_business_error(_exec_update_asset_type), False),
        ("delete_asset_type", _DELETE_ASSET_TYPE_SCHEMA, _with_business_error(_exec_delete_asset_type), False),
        ("delete_asset_types", _DELETE_ASSET_TYPES_SCHEMA, _with_business_error(_exec_delete_asset_types), False),
        ("cleanup_orphan_assets", _CLEANUP_ORPHAN_ASSETS_SCHEMA, _with_business_error(_exec_cleanup_orphan_assets), False),
        ("get_asset_positions", _ASSET_POSITIONS_SCHEMA, _with_business_error(_exec_asset_positions), True),
        ("get_asset_allocation", _ASSET_ALLOCATION_SCHEMA, _with_business_error(_exec_asset_allocation), True),
        ("get_portfolio_assets", _PORTFOLIO_ASSETS_SCHEMA, _with_business_error(_exec_portfolio_assets), True),
        ("get_assets_summary", _ASSETS_SUMMARY_SCHEMA, _with_business_error(_exec_assets_summary), True),
        ("add_portfolio_asset", _ADD_PORTFOLIO_ASSET_SCHEMA, _with_business_error(_exec_add_portfolio_asset), False),
        ("update_portfolio_asset", _UPDATE_PORTFOLIO_ASSET_SCHEMA, _with_business_error(_exec_update_portfolio_asset), False),
        ("update_portfolio_asset_price", _UPDATE_PORTFOLIO_ASSET_PRICE_SCHEMA, _with_business_error(_exec_update_portfolio_asset_price), False),
        ("delete_portfolio_asset", _DELETE_PORTFOLIO_ASSET_SCHEMA, _with_business_error(_exec_delete_portfolio_asset), False),
        ("get_recent_transactions", _RECENT_TRANSACTIONS_SCHEMA, _with_business_error(_exec_recent_transactions), True),
        ("get_transactions", _TRANSACTIONS_SCHEMA, _with_business_error(_exec_transactions), True),
        ("create_transaction", _CREATE_TRANSACTION_SCHEMA, _with_business_error(_exec_create_transaction), False),
        ("update_transaction", _UPDATE_TRANSACTION_SCHEMA, _with_business_error(_exec_update_transaction), False),
        ("delete_transaction", _DELETE_TRANSACTION_SCHEMA, _with_business_error(_exec_delete_transaction), False),
        ("delete_transactions", _DELETE_TRANSACTIONS_SCHEMA, _with_business_error(_exec_delete_transactions), False),
        ("update_transaction_status", _UPDATE_TRANSACTION_STATUS_SCHEMA, _with_business_error(_exec_update_transaction_status), False),
        ("get_transaction_statistics", _TRANSACTION_STATISTICS_SCHEMA, _with_business_error(_exec_transaction_statistics), True),
        ("preview_business_import", _PREVIEW_BUSINESS_IMPORT_SCHEMA, _with_business_error(_exec_preview_business_import), True),
        ("execute_business_import", _EXECUTE_BUSINESS_IMPORT_SCHEMA, _with_business_error(_exec_execute_business_import), False),
        ("get_asset_groups", _ASSET_GROUPS_SCHEMA, _with_business_error(_exec_asset_groups), True),
        ("get_asset_group_detail", _ASSET_GROUP_DETAIL_SCHEMA, _with_business_error(_exec_asset_group_detail), True),
        ("create_asset_group", _CREATE_ASSET_GROUP_SCHEMA, _with_business_error(_exec_create_asset_group), False),
        ("update_asset_group", _UPDATE_ASSET_GROUP_SCHEMA, _with_business_error(_exec_update_asset_group), False),
        ("delete_asset_group", _DELETE_ASSET_GROUP_SCHEMA, _with_business_error(_exec_delete_asset_group), False),
        ("add_asset_group_member", _ADD_ASSET_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_add_asset_group_member), False),
        ("update_asset_group_member", _UPDATE_ASSET_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_update_asset_group_member), False),
        ("remove_asset_group_member", _REMOVE_ASSET_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_remove_asset_group_member), False),
        ("validate_asset_group_weights", _VALIDATE_ASSET_GROUP_WEIGHTS_SCHEMA, _with_business_error(_exec_validate_asset_group_weights), True),
        ("get_group_value", _GROUP_VALUE_SCHEMA, _with_business_error(_exec_group_value), True),
        ("analyze_portfolio_risk", _PORTFOLIO_RISK_SCHEMA, _with_business_error(_exec_portfolio_risk), True),
        ("analyze_portfolio_performance", _PORTFOLIO_PERFORMANCE_SCHEMA, _with_business_error(_exec_portfolio_performance), True),
        ("calculate_rebalance_plan", _REBALANCE_PLAN_SCHEMA, _with_business_error(_exec_rebalance_plan), True),
        ("execute_rebalance", _EXECUTE_REBALANCE_SCHEMA, _with_business_error(_exec_recalculate_portfolio), False),
        ("force_recalculate_portfolio", _FORCE_RECALCULATE_SCHEMA, _with_business_error(_exec_recalculate_portfolio), False),
        ("update_portfolio_weights", _UPDATE_WEIGHTS_SCHEMA, _with_business_error(_exec_update_portfolio_weights), False),
        ("get_dca_plans", _DCA_PLANS_SCHEMA, _with_business_error(_exec_dca_plans), True),
        ("get_dca_plan_detail", _DCA_PLAN_DETAIL_SCHEMA, _with_business_error(_exec_dca_plan_detail), True),
        ("delete_dca_plan", _DELETE_DCA_PLAN_SCHEMA, _with_business_error(_exec_delete_dca_plan), False),
        ("preview_dca_allocation", _DCA_ALLOCATION_SCHEMA, _with_business_error(_exec_dca_allocation), True),
        ("get_pending_dca_plans", _PENDING_DCA_SCHEMA, _with_business_error(_exec_pending_dca), True),
        ("get_dca_execution_history", _DCA_HISTORY_SCHEMA, _with_business_error(_exec_dca_history), True),
        ("get_dca_statistics", _DCA_STATISTICS_SCHEMA, _with_business_error(_exec_dca_statistics), True),
        ("get_dca_groups", _DCA_GROUPS_SCHEMA, _with_business_error(_exec_dca_groups), True),
        ("get_dca_group_detail", _DCA_GROUP_DETAIL_SCHEMA, _with_business_error(_exec_dca_group_detail), True),
        ("create_dca_group", _CREATE_DCA_GROUP_SCHEMA, _with_business_error(_exec_create_dca_group), False),
        ("update_dca_group", _UPDATE_DCA_GROUP_SCHEMA, _with_business_error(_exec_update_dca_group), False),
        ("delete_dca_group", _DELETE_DCA_GROUP_SCHEMA, _with_business_error(_exec_delete_dca_group), False),
        ("set_dca_group_members", _SET_DCA_GROUP_MEMBERS_SCHEMA, _with_business_error(_exec_set_dca_group_members), False),
        ("add_dca_group_member", _ADD_DCA_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_add_dca_group_member), False),
        ("update_dca_group_member", _UPDATE_DCA_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_update_dca_group_member), False),
        ("remove_dca_group_member", _REMOVE_DCA_GROUP_MEMBER_SCHEMA, _with_business_error(_exec_remove_dca_group_member), False),
        ("validate_dca_group_weights", _VALIDATE_DCA_GROUP_WEIGHTS_SCHEMA, _with_business_error(_exec_validate_dca_group_weights), True),
        ("create_dca_plan", _CREATE_DCA_SCHEMA, _with_business_error(_exec_create_dca_plan), False),
        ("update_dca_plan", _UPDATE_DCA_SCHEMA, _with_business_error(_exec_update_dca_plan), False),
        ("toggle_dca_plan", _TOGGLE_DCA_SCHEMA, _with_business_error(_exec_toggle_dca_plan), False),
        ("execute_dca_plan", _EXECUTE_DCA_SCHEMA, _with_business_error(_exec_execute_dca_plan), False),
        ("run_due_dca_plans", _RUN_DUE_DCA_SCHEMA, _with_business_error(_exec_run_due_dca), False),
        ("search_market_symbols", _MARKET_SYMBOL_SEARCH_SCHEMA, _with_business_error(_exec_search_market_symbols), True),
        ("list_market_symbols", _MARKET_SYMBOL_LIST_SCHEMA, _with_business_error(_exec_list_market_symbols), True),
        ("get_kline_history", _KLINE_HISTORY_SCHEMA, _with_business_error(_exec_kline_history), True),
        ("analyze_kline", _ANALYZE_KLINE_SCHEMA, _with_business_error(_exec_analyze_kline), True),
        ("query_valuation_data", _VALUATION_DATA_SCHEMA, _with_business_error(_exec_valuation_data), True),
        ("query_factors", _FACTOR_QUERY_SCHEMA, _with_business_error(_exec_query_factors), True),
    ):
        register_tool(ToolDef(
            name=name,
            schema=schema,
            func=func,
            read_only=read_only,
            concurrent_safe=read_only,
        ))


_register_rich_tools()
