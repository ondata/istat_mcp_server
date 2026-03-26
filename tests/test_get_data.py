"""Tests for get_data tool helpers, including filter_tsv_by_time_period."""

import pytest

from istat_mcp_server.tools.get_data import _parse_period, filter_tsv_by_time_period


# ---------------------------------------------------------------------------
# _parse_period
# ---------------------------------------------------------------------------

class TestParsePeriod:
    def test_annual(self):
        assert _parse_period('2023') == (2023, 1, 12)

    def test_monthly(self):
        assert _parse_period('2023-06') == (2023, 6, 6)

    def test_daily(self):
        assert _parse_period('2023-06-15') == (2023, 6, 6)

    def test_quarterly_q1(self):
        assert _parse_period('2023-Q1') == (2023, 1, 3)

    def test_quarterly_q2(self):
        assert _parse_period('2023-Q2') == (2023, 4, 6)

    def test_quarterly_q3(self):
        assert _parse_period('2023-Q3') == (2023, 7, 9)

    def test_quarterly_q4(self):
        assert _parse_period('2023-Q4') == (2023, 10, 12)

    def test_quarterly_lowercase(self):
        assert _parse_period('2023-q1') == (2023, 1, 3)

    def test_semester_s1(self):
        assert _parse_period('2023-S1') == (2023, 1, 6)

    def test_semester_s2(self):
        assert _parse_period('2023-S2') == (2023, 7, 12)

    def test_half_year_h1(self):
        assert _parse_period('2023-H1') == (2023, 1, 6)

    def test_half_year_h2(self):
        assert _parse_period('2023-H2') == (2023, 7, 12)

    def test_semester_lowercase(self):
        assert _parse_period('2023-s1') == (2023, 1, 6)

    def test_empty_string(self):
        assert _parse_period('') is None

    def test_none_like_empty(self):
        # The function accepts a str; passing '' returns None
        assert _parse_period('') is None

    def test_unparseable(self):
        assert _parse_period('not-a-date') is None

    def test_partial_year_only_three_digits(self):
        assert _parse_period('202') is None


# ---------------------------------------------------------------------------
# filter_tsv_by_time_period
# ---------------------------------------------------------------------------

def _make_tsv(*rows: tuple) -> str:
    """Build a TSV string from (header_tuple, *data_tuples)."""
    return '\n'.join('\t'.join(str(v) for v in row) for row in rows)


HEADER = ('DATAFLOW', 'FREQ', 'TIME_PERIOD', 'OBS_VALUE')


class TestFilterTsvByTimePeriod:
    # ------------------------------------------------------------------
    # No-op cases
    # ------------------------------------------------------------------

    def test_no_periods_returns_unchanged(self):
        tsv = _make_tsv(HEADER, ('DF', 'A', '2024', '10'), ('DF', 'A', '2025', '20'))
        assert filter_tsv_by_time_period(tsv, None, None) == tsv

    def test_no_time_period_column_returns_unchanged(self):
        header = ('DATAFLOW', 'FREQ', 'OBS_VALUE')
        tsv = _make_tsv(header, ('DF', 'A', '10'), ('DF', 'A', '20'))
        assert filter_tsv_by_time_period(tsv, '2023', '2023') == tsv

    def test_empty_string_returns_unchanged(self):
        assert filter_tsv_by_time_period('', '2023', '2023') == ''

    # ------------------------------------------------------------------
    # Year-based (YYYY) end_period filter  – the primary ISTAT bug case
    # ------------------------------------------------------------------

    def test_removes_rows_after_end_year(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'A', '2022', '1'),
            ('DF', 'A', '2023', '2'),
            ('DF', 'A', '2024', '3'),  # should be removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023')
        lines = result.split('\n')
        assert len(lines) == 3  # header + 2022 + 2023
        assert '2024' not in result

    def test_removes_rows_before_start_year(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'A', '2021', '1'),  # should be removed
            ('DF', 'A', '2022', '2'),
            ('DF', 'A', '2023', '3'),
        )
        result = filter_tsv_by_time_period(tsv, '2022', None)
        lines = result.split('\n')
        assert len(lines) == 3  # header + 2022 + 2023
        assert '2021' not in result

    def test_both_start_and_end_year(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'A', '2020', '1'),  # removed
            ('DF', 'A', '2021', '2'),
            ('DF', 'A', '2022', '3'),
            ('DF', 'A', '2023', '4'),  # removed
        )
        result = filter_tsv_by_time_period(tsv, '2021', '2022')
        lines = result.split('\n')
        assert len(lines) == 3  # header + 2021 + 2022
        assert '2020' not in result
        assert '2023' not in result

    def test_header_always_preserved(self):
        tsv = _make_tsv(HEADER, ('DF', 'A', '2025', '99'))
        result = filter_tsv_by_time_period(tsv, None, '2023')
        assert result.split('\n')[0] == '\t'.join(HEADER)

    # ------------------------------------------------------------------
    # Monthly period (YYYY-MM)
    # ------------------------------------------------------------------

    def test_monthly_end_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'M', '2023-11', '1'),
            ('DF', 'M', '2023-12', '2'),
            ('DF', 'M', '2024-01', '3'),  # should be removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-12')
        assert '2024-01' not in result
        assert '2023-12' in result
        assert '2023-11' in result

    def test_monthly_start_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'M', '2023-05', '1'),  # should be removed
            ('DF', 'M', '2023-06', '2'),
            ('DF', 'M', '2023-07', '3'),
        )
        result = filter_tsv_by_time_period(tsv, '2023-06', None)
        assert '2023-05' not in result
        assert '2023-06' in result

    # ------------------------------------------------------------------
    # Daily period (YYYY-MM-DD)
    # ------------------------------------------------------------------

    def test_daily_end_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'D', '2023-12-31', '1'),
            ('DF', 'D', '2024-01-01', '2'),  # should be removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-12-31')
        assert '2024-01-01' not in result
        assert '2023-12-31' in result

    # ------------------------------------------------------------------
    # Quarterly period (YYYY-Qn)
    # ------------------------------------------------------------------

    def test_quarterly_end_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'Q', '2023-Q3', '1'),
            ('DF', 'Q', '2023-Q4', '2'),
            ('DF', 'Q', '2024-Q1', '3'),  # should be removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-Q4')
        assert '2024-Q1' not in result
        assert '2023-Q4' in result

    def test_quarterly_start_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'Q', '2023-Q1', '1'),  # should be removed
            ('DF', 'Q', '2023-Q2', '2'),
            ('DF', 'Q', '2023-Q3', '3'),
        )
        result = filter_tsv_by_time_period(tsv, '2023-Q2', None)
        assert '2023-Q1' not in result
        assert '2023-Q2' in result

    def test_quarterly_mid_year_end_period(self):
        """Q2 end_period should exclude Q3 and Q4 rows of the same year."""
        tsv = _make_tsv(
            HEADER,
            ('DF', 'Q', '2023-Q1', '1'),
            ('DF', 'Q', '2023-Q2', '2'),
            ('DF', 'Q', '2023-Q3', '3'),  # removed
            ('DF', 'Q', '2023-Q4', '4'),  # removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-Q2')
        assert '2023-Q3' not in result
        assert '2023-Q4' not in result
        assert '2023-Q2' in result

    # ------------------------------------------------------------------
    # Semester period (YYYY-Sn / YYYY-Hn)
    # ------------------------------------------------------------------

    def test_semester_end_period(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'S', '2023-S1', '1'),
            ('DF', 'S', '2023-S2', '2'),
            ('DF', 'S', '2024-S1', '3'),  # should be removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-S2')
        assert '2024-S1' not in result
        assert '2023-S2' in result

    def test_semester_mid_year_end_period(self):
        """S1 end_period should exclude S2 of the same year."""
        tsv = _make_tsv(
            HEADER,
            ('DF', 'S', '2023-S1', '1'),
            ('DF', 'S', '2023-S2', '2'),  # removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023-S1')
        assert '2023-S2' not in result
        assert '2023-S1' in result

    # ------------------------------------------------------------------
    # Unparseable TIME_PERIOD rows are kept
    # ------------------------------------------------------------------

    def test_unparseable_row_kept(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'A', 'UNKNOWN', '1'),
            ('DF', 'A', '2025', '2'),  # removed
        )
        result = filter_tsv_by_time_period(tsv, None, '2023')
        assert 'UNKNOWN' in result
        assert '2025' not in result

    # ------------------------------------------------------------------
    # Unparseable start/end periods → skip that bound, log warning
    # ------------------------------------------------------------------

    def test_unparseable_end_period_skips_end_filter(self):
        tsv = _make_tsv(
            HEADER,
            ('DF', 'A', '2025', '1'),
            ('DF', 'A', '2026', '2'),
        )
        # With an unparseable end_period, only start filtering would apply
        result = filter_tsv_by_time_period(tsv, '2025', 'bad-end')
        # 2026 row should still be present because end_period can't be parsed
        assert '2026' in result

    # ------------------------------------------------------------------
    # Rows with short/missing columns are kept
    # ------------------------------------------------------------------

    def test_row_with_too_few_columns_kept(self):
        tsv = '\t'.join(HEADER) + '\nDF\tA'  # only 2 columns, TIME_PERIOD at idx 2 missing
        result = filter_tsv_by_time_period(tsv, None, '2023')
        assert 'DF\tA' in result
