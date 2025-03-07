from setuptools import setup

requirements = [
    'arsenal @ git+https://github.com/timvieira/arsenal',
    'frozendict',
    'graphviz',  # for notebook visualizations
    #'greenery>=4.2.1',
    'interegular',
    #'hfppl @ git+https://github.com/probcomp/hfppl',
    'IPython',
    'jsons',  # for spider benchmarking
    'lark',
    'nltk',
    #'svgling',  # nltk uses svgling to draw derivations
    'numpy',
    'pandas',
    'path',
    'rich',
    'numba',
    'torch',
    'transformers',
    'plotly',
    'maturin',  # for rust parser
    'psutil',
    'mkdocs',
    'mkdocs-material',
]

test_requirements = [
    'coverage',
    #'memory-profiler',
    'pdoc',
    'pre-commit',
    'pytest',
    'pytest-html',
    'pytest-benchmark',
    'ruff',
]

setup(
    name='genparse',
    version='0.0.2',
    description='',
    install_requires=requirements,
    extras_require={'test': test_requirements, 'vllm': ['vllm==0.5.0.post1']},
    python_requires='>=3.10',
    authors=[
        'Tim Vieira',
        'Clemente Pasti',
        'Ben LeBrun',
        'Ben Lipkin',
    ],
    readme=open('README.md', encoding='utf-8').read(),
    scripts=[],
    packages=['genparse'],
)
