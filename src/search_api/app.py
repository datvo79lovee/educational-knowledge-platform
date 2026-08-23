"""FastAPI application cho Dense Retrieval/Search API v1."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status

from src.grounded_answer.contracts import GroundedAnswerRequest, GroundedAnswerResponse
from src.grounded_answer.ollama_provider import GroundedAnswerProviderError
from src.grounded_answer.service import (
    GroundedAnswerContractError,
    GroundedAnswerService,
    build_default_provider,
)
from src.search_api.contracts import SearchRequest, SearchResponse, VideoResponse
from src.search_api.service import DenseSearchService, RETRIEVAL_METHOD


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail startup nếu canonical artifact hoặc pinned model không hợp lệ."""

    app.state.search_service = DenseSearchService.load()
    app.state.answer_service = GroundedAnswerService(
        search_service=app.state.search_service,
        provider=build_default_provider(),
    )
    yield
    app.state.answer_service = None
    app.state.search_service = None


app = FastAPI(
    title="MIT 6.0001 Educational Knowledge Search API",
    version="1.1.0",
    description=(
        "Dense Top 3 retrieval và one-call grounded answer generation trên "
        "canonical MIT 6.0001 Fall 2016 corpus."
    ),
    lifespan=lifespan,
)


def get_search_service(request: Request) -> DenseSearchService:
    """Lấy singleton service đã load trong lifespan của application."""

    service = getattr(request.app.state, "search_service", None)
    if not isinstance(service, DenseSearchService):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is not ready",
        )
    return service


def get_answer_service(request: Request) -> GroundedAnswerService:
    """Lấy orchestration service; Ollama không phải dependency của `/search`."""

    service = getattr(request.app.state, "answer_service", None)
    if not isinstance(service, GroundedAnswerService):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grounded answer service is not ready",
        )
    return service


@app.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    service: DenseSearchService = Depends(get_search_service),
) -> SearchResponse:
    """Trả đúng Dense Top 3 evidence; không thực hiện accept/reject hoặc generation."""

    results = service.search(payload.query)
    return SearchResponse(
        query=payload.query,
        retrieval_method=RETRIEVAL_METHOD,
        index_run_id=service.index_run_id,
        result_count=len(results),
        results=results,
    )


@app.post("/answer", response_model=GroundedAnswerResponse)
def answer(
    payload: GroundedAnswerRequest,
    service: GroundedAnswerService = Depends(get_answer_service),
) -> GroundedAnswerResponse:
    """Retrieve Dense Top 3 rồi answer hoặc abstain bằng đúng một model call."""

    try:
        return service.answer(payload.question).response
    except GroundedAnswerContractError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Grounded answer model returned an invalid structured response",
        ) from error
    except GroundedAnswerProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grounded answer model runtime is unavailable",
        ) from error


@app.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    service: DenseSearchService = Depends(get_search_service),
) -> VideoResponse:
    """Trả metadata video trong canonical 38-video corpus."""

    video = service.get_video(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video is not part of the MIT 6.0001 target corpus",
        )
    return VideoResponse(**video)
