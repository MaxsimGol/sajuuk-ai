# core/interfaces/build_order_abc.py

from abc import ABC, abstractmethod
from collections.abc import Iterator
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# A production goal is a tuple of (supply_trigger, item_to_build)
BuildStep = tuple[int, UnitTypeId | UpgradeId]


class BuildOrder(ABC):
    """
    Defines the abstract contract for a build order strategy.
    It must be iterable to yield production goals (BuildStep).
    """

    @abstractmethod
    def __iter__(self) -> Iterator[BuildStep]:
        """
        Yields the build order steps one by one.

        Each yielded step is a 'BuildStep', which is a tuple containing:
        (supply_trigger, item_to_build)

        - supply_trigger (int): The supply count at which this step should be executed.
        - item_to_build (UnitTypeId | UpgradeId): The unit or upgrade to produce.
        """
        raise NotImplementedError
