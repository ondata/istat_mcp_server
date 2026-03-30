"""Tests for get_data time period filtering (ISTAT endPeriod+1 workaround)."""

from unittest.mock import patch

import pytest

from istat_mcp_server.tools.get_data import _build_curl_info, _determine_default_periods, _parse_period, filter_tsv_by_time_period


# --- _parse_period tests ---

class TestParsePeriod:
    def test_year(self):
        assert _parse_period('2020') == (2020, 1, 12)

    def test_month(self):
        assert _parse_period('2020-03') == (2020, 3, 3)

    def test_day(self):
        assert _parse_period('2020-03-15') == (2020, 3, 3)

    def test_quarter(self):
        assert _parse_period('2020-Q1') == (2020, 1, 3)
        assert _parse_period('2020-Q4') == (2020, 10, 12)

    def test_semester(self):
        assert _parse_period('2020-S1') == (2020, 1, 6)
        assert _parse_period('2020-H2') == (2020, 7, 12)

    def test_empty(self):
        assert _parse_period('') is None

    def test_invalid(self):
        assert _parse_period('abc') is None


# --- filter_tsv_by_time_period tests ---

SAMPLE_TSV = (
    "DATAFLOW\tREF_AREA\tTIME_PERIOD\tOBS_VALUE\n"
    "DF1\tIT\t2019\t100\n"
    "DF1\tIT\t2020\t200\n"
    "DF1\tIT\t2021\t300\n"
    "DF1\tIT\t2022\t400"
)


class TestFilterTsvByTimePeriod:
    def test_filters_extra_year(self):
        """Core bug: requesting 2020-2020 should remove 2021."""
        result = filter_tsv_by_time_period(SAMPLE_TSV, '2020', '2020')
        lines = result.strip().split('\n')
        assert len(lines) == 2  # header + 1 data row
        assert '2020' in lines[1]
        assert '2021' not in result
        assert '2019' not in result

    def test_filters_end_period(self):
        """Requesting 2019-2020 should remove 2021 and 2022."""
        result = filter_tsv_by_time_period(SAMPLE_TSV, '2019', '2020')
        lines = result.strip().split('\n')
        assert len(lines) == 3  # header + 2 data rows
        assert '2021' not in result
        assert '2022' not in result

    def test_no_filter_when_no_periods(self):
        """No periods specified: return data unchanged."""
        result = filter_tsv_by_time_period(SAMPLE_TSV, None, None)
        assert result == SAMPLE_TSV

    def test_no_time_period_column(self):
        """TSV without TIME_PERIOD column: return unchanged."""
        tsv = "DATAFLOW\tREF_AREA\tOBS_VALUE\nDF1\tIT\t100"
        result = filter_tsv_by_time_period(tsv, '2020', '2020')
        assert result == tsv

    def test_only_end_period(self):
        """Only end_period specified: keep everything up to end."""
        result = filter_tsv_by_time_period(SAMPLE_TSV, None, '2020')
        lines = result.strip().split('\n')
        assert len(lines) == 3  # header + 2019 + 2020
        assert '2021' not in result

    def test_only_start_period(self):
        """Only start_period specified: keep everything from start."""
        result = filter_tsv_by_time_period(SAMPLE_TSV, '2021', None)
        lines = result.strip().split('\n')
        assert len(lines) == 3  # header + 2021 + 2022
        assert '2020\t' not in result
        assert '2019' not in result

    def test_quarterly_filter(self):
        """Filter with quarterly periods."""
        tsv = (
            "DATAFLOW\tTIME_PERIOD\tOBS_VALUE\n"
            "DF1\t2020-Q1\t10\n"
            "DF1\t2020-Q2\t20\n"
            "DF1\t2020-Q3\t30\n"
            "DF1\t2020-Q4\t40\n"
            "DF1\t2021-Q1\t50"
        )
        result = filter_tsv_by_time_period(tsv, '2020-Q1', '2020-Q4')
        lines = result.strip().split('\n')
        assert len(lines) == 5  # header + 4 quarters
        assert '2021-Q1' not in result


# --- _build_curl_info tests ---


class TestBuildCurlInfo:
    def test_contains_url_and_curl(self):
        result = _build_curl_info(
            dataflow_id='101_1015_DF_DCSP_COLTIVAZIONI_1',
            dimension_order=['FREQ', 'REF_AREA'],
            ordered_dimension_filters=[['A'], ['IT']],
            start_period='2020',
            end_period='2020',
            detail='full',
        )
        assert 'curl' in result
        assert '101_1015_DF_DCSP_COLTIVAZIONI_1' in result
        assert 'startPeriod=2020' in result
        assert 'endPeriod=2020' in result
        assert 'csv' in result
        assert 'format=csv' in result
        assert 'CSV URL (open in browser or with cURL)' in result
        assert 'SDMX URL (XML)' in result

    def test_no_filters(self):
        result = _build_curl_info(
            dataflow_id='test_df',
            dimension_order=['FREQ'],
            ordered_dimension_filters=[[]],
            start_period=None,
            end_period=None,
            detail='dataonly',
        )
        assert 'test_df' in result
        assert 'curl' in result
        # When no start/end periods are provided, the Period line should show a placeholder.
        assert 'Period' in result
        assert 'n/a' in result


# --- _determine_default_periods tests ---

class TestDetermineDefaultPeriods:
    @patch('istat_mcp_server.tools.get_data.datetime')
    def test_future_end_period_falls_back(self, mock_dt):
        """EndPeriod in the future should fall back to current_year - 1."""
        mock_dt.now.return_value.year = 2026
        assert _determine_default_periods('2026-12-31T23:59:59') == ('2025', '2025')

    @patch('istat_mcp_server.tools.get_data.datetime')
    def test_current_year_end_period_falls_back(self, mock_dt):
        """EndPeriod in the current year should fall back to current_year - 1."""
        mock_dt.now.return_value.year = 2026
        assert _determine_default_periods('2026-06-01') == ('2025', '2025')

    @patch('istat_mcp_server.tools.get_data.datetime')
    def test_past_end_period_uses_that_year(self, mock_dt):
        """EndPeriod in the past should use that year directly."""
        mock_dt.now.return_value.year = 2026
        assert _determine_default_periods('2023-12-31') == ('2023', '2023')

    @patch('istat_mcp_server.tools.get_data.datetime')
    def test_none_end_period_uses_fallback(self, mock_dt):
        """None EndPeriod should fall back to current_year - 1."""
        mock_dt.now.return_value.year = 2026
        assert _determine_default_periods(None) == ('2025', '2025')

    @patch('istat_mcp_server.tools.get_data.datetime')
    def test_year_only_format(self, mock_dt):
        """EndPeriod as plain year string."""
        mock_dt.now.return_value.year = 2026
        assert _determine_default_periods('2024') == ('2024', '2024')
