from fastapi import APIRouter
from app.models.schemas import WorkspaceContext
from app.services.agents import (
    sales_predictor,
    pain_point_analyzer,
    profit_optimiser,
    decision_recommendation,
    risk_identifier,
    scenario_simulator,
    resource_optimiser,
)

router = APIRouter(prefix="/agents")

@router.post("/sales-predictor")
def sales_predictor_route(data: WorkspaceContext):
    return sales_predictor.run(data)

@router.post("/pain-point-analyser")
def pain_point_analyser_route(data: WorkspaceContext):
    return pain_point_analyzer.run(data)

@router.post("/profit-optimiser")
def profit_optimiser_route(data: WorkspaceContext):
    return profit_optimiser.run(data)

@router.post("/decision-recommendation")
def decision_recommendation_route(data: WorkspaceContext):
    return decision_recommendation.run(data)

@router.post("/risk-identifier")
def risk_identifier_route(data: WorkspaceContext):
    return risk_identifier.run(data)

@router.post("/scenario-simulator")
def scenario_simulator_route(data: WorkspaceContext):
    return scenario_simulator.run(data)

@router.post("/resource-optimiser")
def resource_optimiser_route(data: WorkspaceContext):
    return resource_optimiser.run(data)
