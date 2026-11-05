"""Independent, stdlib-only verifier for pinned CheckM2 membership semantics.

No I/O or scientific imports. The owner must verify the original JSON assets and
saved raw KO columns before passing them here. Original CheckM2 code/data and
notices remain unchanged in the project package cache. This computes expected
values for validation; it never clips or rewrites a saved feature vector.
"""
import math


def _integer_count(value):
    if hasattr(value, 'item'):
        value = value.item()
    if type(value) is int:
        if value < 0:
            raise ValueError('Negative raw KO count')
        return value
    if type(value) is float and math.isfinite(value) and value >= 0 and value.is_integer():
        # Above this bound a float cannot establish the original integer count.
        if value > 2**53:
            raise ValueError('Raw KO integer precision cannot be established from float')
        return int(value)
    raise ValueError('Raw KO count must be finite, nonnegative and integral; bool is invalid')


def recompute_membership_features(raw_ko_counts, feature_order,
                                  path_category_mapping, module_definitions):
    """Return ordered {feature: expected_float} for pathway/module/category.

    Pathways/categories are clipped-presence proportions over mapping ROWS.
    Modules use RAW counts over original membership OCCURRENCES; their original
    list length remains the denominator even when unknown KO IDs are excluded.
    Complete raw KO columns are mandatory: a missing known column is not zero.
    """
    genes = list(feature_order['KO_Genes'])
    if len(genes) != len(set(genes)) or set(raw_ko_counts) != set(genes):
        raise ValueError('Raw KO count keys must exactly match all original KO columns')
    counts = {name: _integer_count(raw_ko_counts[name]) for name in genes}
    if list(module_definitions) != list(feature_order['KO_Modules']):
        raise ValueError('Original module-definition order differs from feature order')
    ids = path_category_mapping['Kegg_ID']
    grouped = {}
    for group in ('KO_Pathways', 'KO_Categories'):
        labels = path_category_mapping[group]
        if set(labels) != set(ids):
            raise ValueError('Mapping columns must have the same original row IDs')
        names = list(feature_order[group])
        if len(names) != len(set(names)):
            raise ValueError('Duplicate group feature name')
        members = {name: [] for name in names}
        for row, label in labels.items():
            if label in members:
                ko = ids[row]
                if ko not in counts:
                    raise ValueError('Mapping references a missing original KO column')
                members[label].append(ko)
        values = {}
        for name in names:
            occurrence_list = members[name]
            if not occurrence_list:
                raise ValueError('Original pathway/category denominator is zero')
            values[name] = sum(min(counts[ko], 1) for ko in occurrence_list) / len(occurrence_list)
        grouped[group] = values
    modules = {}
    for name, original_members in module_definitions.items():
        denominator = len(original_members)
        if not denominator:
            raise ValueError('Original module denominator is zero')
        # Exact producer behavior at keggData.py:69,72,74. Do not deduplicate,
        # do not use the clipped temporary, and do not shrink the denominator.
        modules[name] = sum(counts[ko] for ko in original_members if ko in counts) / denominator
    expected = {}
    for block in (grouped['KO_Pathways'], modules, grouped['KO_Categories']):
        for name, value in block.items():
            if name in expected or not math.isfinite(value) or value < 0:
                raise ValueError('Duplicate or invalid recomputed membership feature')
            expected[name] = value
    return expected
