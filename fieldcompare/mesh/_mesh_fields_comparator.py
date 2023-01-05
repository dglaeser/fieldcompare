"""Comparator for mesh field data"""

from typing import Callable

from ..predicates import DefaultEquality
from . import protocols as mesh_protocols
from ._transformations import strip_orphan_points, sort_points, sort_cells
from .._field_data_comparison import (
    FieldDataComparator,
    PredicateSelector,
    FieldComparisonCallback,
    FieldComparisonSuite,
    DefaultFieldComparisonCallback
)


class MeshFieldsComparator:
    """
    Compares all fields in two given instances of :class:`.mesh_protocols.MeshFields`.
    Per default, this comparator implementation compares the data on sorted meshes.

    Args:
        source: Mesh field data to be compared.
        reference: Reference mesh field data to compare against.
        disable_orphan_point_removal: If true, unconnected points are included in reordered meshes.
        field_inclusion_filter: Filter to select the fields to be compared (optional).
        field_exclusion_filter: Filter to exclude fields from being compared (optional).
    """
    def __init__(self,
                 source: mesh_protocols.MeshFields,
                 reference: mesh_protocols.MeshFields,
                 disable_orphan_point_removal: bool = False,
                 field_inclusion_filter: Callable[[str], bool] = lambda _: True,
                 field_exclusion_filter: Callable[[str], bool] = lambda _: False) -> None:
        self._disable_orphan_point_removal = disable_orphan_point_removal
        self._source = source
        self._reference = reference
        self._field_inclusion_filter = field_inclusion_filter
        self._field_exclusion_filter = field_exclusion_filter

    def __call__(self,
                 predicate_selector: PredicateSelector = lambda _, __: DefaultEquality(),
                 fieldcomp_callback: FieldComparisonCallback = DefaultFieldComparisonCallback(),
                 reordering_callback: Callable[[str], None] = lambda _: None) -> FieldComparisonSuite:
        """
        Compare all fields in the mesh field data objects using the given predicates.

        Args:
            predicate_selector: Selector function taking the two fields to be compared,
                                returning a predicate to be used for comparing the field values.
                                Default: :class:`.DefaultEquality`.
            fieldcomp_callback: Function that is invoked with the results of individual
                                field comparison results as soon as they are available (e.g. to
                                print intermediate output). Defaults to :class:`.DefaultFieldComparisonCallback`.
            reordering_callback: Function that is invoked with status messages about the reordering
                                 steps that are performed. Default: no-op lambda.
        """
        suite = self._make_comparator()(predicate_selector, fieldcomp_callback)
        if suite.domain_equality_check:
            return suite

        reordering_callback("Meshes did not compare equal. Retrying with sorted points...")
        def _permute(mesh_fields):
            if not self._disable_orphan_point_removal:
                mesh_fields = strip_orphan_points(mesh_fields)
            return sort_points(mesh_fields)
        self._source = _permute(self._source)
        self._reference = _permute(self._reference)
        suite = self._make_comparator()(predicate_selector, fieldcomp_callback)
        if suite.domain_equality_check:
            return suite

        reordering_callback("Meshes did not compare equal. Retrying with sorted cells...")
        self._source = sort_cells(self._source)
        self._reference = sort_cells(self._reference)
        return self._make_comparator()(predicate_selector, fieldcomp_callback)

    def _make_comparator(self) -> FieldDataComparator:
        return FieldDataComparator(
            self._source,
            self._reference,
            field_inclusion_filter=self._field_inclusion_filter,
            field_exclusion_filter=self._field_exclusion_filter
        )
