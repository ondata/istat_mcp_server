"""Blacklist manager for filtering dataflows."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DataflowBlacklist:
    """Manager for dataflow ID blacklist."""

    def __init__(self, blacklist_ids: list[str] | None = None):
        """Initialize blacklist.

        Args:
            blacklist_ids: List of dataflow IDs to exclude. If None, loads from environment.
        """
        if blacklist_ids is None:
            blacklist_ids = self._load_from_env()

        self._blacklist = set(blacklist_ids)

        if self._blacklist:
            logger.info(f'Blacklist initialized with {len(self._blacklist)} dataflow(s): {sorted(self._blacklist)}')
        else:
            logger.info('Blacklist is empty')

    def _load_from_env(self) -> list[str]:
        """Load blacklist from DATAFLOW_BLACKLIST environment variable.

        Expected format: comma-separated list of dataflow IDs
        Example: "149_577_DF_DCSC_OROS_1_1,22_315_DF_DCIS_POPORESBIL1_2"

        Returns:
            List of blacklisted dataflow IDs
        """
        blacklist_str = os.getenv('DATAFLOW_BLACKLIST', '').strip()

        if not blacklist_str:
            return []

        # Split by comma and clean whitespace
        ids = [id_.strip() for id_ in blacklist_str.split(',') if id_.strip()]
        logger.info(f'Loaded blacklist from environment: {ids}')
        return ids

    def is_blacklisted(self, dataflow_id: str) -> bool:
        """Check if a dataflow ID is blacklisted.

        Args:
            dataflow_id: Dataflow ID to check

        Returns:
            True if blacklisted, False otherwise
        """
        return dataflow_id in self._blacklist

    def filter_dataflows(self, dataflows: list[Any]) -> list[Any]:
        """Filter out blacklisted dataflows.

        Args:
            dataflows: List of dataflow objects (must have 'id' attribute)

        Returns:
            Filtered list without blacklisted dataflows
        """
        if not self._blacklist:
            return dataflows

        original_count = len(dataflows)
        filtered = [df for df in dataflows if not self.is_blacklisted(df.id)]
        filtered_count = original_count - len(filtered)

        if filtered_count > 0:
            logger.info(f'Filtered out {filtered_count} blacklisted dataflow(s)')

        return filtered

    def get_blacklisted_ids(self) -> set[str]:
        """Get the set of blacklisted IDs.

        Returns:
            Set of blacklisted dataflow IDs
        """
        return self._blacklist.copy()

    def add_to_blacklist(self, dataflow_id: str) -> None:
        """Add a dataflow ID to the blacklist.

        Args:
            dataflow_id: Dataflow ID to blacklist
        """
        if dataflow_id not in self._blacklist:
            self._blacklist.add(dataflow_id)
            logger.info(f'Added to blacklist: {dataflow_id}')

    def remove_from_blacklist(self, dataflow_id: str) -> None:
        """Remove a dataflow ID from the blacklist.

        Args:
            dataflow_id: Dataflow ID to remove
        """
        if dataflow_id in self._blacklist:
            self._blacklist.remove(dataflow_id)
            logger.info(f'Removed from blacklist: {dataflow_id}')
