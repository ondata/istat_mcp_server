"""Tests for dataflow blacklist functionality."""

import os
from unittest.mock import patch

from istat_mcp_server.api.models import DataflowInfo
from istat_mcp_server.utils.blacklist import DataflowBlacklist


class TestDataflowBlacklist:
    """Test suite for DataflowBlacklist class."""

    def test_init_empty(self):
        """Test initialization with empty blacklist."""
        blacklist = DataflowBlacklist([])
        assert len(blacklist.get_blacklisted_ids()) == 0

    def test_init_with_ids(self):
        """Test initialization with specific IDs."""
        ids = ['DF_123', 'DF_456']
        blacklist = DataflowBlacklist(ids)
        assert blacklist.get_blacklisted_ids() == set(ids)

    def test_is_blacklisted(self):
        """Test checking if a dataflow is blacklisted."""
        blacklist = DataflowBlacklist(['DF_123', 'DF_456'])
        assert blacklist.is_blacklisted('DF_123') is True
        assert blacklist.is_blacklisted('DF_789') is False

    def test_filter_dataflows(self):
        """Test filtering a list of dataflows."""
        dataflows = [
            DataflowInfo(
                id='DF_123',
                name_it='Test 1',
                name_en='Test 1',
                description_it='',
                description_en='',
                id_datastructure='DS_1',
                agency='IT1',
                version='1.0',
            ),
            DataflowInfo(
                id='DF_456',
                name_it='Test 2',
                name_en='Test 2',
                description_it='',
                description_en='',
                id_datastructure='DS_2',
                agency='IT1',
                version='1.0',
            ),
            DataflowInfo(
                id='DF_789',
                name_it='Test 3',
                name_en='Test 3',
                description_it='',
                description_en='',
                id_datastructure='DS_3',
                agency='IT1',
                version='1.0',
            ),
        ]

        blacklist = DataflowBlacklist(['DF_123', 'DF_456'])
        filtered = blacklist.filter_dataflows(dataflows)

        assert len(filtered) == 1
        assert filtered[0].id == 'DF_789'

    def test_filter_dataflows_empty_blacklist(self):
        """Test filtering with empty blacklist returns all dataflows."""
        dataflows = [
            DataflowInfo(
                id='DF_123',
                name_it='Test 1',
                name_en='Test 1',
                description_it='',
                description_en='',
                id_datastructure='DS_1',
                agency='IT1',
                version='1.0',
            ),
        ]

        blacklist = DataflowBlacklist([])
        filtered = blacklist.filter_dataflows(dataflows)

        assert len(filtered) == 1
        assert filtered[0].id == 'DF_123'

    def test_add_to_blacklist(self):
        """Test adding an ID to the blacklist."""
        blacklist = DataflowBlacklist(['DF_123'])
        assert len(blacklist.get_blacklisted_ids()) == 1

        blacklist.add_to_blacklist('DF_456')
        assert len(blacklist.get_blacklisted_ids()) == 2
        assert blacklist.is_blacklisted('DF_456') is True

    def test_remove_from_blacklist(self):
        """Test removing an ID from the blacklist."""
        blacklist = DataflowBlacklist(['DF_123', 'DF_456'])
        assert len(blacklist.get_blacklisted_ids()) == 2

        blacklist.remove_from_blacklist('DF_123')
        assert len(blacklist.get_blacklisted_ids()) == 1
        assert blacklist.is_blacklisted('DF_123') is False
        assert blacklist.is_blacklisted('DF_456') is True

    def test_load_from_env_empty(self):
        """Test loading from empty environment variable."""
        with patch.dict(os.environ, {'DATAFLOW_BLACKLIST': ''}, clear=False):
            blacklist = DataflowBlacklist()
            assert len(blacklist.get_blacklisted_ids()) == 0

    def test_load_from_env_single(self):
        """Test loading single ID from environment."""
        with patch.dict(os.environ, {'DATAFLOW_BLACKLIST': 'DF_123'}, clear=False):
            blacklist = DataflowBlacklist()
            assert len(blacklist.get_blacklisted_ids()) == 1
            assert blacklist.is_blacklisted('DF_123') is True

    def test_load_from_env_multiple(self):
        """Test loading multiple IDs from environment."""
        with patch.dict(
            os.environ, {'DATAFLOW_BLACKLIST': 'DF_123,DF_456,DF_789'}, clear=False
        ):
            blacklist = DataflowBlacklist()
            assert len(blacklist.get_blacklisted_ids()) == 3
            assert blacklist.is_blacklisted('DF_123') is True
            assert blacklist.is_blacklisted('DF_456') is True
            assert blacklist.is_blacklisted('DF_789') is True

    def test_load_from_env_whitespace(self):
        """Test loading with whitespace handling."""
        with patch.dict(
            os.environ, {'DATAFLOW_BLACKLIST': ' DF_123 , DF_456 , DF_789 '}, clear=False
        ):
            blacklist = DataflowBlacklist()
            assert len(blacklist.get_blacklisted_ids()) == 3
            assert blacklist.is_blacklisted('DF_123') is True
            assert blacklist.is_blacklisted('DF_456') is True
            assert blacklist.is_blacklisted('DF_789') is True

    def test_get_blacklisted_ids_returns_copy(self):
        """Test that get_blacklisted_ids returns a copy, not the original set."""
        blacklist = DataflowBlacklist(['DF_123'])
        ids = blacklist.get_blacklisted_ids()
        ids.add('DF_456')

        # Original blacklist should not be modified
        assert len(blacklist.get_blacklisted_ids()) == 1
        assert blacklist.is_blacklisted('DF_456') is False
