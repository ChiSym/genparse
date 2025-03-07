from collections import defaultdict as dd
from itertools import chain

import networkx as nx

from genparse import CFG, EOS, Float, EPSILON
from genparse.parse.earley import Earley


class LL1:
    def __init__(self, cfg):
        # assert (
        #    not cfg.has_nullary()
        # )  # TODO: enable nullary production + add assertion for LL1 grammars
        self.cfg = cfg

        # Build the left dependency graph
        self.L = nx.DiGraph()
        for r in self.cfg:
            if r.body:
                self.L.add_edge(r.head, r.body[0])
            else:
                self.L.add_edge(r.head, EPSILON)

        for X in chain(cfg.N, cfg.V):
            self.L.add_node(X)

        # Build the First table: FIRST[X] contains all the terminal symbols
        # 'a' such that X=*=> 'a'α
        self.FIRST = dd(set)
        for X in chain(cfg.N, cfg.V):
            for a in cfg.V:
                if nx.has_path(self.L, X, a):
                    self.FIRST[X].add(a)

        # Build the parsing table: TABLE[X][a] contains the first production rule used
        # in a derivation X=*=> 'a'α  (if there is one)
        self.TABLE = dd(lambda: dd(lambda: None))
        for r in cfg:
            for a in self.FIRST[r.body[0]]:
                self.TABLE[r.head][a] = r

    def parse(self, x):
        """The LL(1) parser works like a push down automaton, where the input
        is the input string, the stack contains terminal snd nonterminal symbols
        and the transitions are specified by the parsing table"""

        Input = x + EOS
        stack = [EOS, self.cfg.S]

        i = 0
        weight = self.cfg.R.one

        while stack:
            top = stack[-1]
            curr = Input[i]

            if top == curr:
                i += 1
                stack.pop()

            else:
                if not self.TABLE[top][curr]:
                    assert False, f'the string is not accepted: top={top} curr={curr}'
                r = self.TABLE[top][curr]
                stack.pop()
                stack.extend(r.body[::-1])
                weight *= r.w

        return weight


def assert_equal(have, want, tol=1e-10):
    if isinstance(have, (float, int)):
        error = Float.metric(have, want)
    else:
        error = have.metric(want)
    assert error <= tol, f'have = {have}, want = {want}, error = {error}'


def test_basics():
    cfg = CFG.from_string(
        """
    0.7: S → A T
    1 : T → S B
    0.3 : S → c
    1 : A → a
    1 : B → b
    """,
        Float,
    )

    x = 'aaaacbbbb'

    ll1 = LL1(cfg)
    earley = Earley(cfg)

    ll1_parse = ll1.parse(x)
    earley_parse = earley(x)

    assert_equal(ll1_parse, earley_parse)


if __name__ == '__main__':
    from arsenal import testing_framework

    testing_framework(globals())
