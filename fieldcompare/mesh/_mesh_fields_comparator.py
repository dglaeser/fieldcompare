# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Comparator for mesh field data"""

from typing import Callable, Optional

from ..predicates import DefaultEquality
from . import protocols as mesh_protocols
from ._structured_mesh import StructuredMesh
from ._transformations import strip_orphan_points, sort_points, sort_cells, extend_space_dimension_to
from .._field_data_comparison import (
    FieldDataComparator,
    PredicateSelector,
    FieldComparisonCallback,
    FieldComparisonSuite,
    DefaultFieldComparisonCallback,
)


class MeshFieldsComparator:
    """
    Compares all fields in two given instances of :class:`.mesh_protocols.MeshFields`.
    Per default, this comparator implementation compares the data on sorted meshes.

    Args:
        source: Mesh field data to be compared.
        reference: Reference mesh field data to compare against.
        disable_mesh_reordering: If true, no attempt is made to pass the domain equality check with reordered meshes.
        disable_orphan_point_removal: If true, unconnected points are included in reordered meshes.
        disable_space_dimension_matching: If true, not attempt is made to pass the domain equality
                                          check by making the space dimensions of the two meshes match.
        field_inclusion_filter: Filter to select the fields to be compared (optional).
        field_exclusion_filter: Filter to exclude fields from being compared (optional).
    """

    def __init__(  # noqa: PLR0913
        self,
        source: mesh_protocols.MeshFields,
        reference: mesh_protocols.MeshFields,
        disable_mesh_reordering: bool = False,
        disable_orphan_point_removal: bool = False,
        disable_space_dimension_matching: bool = False,
        field_inclusion_filter: Callable[[str], bool] = lambda _: True,
        field_exclusion_filter: Callable[[str], bool] = lambda _: False,
    ) -> None:
        self._disable_mesh_reordering = disable_mesh_reordering
        self._disable_orphan_point_removal = disable_orphan_point_removal
        self._disable_space_dimension_matching = disable_space_dimension_matching
        self._source = source
        self._reference = reference
        self._field_inclusion_filter = field_inclusion_filter
        self._field_exclusion_filter = field_exclusion_filter

    def __call__(
        self,
        predicate_selector: Optional[PredicateSelector] = None,
        fieldcomp_callback: Optional[FieldComparisonCallback] = None,
        reordering_callback: Callable[[str], None] = lambda _: None,
    ) -> FieldComparisonSuite:
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

        def _default_predicate_selector(*_, **__):
            return DefaultEquality()

        predicate_selector = predicate_selector or _default_predicate_selector
        fieldcomp_callback = fieldcomp_callback or DefaultFieldComparisonCallback()
        suite = self._run_comparison(predicate_selector, fieldcomp_callback)
        if suite.domain_equality_check:
            return suite

        # (maybe) retry with matching space dimension
        space_dim_source = self._source.domain.points.shape[1]
        space_dim_target = self._reference.domain.points.shape[1]
        if space_dim_source != space_dim_target and not self._disable_space_dimension_matching:
            reordering_callback(self._mesh_fail_msg(suite.domain_equality_check.report, "extended points"))
            max_dim = max(space_dim_source, space_dim_target)
            self._source = extend_space_dimension_to(max_dim, self._source)
            self._reference = extend_space_dimension_to(max_dim, self._reference)
            suite = self._run_comparison(predicate_selector, fieldcomp_callback)
            if suite.domain_equality_check:
                return suite

        # (maybe) retry with sorted meshes
        if (
            not self._disable_mesh_reordering
            and isinstance(self._source.domain, StructuredMesh)
            and isinstance(self._reference.domain, StructuredMesh)
        ):
            reordering_callback("Skipping mesh reordering because both meshes are structured")
        elif not self._disable_mesh_reordering:
            # sorted points
            reordering_callback(self._mesh_fail_msg(suite.domain_equality_check.report, "sorted points"))

            def _permute(mesh_fields):
                if not self._disable_orphan_point_removal:
                    mesh_fields = strip_orphan_points(mesh_fields)
                return sort_points(mesh_fields)

            self._source = _permute(self._source)
            self._reference = _permute(self._reference)
            suite = self._run_comparison(predicate_selector, fieldcomp_callback)
            if suite.domain_equality_check:
                return suite

            # sorted cells
            reordering_callback(self._mesh_fail_msg(suite.domain_equality_check.report, "sorted cells"))
            self._source = sort_cells(self._source)
            self._reference = sort_cells(self._reference)
            suite = self._run_comparison(predicate_selector, fieldcomp_callback)
        if not suite.domain_equality_check:
            reordering_callback(self._mesh_fail_msg(suite.domain_equality_check.report))
        return suite

    def _mesh_fail_msg(self, predicate_report: str, retry_measure: str = "") -> str:
        return f"Meshes did not compare equal ({predicate_report})" + (
            f". Retrying with {retry_measure}..." if retry_measure else ""
        )

    def _run_comparison(
        self, predicate_selector: PredicateSelector, fieldcomp_callback: FieldComparisonCallback
    ) -> FieldComparisonSuite:
        return self._make_comparator()(predicate_selector, fieldcomp_callback)

    def _make_comparator(self) -> FieldDataComparator:
        return FieldDataComparator(
            self._source,
            self._reference,
            field_inclusion_filter=self._field_inclusion_filter,
            field_exclusion_filter=self._field_exclusion_filter,
        )
