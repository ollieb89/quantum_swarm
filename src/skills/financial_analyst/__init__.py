"""
Financial Analyst Skill - Main Handler

Routes requests to appropriate financial analysis tools.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from typing import Dict, Any, Optional
from tools import ratio_calculator, dcf_valuation, budget_analyzer, forecast_builder


class FinancialAnalystSkill:
    """Main handler for financial analyst skill"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.tools = {
            "ratio_calculator": ratio_calculator,
            "dcf_valuation": dcf_valuation,
            "budget_variance_analyzer": budget_analyzer,
            "forecast_builder": forecast_builder
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute financial analysis tool based on payload.

        Expected payload format:
        {
            "tool": "ratio_calculator" | "dcf_valuation" | "budget_variance_analyzer" | "forecast_builder",
            "parameters": {...}
        }

        Returns:
            Dict containing the tool execution results
        """
        tool_name = payload.get("tool")
        parameters = payload.get("parameters", {})

        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Available tools: {list(self.tools.keys())}"
            }

        try:
            tool = self.tools[tool_name]
            result = tool.execute(parameters)
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }

    def get_available_tools(self) -> list:
        """Return list of available tools"""
        return list(self.tools.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]
        return {
            "name": tool_name,
            "description": tool.DESCRIPTION,
            "required_parameters": tool.REQUIRED_PARAMETERS,
            "optional_parameters": tool.OPTIONAL_PARAMETERS
        }


def execute_financial_skill(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone function to execute financial analysis.

    Usage:
        result = execute_financial_skill({
            "tool": "ratio_calculator",
            "parameters": {...}
        })
    """
    skill = FinancialAnalystSkill()
    return skill.execute(payload)
