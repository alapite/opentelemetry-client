import logging
from typing import Optional, Any, Union, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from primes.api.test_executor import (
    RunConfig,
    RunMetrics,
    PluginConfig,
    create_test,
    execute_test,
    get_test_state,
    stop_test,
    list_active_tests,
    list_running_tests,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class DistributionRef(BaseModel):
    name: str = Field(..., description="Distribution plugin name")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Distribution-specific configuration"
    )


class MixComponent(BaseModel):
    weight: float = Field(..., description="Component weight (must be > 0)")
    distribution: DistributionRef


class MixConfig(BaseModel):
    components: list[MixComponent]
    target_rps: Optional[float] = Field(
        default=None, description="Default target RPS for all components"
    )


class SequenceStage(BaseModel):
    duration_seconds: float = Field(..., description="Stage duration in seconds")
    distribution: DistributionRef


class SequenceConfig(BaseModel):
    stages: list[SequenceStage]
    post_behavior: str = Field(
        default="hold_last",
        description="Behavior after stages: hold_last, zero, or repeat",
    )


class DistributionRequest(BaseModel):
    name: str = Field(..., description="Distribution plugin name")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Distribution-specific configuration"
    )


class MixDistributionRequest(BaseModel):
    name: Literal["mix"]
    config: MixConfig


class SequenceDistributionRequest(BaseModel):
    name: Literal["sequence"]
    config: SequenceConfig


DistributionRequestType = Union[
    MixDistributionRequest, SequenceDistributionRequest, DistributionRequest
]


def _dump_model(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


class StartTestRequest(BaseModel):
    test_type: str = Field(default="linear", description="Type of test to run")
    duration_seconds: Optional[int] = Field(
        default=None, description="Duration of test in seconds"
    )
    spawn_rate: float = Field(default=10.0, description="Rate at which users spawn")
    user_count: int = Field(default=1, description="Number of users to simulate")
    num_requests: Optional[int] = Field(
        default=None, description="Number of requests to send"
    )
    target_rps: Optional[float] = Field(
        default=None, description="Target requests per second for distributions"
    )
    distribution: Optional[DistributionRequestType] = Field(
        default=None, description="Distribution plugin config"
    )


class StartTestResponse(BaseModel):
    test_id: str
    status: str


class StopTestRequest(BaseModel):
    test_id: str = Field(..., description="ID of the test to stop")


class StopTestResponse(BaseModel):
    test_id: str
    status: str


class TestStatusResponse(BaseModel):
    test_id: str
    status: str
    metrics: RunMetrics


class TestsListResponse(BaseModel):
    tests: list[str]
    active: list[str]


@router.post(
    "/start", response_model=StartTestResponse, status_code=status.HTTP_202_ACCEPTED
)
async def start_test(
    request: StartTestRequest, background_tasks: BackgroundTasks
) -> StartTestResponse:
    if request.distribution is not None:
        if request.target_rps is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_rps is required when using a distribution",
            )
        if request.num_requests is None and request.duration_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="num_requests or duration_seconds is required when using a distribution",
            )
    distribution = None
    if request.distribution is not None:
        config_dict = _dump_model(request.distribution.config)
        distribution = PluginConfig(name=request.distribution.name, config=config_dict)

    config = RunConfig(
        test_type=request.test_type,
        duration_seconds=request.duration_seconds,
        spawn_rate=request.spawn_rate,
        user_count=request.user_count,
        num_requests=request.num_requests,
        target_rps=request.target_rps,
        distribution=distribution,
    )

    test_id = create_test(config)
    background_tasks.add_task(execute_test, test_id, config)

    return StartTestResponse(test_id=test_id, status="starting")


@router.post(
    "/stop", response_model=StopTestResponse, status_code=status.HTTP_202_ACCEPTED
)
async def stop_test_endpoint(request: StopTestRequest) -> StopTestResponse:
    success = await stop_test(request.test_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test {request.test_id} not found",
        )

    return StopTestResponse(test_id=request.test_id, status="stopping")


@router.get("/status/{test_id}", response_model=TestStatusResponse)
async def get_status(test_id: str) -> TestStatusResponse:
    state = get_test_state(test_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Test {test_id} not found"
        )

    return TestStatusResponse(
        test_id=state.test_id, status=state.status, metrics=state.metrics
    )


@router.get("/", response_model=TestsListResponse)
async def list_tests() -> TestsListResponse:
    return TestsListResponse(tests=list_active_tests(), active=list_running_tests())
