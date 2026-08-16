"""Pydantic contract cho Search API v1.

Các model trong file này là nguồn tạo OpenAPI runtime. JSON Schema tĩnh tương ứng
được lưu tại ``schemas/search_api_v1.schema.json`` để review mà không cần chạy server.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Không nhận field ngoài contract đã khóa."""

    model_config = ConfigDict(extra="forbid")


class SearchRequest(StrictModel):
    """Payload duy nhất được chấp nhận bởi ``POST /search``."""

    query: str = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """Trim query và từ chối chuỗi chỉ chứa whitespace."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be empty or whitespace-only")
        return normalized


class SearchResult(StrictModel):
    """Một canonical chunk trong Dense Top 3."""

    rank: int = Field(ge=1, le=3)
    chunk_id: str
    chunk_text: str
    score: float
    video_id: str
    video_title: str
    start_second: float = Field(ge=0)
    end_second: float = Field(gt=0)
    source_url: str
    citation_url: str


class SearchResponse(StrictModel):
    """Response của Dense retrieval; chưa phải grounded answer."""

    query: str
    retrieval_method: Literal["dense_baseline_v1"]
    index_run_id: str
    result_count: Literal[3]
    results: list[SearchResult] = Field(min_length=3, max_length=3)


class VideoResponse(StrictModel):
    """Metadata tổng hợp từ các canonical chunks của một target video."""

    video_id: str
    video_title: str
    source_url: str
    chunk_count: int = Field(gt=0)
    start_second: float = Field(ge=0)
    end_second: float = Field(gt=0)
