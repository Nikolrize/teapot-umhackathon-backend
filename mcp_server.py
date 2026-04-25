import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from app.models.schemas import WorkspaceContext, AnalyzeRequest
from app.services.agents import (
    sales_predictor,
    pain_point_analyzer,
    profit_optimiser,
    risk_identifier,
    scenario_simulator,
    resource_optimiser,
    decision_recommendation,
)
from app.services.analysis_service import basic_analysis

mcp = FastMCP("Teapot Business Intelligence")


def _workspace(name: str, business_type: str, expected_costs: float, brief_description: str, mode_of_business: str | None = None) -> WorkspaceContext:
    return WorkspaceContext(
        name=name,
        business_type=business_type,
        expected_costs=expected_costs,
        mode_of_business=mode_of_business,
        brief_description=brief_description,
    )


@mcp.tool()
def predict_sales(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Predict future sales trends and revenue opportunities for a business."""
    return sales_predictor.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def analyze_pain_points(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Identify the key pain points and operational challenges facing a business."""
    return pain_point_analyzer.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def optimize_profit(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Suggest ways to improve profit margins and reduce unnecessary costs."""
    return profit_optimiser.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def identify_risks(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Identify business risks and potential threats the business should prepare for."""
    return risk_identifier.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def simulate_scenarios(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Simulate best-case, worst-case, and most likely business scenarios."""
    return scenario_simulator.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def optimize_resources(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Suggest how to optimally allocate resources (staff, budget, time) for the business."""
    return resource_optimiser.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def get_decision_recommendation(
    name: str,
    business_type: str,
    expected_costs: float,
    brief_description: str,
    mode_of_business: str = None,
) -> str:
    """Get strategic decision recommendations tailored to the business situation."""
    return decision_recommendation.run(_workspace(name, business_type, expected_costs, brief_description, mode_of_business))


@mcp.tool()
def analyze_financials(revenue: float, cost: float, demand: int) -> dict:
    """Calculate profit and profit margin given revenue, cost, and demand figures."""
    return basic_analysis(AnalyzeRequest(revenue=revenue, cost=cost, demand=demand))


if __name__ == "__main__":
    mcp.run()