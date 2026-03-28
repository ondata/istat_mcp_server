"""Pydantic models for API requests and responses."""

import json

from pydantic import AliasChoices, BaseModel, Field, field_validator


# ===== Input Models (for tool arguments) =====


class DiscoverDataflowsInput(BaseModel):
    """Input for discover_dataflows tool."""

    keywords: str = Field(
        '',
        description="Comma-separated keywords (e.g., 'population,employment'). Leave empty to return all dataflows.",
    )


class GetStructureInput(BaseModel):
    """Input for get_structure tool."""

    id_datastructure: str = Field(
        ..., description="Datastructure ID to analyze (e.g., 'DCSP_COLTIVAZIONI')"
    )


class GetConstraintsInput(BaseModel):
    """Input for get_constraints tool."""

    dataflow_id: str = Field(
        ...,
        validation_alias=AliasChoices('dataflow_id', 'id_dataflow'),
        description="Dataflow ID to analyze (e.g., '101_1015_DF_DCSP_COLTIVAZIONI_1')",
    )


class GetCodelistDescriptionInput(BaseModel):
    """Input for get_codelist_description tool."""

    codelist_id: str = Field(
        ..., description="Codelist ID to analyze (e.g., 'CL_AGRI_MADRE')"
    )


class GetDataInput(BaseModel):
    """Input for get_data tool."""

    id_dataflow: str = Field(
        ...,
        validation_alias=AliasChoices('id_dataflow', 'dataflow_id'),
        description="Dataflow ID to fetch data from (e.g., '22_315_DF_DCIS_POPORESBIL1_2')",
    )
    dimension_filters: dict[str, list[str]] | None = Field(
        None,
        validation_alias=AliasChoices('dimension_filters', 'filters'),
        description="Optional filters for dimensions. Keys are dimension IDs, values are lists of codes.",
    )

    @field_validator('dimension_filters', mode='before')
    @classmethod
    def coerce_dimension_filters(cls, v: object) -> object:
        # Accept either a dict directly, or a JSON string that decodes to a dict.
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "dimension_filters must be a valid JSON object string"
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError("dimension_filters must be a JSON object")
            return parsed
        if v is None or isinstance(v, dict):
            return v
        raise ValueError(
            "dimension_filters must be a mapping or a JSON object string"
        )

    start_period: str | None = Field(
        None, description="Start period for time filter (e.g., '2024-11-01')"
    )
    end_period: str | None = Field(
        None, description="End period for time filter (e.g., '2025-11-30')"
    )
    detail: str = Field(
        'full',
        description="Detail level: 'full', 'dataonly', 'serieskeysonly', or 'nodata'",
    )
    dimension_at_observation: str | None = Field(
        None, description="Dimension to use at observation level (e.g., 'TIME_PERIOD')"
    )


# ===== Response Models (for API data) =====


class DataflowInfo(BaseModel):
    """Information about a dataflow."""

    id: str
    name_it: str = ''
    name_en: str = ''
    description_it: str = ''
    description_en: str = ''
    version: str = ''
    agency: str = ''
    id_datastructure: str = ''
    last_update: str = ''


class DimensionInfo(BaseModel):
    """Dimension and its associated codelist."""

    dimension: str
    codelist: str = ''


class DatastructureInfo(BaseModel):
    """Datastructure with its dimensions."""

    id_datastructure: str
    dimensions: list[DimensionInfo] = []


class ConstraintValue(BaseModel):
    """Regular dimension value."""

    value: str


class TimeConstraintValue(BaseModel):
    """Time period constraint with start and end."""

    StartPeriod: str
    EndPeriod: str


class DimensionConstraint(BaseModel):
    """Dimension with its available values."""

    dimension: str
    values: list[ConstraintValue | TimeConstraintValue] = []


class ConstraintInfo(BaseModel):
    """Constraints for a dataflow."""

    id: str
    dimensions: list[DimensionConstraint] = []


class CodeValue(BaseModel):
    """Code with descriptions in both languages."""

    code: str
    description_en: str = ''
    description_it: str = ''


class CodelistInfo(BaseModel):
    """Codelist with all its values."""

    id_codelist: str
    values: list[CodeValue] = []


class DimensionConstraintWithDescriptions(BaseModel):
    """Dimension constraint with value descriptions from codelist."""

    dimension: str
    codelist: str
    values: list[CodeValue] = []


class TimeConstraintOutput(BaseModel):
    """Time period constraint for output."""

    dimension: str = 'TIME_PERIOD'
    StartPeriod: str
    EndPeriod: str


class ConstraintsOutput(BaseModel):
    """Complete constraints output for a dataflow."""

    id_dataflow: str
    constraints: list[DimensionConstraintWithDescriptions | TimeConstraintOutput] = []


class ConceptInfo(BaseModel):
    """Individual concept with ID and descriptions."""

    id: str
    name_en: str = ''
    name_it: str = ''


class ConceptSchemeInfo(BaseModel):
    """Concept scheme with all its concepts."""

    id: str
    agency: str = ''
    version: str = ''
    name_en: str = ''
    concepts: list[ConceptInfo] = []


# ===== Error Models =====


class ApiError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: int = 0):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
