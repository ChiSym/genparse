import pytest
import pdb
from ambiguous_parsing.tree.formula import FOLFormula, LispFormula
from ambiguous_parsing.generation.generate_pairs import (
    generate_pp_pairs,
    generate_unambiguous_pp,
    generate_scope_pairs,
    generate_reverse_scope_pairs,
    generate_unambiguous_scope,
    generate_conjunction_pairs,
    generate_unambiguous_conj,
    generate_bound_pronoun_pairs,
    generate_unambigous_bound_pronoun,
    generate_unambiguous_basic,
)


@pytest.fixture
def load_pp_pairs():
    pp_pairs = generate_pp_pairs()
    unambig_pp = generate_unambiguous_pp()
    return pp_pairs + unambig_pp


@pytest.fixture
def load_scope_pairs():
    scope_pairs = generate_scope_pairs()
    reverse_scope_pairs = generate_reverse_scope_pairs()
    unambig_scope = generate_unambiguous_scope()
    return scope_pairs + reverse_scope_pairs + unambig_scope


@pytest.fixture
def load_conj_pairs():
    conj_pairs = generate_conjunction_pairs()
    unambig_conj = generate_unambiguous_conj()
    return conj_pairs + unambig_conj


@pytest.fixture
def load_bound_pairs():
    bound_pairs = generate_bound_pronoun_pairs(
        is_female=True
    ) + generate_bound_pronoun_pairs(is_female=False)
    unambig_bound = generate_unambigous_bound_pronoun(
        is_female=True
    ) + generate_unambigous_bound_pronoun(is_female=False)
    return bound_pairs + unambig_bound


@pytest.fixture
def load_unambiguous():
    unambiguous = generate_unambiguous_basic()
    return unambiguous


def check_fol_roundtrip(formula_str, ordered=False):
    formula_obj = FOLFormula.parse_formula(formula_str)
    generated_str_1 = formula_obj.render(ordered_vars=ordered)
    formula_obj_2 = FOLFormula.parse_formula(generated_str_1)
    generated_str_2 = formula_obj_2.render(ordered_vars=ordered)
    assert generated_str_1 == generated_str_2


def check_fol_roundtrip_via_lisp(formula_str, ordered=True):
    formula_obj = FOLFormula.parse_formula(formula_str)
    generated_str_1 = formula_obj.render(ordered_vars=ordered)
    # roundtrip once to anonymize
    formula_obj = FOLFormula.parse_formula(generated_str_1)
    generated_str_1 = formula_obj.render(ordered_vars=ordered)

    lisp_obj = LispFormula.from_formula(formula_obj)
    lisp_str = lisp_obj.render(ordered_vars=ordered)
    lisp_obj_2 = LispFormula.parse_formula(lisp_str)

    formula_obj_2 = FOLFormula.from_formula(lisp_obj_2)
    generated_str_2 = formula_obj_2.render(ordered_vars=ordered)
    assert generated_str_1 == generated_str_2


def test_fol():
    fol_str = 'exists x . exists a . exists e . spyglass(x) AND observed(a) AND agent(a, Ada) AND instrument(a, x)'
    check_fol_roundtrip(fol_str)
    check_fol_roundtrip(fol_str, ordered=True)


def test_conj_trouble():
    fol_str = 'exists x . exists a . exists e . exists i . bird(x) AND ate(a) AND agent(a, x) AND ( ( drank(e) AND agent(e, x) ) OR ( slept(i) AND agent(i, x) ) )'
    check_fol_roundtrip(fol_str)
    check_fol_roundtrip(fol_str, ordered=True)


def test_pp_pairs(load_pp_pairs):
    for pair in load_pp_pairs:
        check_fol_roundtrip(pair['lf'])
        check_fol_roundtrip(pair['lf'], ordered=True)


def test_scope_pairs(load_scope_pairs):
    for pair in load_scope_pairs:
        check_fol_roundtrip(pair['lf'])
        check_fol_roundtrip(pair['lf'], ordered=True)


def test_conj_pairs(load_conj_pairs):
    for pair in load_conj_pairs:
        check_fol_roundtrip(pair['lf'])
        check_fol_roundtrip(pair['lf'], ordered=True)


def test_bound_pairs(load_bound_pairs):
    for pair in load_bound_pairs:
        check_fol_roundtrip(pair['lf'])
        check_fol_roundtrip(pair['lf'], ordered=True)


def test_unambiguous(load_unambiguous):
    for pair in load_unambiguous:
        check_fol_roundtrip(pair['lf'])
        check_fol_roundtrip(pair['lf'], ordered=True)


def test_pp_pairs_lisp(load_pp_pairs):
    for pair in load_pp_pairs:
        check_fol_roundtrip_via_lisp(pair['lf'])
        check_fol_roundtrip_via_lisp(pair['lf'], ordered=True)


def test_scope_pairs_lisp(load_scope_pairs):
    for pair in load_scope_pairs:
        check_fol_roundtrip_via_lisp(pair['lf'])
        check_fol_roundtrip_via_lisp(pair['lf'], ordered=True)


def test_conj_pairs_lisp(load_conj_pairs):
    for pair in load_conj_pairs:
        check_fol_roundtrip_via_lisp(pair['lf'])
        check_fol_roundtrip_via_lisp(pair['lf'], ordered=True)


def test_bound_pairs_lisp(load_bound_pairs):
    for pair in load_bound_pairs:
        check_fol_roundtrip_via_lisp(pair['lf'])
        check_fol_roundtrip_via_lisp(pair['lf'], ordered=True)


def test_unambiguous_lisp(load_unambiguous):
    for pair in load_unambiguous:
        check_fol_roundtrip_via_lisp(pair['lf'])
        check_fol_roundtrip_via_lisp(pair['lf'], ordered=True)
