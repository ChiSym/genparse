from example_grammars import arith, iql_small

from genparse import locally_normalize
from genparse.parse.earley import EarleyLM
from genparse.proposal import CharacterProposal, TokenProposal
from genparse.util import set_seed, load_model_by_name
from genparse.lark_interface import LarkStuff


def test_token_arith():
    set_seed(0)

    llm = load_model_by_name('mock-gpt2')

    cfg = locally_normalize(LarkStuff(arith, cnf=False).char_cfg(), tol=1e-100).trim()

    guide = EarleyLM(cfg)

    proposal = TokenProposal(guide=guide, llm=llm, K=5)

    samples = []
    for _ in range(10):
        samples.append(proposal.sample(prompt=(), max_tokens=100, verbosity=1))
        print(samples[-1])


def test_character_arith():
    set_seed(0)

    llm = load_model_by_name('mock-gpt2')

    cfg = locally_normalize(LarkStuff(arith, cnf=False).char_cfg(), tol=1e-100).trim()

    guide = EarleyLM(cfg)

    proposal = CharacterProposal(llm=llm, guide=guide)

    samples = []
    for _ in range(10):
        samples.append(proposal.sample(prompt=(), max_tokens=100, verbosity=1))
        print(samples[-1])


def test_token_iql_small():
    set_seed(0)

    llm = load_model_by_name('mock-gpt2')

    cfg = locally_normalize(LarkStuff(iql_small, cnf=False).char_cfg(), tol=1e-100).trim()

    guide = EarleyLM(cfg)

    proposal = TokenProposal(llm=llm, guide=guide, K=5)

    samples = []
    for _ in range(10):
        samples.append(proposal.sample(max_tokens=100))
        print(samples[-1])


def test_character_iql_small():
    set_seed(0)

    llm = load_model_by_name('mock-gpt2')

    cfg = locally_normalize(LarkStuff(iql_small, cnf=False).char_cfg(), tol=1e-100).trim()

    guide = EarleyLM(cfg)

    proposal = CharacterProposal(llm=llm, guide=guide)

    samples = []
    for _ in range(10):
        samples.append(proposal.sample(prompt=(), max_tokens=100, verbosity=1))
        print(samples[-1])


if __name__ == '__main__':
    from arsenal import testing_framework

    testing_framework(globals())
