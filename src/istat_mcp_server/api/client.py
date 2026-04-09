"""API client for ISTAT SDMX REST API with rate limiting and retry logic."""

import asyncio
import logging
import time
from typing import Any

import httpx
from lxml import etree
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import (
    ApiError,
    CodelistInfo,
    CodeValue,
    ConceptInfo,
    ConceptSchemeInfo,
    ConstraintInfo,
    ConstraintValue,
    DataflowInfo,
    DatastructureInfo,
    DimensionConstraint,
    DimensionInfo,
    TimeConstraintValue,
)

logger = logging.getLogger(__name__)

# SDMX XML namespaces
NAMESPACES = {
    'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
    'structure': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
    'common': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
    'generic': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic',
}


class RateLimiter:
    """Rate limiter to enforce maximum API calls per time window."""

    def __init__(self, max_calls: int = 3, time_window: float = 60.0):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self._max_calls = max_calls
        self._time_window = time_window
        self._call_times: list[float] = []
        self._lock = asyncio.Lock()
        logger.info(f'RateLimiter: {max_calls} calls per {time_window}s')

    async def acquire(self) -> None:
        """Acquire permission to make an API call. Waits if limit reached."""
        async with self._lock:
            now = time.time()

            # Remove timestamps older than time window
            self._call_times = [t for t in self._call_times if now - t < self._time_window]

            # Check if we've hit the limit
            if len(self._call_times) >= self._max_calls:
                # Calculate wait time
                oldest_call = self._call_times[0]
                wait_time = self._time_window - (now - oldest_call)
                if wait_time > 0:
                    logger.warning(f'RateLimiter: Limit reached, waiting {wait_time:.2f}s')
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    # Clean up again after waiting
                    self._call_times = [
                        t for t in self._call_times if now - t < self._time_window
                    ]

            # Record this call
            self._call_times.append(now)
            logger.debug(
                f'RateLimiter: Call recorded ({len(self._call_times)}/{self._max_calls})'
            )


class ApiClient:
    """HTTP client for ISTAT SDMX REST API."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        availableconstraint_timeout: float = 180.0,
        max_retries: int = 3,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL of the ISTAT SDMX API
            timeout: Request timeout in seconds
            availableconstraint_timeout: Timeout for availableconstraint endpoint in seconds
            max_retries: Maximum retry attempts
        """
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._availableconstraint_timeout = availableconstraint_timeout
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)
        self._rate_limiter = RateLimiter(max_calls=4, time_window=60.0)
        logger.info(f'ApiClient initialized: {base_url}')

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Make GET request with rate limiting and retry logic.

        Args:
            path: API endpoint path
            params: Query parameters
            headers: Optional HTTP headers
            timeout: Optional request timeout in seconds (overrides default)

        Returns:
            HTTP response

        Raises:
            ApiError: On HTTP or network errors
        """
        await self._rate_limiter.acquire()

        url = f'{self._base_url}/{path.lstrip("/")}'
        request_timeout = timeout if timeout is not None else self._timeout
        start_time = time.time()
        
        try:
            # Log chiamata HTTP con parametri
            logger.info(f'→ HTTP GET: {url}')
            if params:
                logger.debug(f'  Query params: {params}')
            
            response = await self._client.get(
                url,
                params=params,
                headers=headers,
                timeout=request_timeout,
            )
            response.raise_for_status()
            
            # Log risposta con dettagli
            elapsed = time.time() - start_time
            logger.info(f'← HTTP {response.status_code}: {len(response.content)} bytes in {elapsed:.3f}s')
            
            return response
            
        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            logger.error(
                f'✗ TIMEOUT for {url} after {elapsed:.3f}s '
                f'(timeout: {request_timeout}s)'
            )
            raise ApiError(
                f'Request timeout after {elapsed:.1f}s - The ISTAT API did not respond within {request_timeout} seconds. Please try again later or with a smaller dataset.',
                408
            ) from e
        except httpx.HTTPStatusError as e:
            elapsed = time.time() - start_time
            response_text = e.response.text
            logger.error(f'✗ HTTP ERROR {e.response.status_code} for {url} after {elapsed:.3f}s')
            logger.error(f'  Response: {response_text[:200]}...' if len(response_text) > 200 else f'  Response: {response_text}')
            # ISTAT returns HTTP 404 with body "NoRecordsFound" when no data matches the filters
            if e.response.status_code == 404 and 'NoRecordsFound' in response_text:
                raise ApiError(
                    'No data found for the requested filters/period. '
                    'Try using a different time period or broader filters. '
                    'Note: get_constraints may report a wider EndPeriod than what is actually available at municipal level.',
                    404
                ) from e
            raise ApiError(
                f'HTTP error: {e.response.status_code}', e.response.status_code
            ) from e
        except httpx.NetworkError as e:
            elapsed = time.time() - start_time
            logger.error(f'✗ NETWORK ERROR for {url} after {elapsed:.3f}s: {e}')
            raise ApiError(f'Network error: {e}', 0) from e

    async def _get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Make GET request with JSON Accept header.

        Args:
            path: API endpoint path
            params: Query parameters
            timeout: Optional request timeout in seconds (overrides default)

        Returns:
            Parsed JSON response

        Raises:
            ApiError: On HTTP or network errors
        """
        headers = {
            'Accept': 'application/vnd.sdmx.structure+json; charset=utf-8; version=1.0'
        }
        response = await self._get(path, params=params, headers=headers, timeout=timeout)
        return response.json()

    async def fetch_dataflows(self) -> list[DataflowInfo]:
        """Fetch all dataflows from ISTAT SDMX API.

        Returns:
            List of DataflowInfo objects

        Raises:
            ApiError: On API errors
        """
        response = await self._get('/dataflow/IT1')
        root = etree.fromstring(response.content)

        dataflows = []
        for df_elem in root.xpath('//structure:Dataflow', namespaces=NAMESPACES):
            # Check for NonProductionDataflow annotation - skip if present
            annotations = df_elem.xpath(
                './/common:Annotation', namespaces=NAMESPACES
            )
            is_non_production = False
            for ann in annotations:
                ann_type = ann.xpath(
                    './common:AnnotationType/text()', namespaces=NAMESPACES
                )
                if ann_type and ann_type[0] == 'NonProductionDataflow':
                    is_non_production = True
                    break

            if is_non_production:
                continue

            # Extract basic attributes
            df_id = df_elem.get('id', '')
            version = df_elem.get('version', '')
            agency = df_elem.get('agencyID', '')

            # Extract names
            name_it = ''
            name_en = ''
            for name_elem in df_elem.xpath('.//common:Name', namespaces=NAMESPACES):
                lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                if lang == 'it':
                    name_it = name_elem.text or ''
                elif lang == 'en':
                    name_en = name_elem.text or ''

            # Extract descriptions and last_update from annotations
            description_it = ''
            description_en = ''
            last_update = ''

            for ann in annotations:
                ann_type = ann.xpath(
                    './common:AnnotationType/text()', namespaces=NAMESPACES
                )
                if ann_type and ann_type[0] == 'LAYOUT_DATAFLOW_KEYWORDS':
                    for text_elem in ann.xpath(
                        './common:AnnotationText', namespaces=NAMESPACES
                    ):
                        lang = text_elem.get(
                            '{http://www.w3.org/XML/1998/namespace}lang', ''
                        )
                        if lang == 'it':
                            description_it = text_elem.text or ''
                        elif lang == 'en':
                            description_en = text_elem.text or ''
                elif ann_type and ann_type[0] == 'LAST_UPDATE':
                    title_elem = ann.xpath(
                        './common:AnnotationTitle/text()', namespaces=NAMESPACES
                    )
                    if title_elem:
                        last_update = title_elem[0]

            # Extract datastructure ID
            id_datastructure = ''
            ref_elem = df_elem.xpath(
                './/structure:Structure/Ref', namespaces=NAMESPACES
            )
            if ref_elem:
                id_datastructure = ref_elem[0].get('id', '')

            dataflows.append(
                DataflowInfo(
                    id=df_id,
                    name_it=name_it,
                    name_en=name_en,
                    description_it=description_it,
                    description_en=description_en,
                    version=version,
                    agency=agency,
                    id_datastructure=id_datastructure,
                    last_update=last_update,
                )
            )

        logger.info(f'Fetched {len(dataflows)} dataflows')
        return dataflows

    async def fetch_datastructure(self, id_datastructure: str) -> DatastructureInfo:
        """Fetch datastructure definition.

        Args:
            id_datastructure: Datastructure ID

        Returns:
            DatastructureInfo object

        Raises:
            ApiError: On API errors
        """
        response = await self._get(f'/datastructure/IT1/{id_datastructure}')
        root = etree.fromstring(response.content)

        dimensions = []
        for dim_elem in root.xpath('//structure:Dimension', namespaces=NAMESPACES):
            dimension = dim_elem.get('id', '')
            
            # Skip dimensions without ID (empty or malformed)
            if not dimension:
                continue

            # Extract codelist from LocalRepresentation/Enumeration/Ref
            codelist = ''
            ref_elem = dim_elem.xpath(
                './/structure:LocalRepresentation/structure:Enumeration/Ref',
                namespaces=NAMESPACES,
            )
            if ref_elem:
                codelist = ref_elem[0].get('id', '')

            dimensions.append(DimensionInfo(dimension=dimension, codelist=codelist))

        logger.info(f'Fetched datastructure {id_datastructure} with {len(dimensions)} dimensions')
        return DatastructureInfo(id_datastructure=id_datastructure, dimensions=dimensions)

    async def fetch_constraints(self, dataflow_id: str) -> ConstraintInfo:
        """Fetch available constraints for a dataflow using JSON format.

        Args:
            dataflow_id: Dataflow ID

        Returns:
            ConstraintInfo object

        Raises:
            ApiError: On API errors
        """
        data = await self._get_json(
            f'/availableconstraint/{dataflow_id}/all/all',
            params={'mode': 'available'},
            timeout=self._availableconstraint_timeout,
        )

        dimensions = []
        
        # Navigate JSON structure: data.contentConstraints[0].cubeRegions[0].keyValues
        try:
            content_constraints = data.get('data', {}).get('contentConstraints', [])
            if content_constraints:
                cube_regions = content_constraints[0].get('cubeRegions', [])
                if cube_regions:
                    key_values = cube_regions[0].get('keyValues', [])
                    
                    for kv in key_values:
                        dimension_id = kv.get('id', '')
                        
                        # Check if this has a timeRange (TIME_PERIOD dimension)
                        if 'timeRange' in kv:
                            time_range = kv['timeRange']
                            # Extract period strings from nested objects
                            start_obj = time_range.get('startPeriod', {})
                            end_obj = time_range.get('endPeriod', {})
                            start_period = start_obj.get('period', '') if isinstance(start_obj, dict) else str(start_obj)
                            end_period = end_obj.get('period', '') if isinstance(end_obj, dict) else str(end_obj)
                            values = [
                                TimeConstraintValue(StartPeriod=start_period, EndPeriod=end_period)
                            ]
                        else:
                            # Regular dimension - extract all values
                            value_list = kv.get('values', [])
                            values = [ConstraintValue(value=str(v)) for v in value_list]
                        
                        dimensions.append(DimensionConstraint(dimension=dimension_id, values=values))
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f'Error parsing constraints JSON: {e}')
            # Return empty constraints rather than failing
            pass

        logger.info(f'Fetched constraints for {dataflow_id} with {len(dimensions)} dimensions')
        return ConstraintInfo(id=dataflow_id, dimensions=dimensions)

    async def fetch_codelist(self, codelist_id: str) -> CodelistInfo:
        """Fetch codelist descriptions.

        Args:
            codelist_id: Codelist ID

        Returns:
            CodelistInfo object

        Raises:
            ApiError: On API errors
        """
        response = await self._get(f'/codelist/IT1/{codelist_id}')
        root = etree.fromstring(response.content)

        values = []
        for code_elem in root.xpath('//structure:Code', namespaces=NAMESPACES):
            code = code_elem.get('id', '')

            # Extract descriptions in both languages
            description_en = ''
            description_it = ''
            for name_elem in code_elem.xpath('.//common:Name', namespaces=NAMESPACES):
                lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                if lang == 'en':
                    description_en = name_elem.text or ''
                elif lang == 'it':
                    description_it = name_elem.text or ''

            values.append(
                CodeValue(
                    code=code, description_en=description_en, description_it=description_it
                )
            )

        logger.info(f'Fetched codelist {codelist_id} with {len(values)} values')
        return CodelistInfo(id_codelist=codelist_id, values=values)

    async def fetch_conceptschemes(self) -> list[ConceptSchemeInfo]:
        """Fetch all concept schemes from ISTAT SDMX API.

        Returns:
            List of ConceptSchemeInfo objects

        Raises:
            ApiError: On API errors
        """
        response = await self._get('/conceptscheme')
        root = etree.fromstring(response.content)

        schemes = []
        for scheme_elem in root.xpath('//structure:ConceptScheme', namespaces=NAMESPACES):
            scheme_id = scheme_elem.get('id', '')
            agency = scheme_elem.get('agencyID', '')
            version = scheme_elem.get('version', '')

            # Extract scheme name in English
            name_en = ''
            for name_elem in scheme_elem.xpath('.//common:Name', namespaces=NAMESPACES):
                lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                if lang == 'en':
                    name_en = name_elem.text or ''
                    break

            # Extract all concepts in this scheme
            concepts = []
            for concept_elem in scheme_elem.xpath('.//structure:Concept', namespaces=NAMESPACES):
                concept_id = concept_elem.get('id', '')
                concept_name_en = ''
                concept_name_it = ''

                for name_elem in concept_elem.xpath('.//common:Name', namespaces=NAMESPACES):
                    lang = name_elem.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                    if lang == 'en':
                        concept_name_en = name_elem.text or ''
                    elif lang == 'it':
                        concept_name_it = name_elem.text or ''

                concepts.append(
                    ConceptInfo(
                        id=concept_id,
                        name_en=concept_name_en,
                        name_it=concept_name_it,
                    )
                )

            schemes.append(
                ConceptSchemeInfo(
                    id=scheme_id,
                    agency=agency,
                    version=version,
                    name_en=name_en,
                    concepts=concepts,
                )
            )

        logger.info(f'Fetched {len(schemes)} concept schemes')
        return schemes

    async def fetch_data(
        self,
        agency: str,
        dataflow_id: str,
        version: str,
        ordered_dimension_filters: list[list[str]],
        start_period: str | None = None,
        end_period: str | None = None,
        detail: str = 'full',
        dimension_at_observation: str | None = None,
    ) -> str:
        """Fetch actual data from ISTAT SDMX API.

        Args:
            agency: Agency ID (e.g., 'IT1')
            dataflow_id: Dataflow ID
            version: Version (e.g., '1.0')
            ordered_dimension_filters: List of dimension filter lists in the correct order
            start_period: Start period for time filter
            end_period: End period for time filter
            detail: Detail level ('full', 'dataonly', 'serieskeysonly', 'nodata')
            dimension_at_observation: Dimension to use at observation level (e.g., 'TIME_PERIOD')

        Returns:
            Raw SDMX-XML response as string

        Raises:
            ApiError: On API errors
        """
        # Build dimension path
        # Schema: /data/{dataflow_id}/{dimension1}.{dimension2}.{dimension3}.../ALL/
        # IMPORTANTE:
        # - I punti (.) separano le dimensioni
        # - Dimensione vuota = niente tra i punti (es: A.IT..B ha dim vuota in posizione 3)
        # - Per OR nella stessa dimensione: usare + (es: ATECO1+ATECO2)
        # - I codici dalle codelists vanno usati esattamente come sono (es: 1092 non 10.92)
        # - Il numero di argomenti deve essere pari al numero di dimensioni
        # Esempio: A.IT.LU.1092. -> 5 dimensioni (ultima vuota, indicata dal punto finale)
        
        # Build dimension path using list comprehension
        dim_path = '.'.join(
            '+'.join(f) if f else '' for f in ordered_dimension_filters
        ) if ordered_dimension_filters else ''

        # Build URL path: /data/{dataflow_id}/{dimensions}/ALL/
        # Handle empty dim_path to avoid double slash
        path = f'/data/{dataflow_id}/{dim_path}/ALL/' if dim_path else f'/data/{dataflow_id}/ALL/'

        # Build query parameters
        params: dict[str, str] = {'detail': detail}
        if start_period:
            params['startPeriod'] = start_period
        if end_period:
            params['endPeriod'] = end_period
        if dimension_at_observation:
            params['dimensionAtObservation'] = dimension_at_observation

        response = await self._get(path, params=params)
        logger.info(f'Fetched data for {dataflow_id}')
        return response.text

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
        logger.info('ApiClient closed')
