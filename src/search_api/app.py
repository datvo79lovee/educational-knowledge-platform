"""FastAPI application cho Dense Retrieval/Search API v1."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status

from src.search_api.contracts import SearchRequest, SearchResponse, VideoResponse
from src.search_api.service import DenseSearchService, RETRIEVAL_METHOD


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail startup nếu canonical artifact hoặc pinned model không hợp lệ."""

    app.state.search_service = DenseSearchService.load()
    yield
    app.state.search_service = None


app = FastAPI(
    title="MIT 6.0001 Educational Knowledge Search API",
    version="1.0.0",
    description=(
        "Dense Top 3 retrieval trên canonical MIT 6.0001 Fall 2016 corpus. "
        "API này chưa sinh grounded answer."
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

