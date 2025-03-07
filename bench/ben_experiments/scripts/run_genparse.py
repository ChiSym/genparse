#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################
# Runs genparse on spider dataset #
###################################

import os
import time
import json
import psutil
import logging
import argparse
from tqdm import tqdm
from pathlib import Path
import multiprocessing as mp

from bench.cache import ProposalCache
from bench.spider.evaluator import Evaluator
from utils import (
    load_spider_data,
    load_prompt_formatter,
    reformat_grammar,
    HF_ACCESS_TOKEN,
    mbr_eval,
    posterior_weighted_eval,
    viterbi_eval,
)

from genparse.util import set_seed
from genparse.experimental.batch_inference import (
    BatchVLLM,
    BatchStepModel,
    smc,
    importance_sampling,
)
from genparse.experimental.batch_inference.steer import ParticleApproximation, Particle

os.environ['TOKENIZERS_PARALLELISM'] = '(true | false)'
os.environ['HF_TOKEN'] = HF_ACCESS_TOKEN

logger = logging.getLogger(__name__)


def int_or_none(value):
    if value == 'None':
        return None
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid integer value: {value}')


def get_argparser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--model-name', type=str, default='meta-llama/Meta-Llama-3-8B-Instruct'
    )
    parser.add_argument('--exp-name', type=str)
    parser.add_argument('--particles', type=int, default=1)
    parser.add_argument('--max-tokens', type=int, default=100)
    parser.add_argument(
        '--proposal',
        choices=['character', 'token'],
        default='character',
        help='Specify which proposal distribution to use in SMC inference.',
    )
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument(
        '--K',
        type=int_or_none,
        default=0,
        help='Parameter for token proposal.',
    )
    parser.add_argument('--n-processes', type=int_or_none, default=None)
    parser.add_argument('--out-dir', default='', type=str)
    parser.add_argument(
        '--schema',
        type=str,
        help='Schema to evaluate, seperated by commas. Defaults to `all` for all schema.',
        default='all',
    )
    parser.add_argument(
        '--sis',
        action='store_true',
        help='Perform SIS.',
    )
    parser.add_argument('--verbosity', type=int, default=0)
    parser.add_argument('--n_replicates', type=int, default=1)
    parser.add_argument(
        '--max-mem-usage',
        type=int,
        default=70,
        help='Memory usage (as percentage of total memory) at which to trigger memory management strategies.',
    )
    parser.add_argument(
        '--ess-threshold',
        type=float,
        default=0.5,
        help='Effective sample size below which resampling triggered, given as a fraction of `n_particles`.',
    )

    return parser


def make_example_key(schema_name, question):
    return (schema_name, question)


def initialize_output_path(args):
    """Constructs the output path and saves arguments."""
    outpath = os.path.join(
        args.out_dir, f'{args.exp_name}-p{args.particles}-{args.proposal}'
    )

    if args.K != 0:
        outpath += f'-K{args.K}'

    json.dump(vars(args), open(f'{outpath}-args.json', 'w'), indent=4)

    return f'{outpath}.jsonl'


def load_processed_examples(outpath):
    """
    Loads already processed examples if the output file exists.
    Handles JSON decoding errors for existing output file.
    """
    already_processed = []
    valid_lines = []
    do_rewrite = False
    if os.path.exists(outpath):
        with open(outpath, 'r') as file:
            for line in file:
                try:
                    example = json.loads(line)
                    valid_lines.append(example)
                    already_processed.append(
                        make_example_key(example['db_name'], example['question'])
                    )
                except json.JSONDecodeError:
                    do_rewrite = True
                    continue

        if do_rewrite:
            # exclude offending lines
            with open(outpath, 'w') as file:
                for line in valid_lines:
                    print(json.dumps(line), file=file)

        print(f'Found {len(already_processed)} already complete at {outpath}')

    return already_processed


def prepare_schema(args, spider_dev_data):
    """Prepares the schema list for evaluation."""
    if args.schema == 'all':
        schema = list(set([d.schema_name for d in spider_dev_data]))
    else:
        schema = args.schema.split(',')
    print(f'Using schema {",".join(schema)}')

    return schema


def get_proposal_args(K):
    """Returns proposal arguments based on K."""
    if K is None:
        return {'K': K}
    elif isinstance(K, int) and K > 0:
        return {'K': K}
    elif isinstance(K, int) and K == 0:
        return {}
    else:
        raise ValueError(f'Invalid K value: {K}')


def get_n_processes(particles, n_processes):
    """Determines the number of processes to use."""
    if n_processes is None:
        return min(particles, 10, mp.cpu_count() - 1)
    elif isinstance(n_processes, int):
        return n_processes
    else:
        raise ValueError(f'Invalid n_processes value: {n_processes}')


def main():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=os.environ.get('LOGLEVEL', 'INFO').upper(),
    )

    parser = get_argparser()
    args = parser.parse_args()

    if args.sis:
        print('Running SIS: Ignoring ess_threshold argument')
    else:
        print(f'Running SMC with ess_threshold={args.ess_threshold}')

    if args.proposal == 'character':
        print('Using character proposal: Ignoring K argument')
    else:
        print(f'Using token proposal with K={args.K}')

    outpath = initialize_output_path(args)
    already_processed = load_processed_examples(outpath)
    outfile = open(outpath, 'a+')

    raw_spider_dir = Path('../spider/data/spider')
    spider_dev_data = load_spider_data(raw_spider_dir, split='dev')
    prompt_formatter = load_prompt_formatter(raw_spider_dir)

    if len(already_processed) >= (len(spider_dev_data) * args.n_replicates):
        return

    grammar_dir = 'spider_grammars'
    schema = prepare_schema(args, spider_dev_data)

    set_seed(args.seed)

    proposal_cache = ProposalCache(
        guide_cache_path='guide_cache.pkl', maxsize=1, max_mem_usage=args.max_mem_usage
    )
    print(f'Initialized {proposal_cache}')

    n_processes = get_n_processes(args.particles, args.n_processes)
    print(f'Using {n_processes=} for parallel inference')

    proposal_args = get_proposal_args(args.K)

    batch_llm = BatchVLLM.from_name(args.model_name)
    tokenizer = batch_llm.get_tokenizer()

    skipped_schema = []
    for i, dev_datum in tqdm(
        enumerate(spider_dev_data), total=len(spider_dev_data), smoothing=0.0
    ):
        if dev_datum.schema_name not in schema:
            if dev_datum.schema_name not in skipped_schema:
                skipped_schema.append(dev_datum.schema_name)
                print(f'Skipping schema {dev_datum.schema_name}')
            continue

        num_already_processed_ex = already_processed.count(
            make_example_key(dev_datum.schema_name, dev_datum.utterance)
        )

        if num_already_processed_ex >= args.n_replicates:
            print(f'Skipping {i}')
            continue

        messages = prompt_formatter.format_openai(dev_datum)

        grammar = open(
            os.path.join(grammar_dir, f'{dev_datum.schema_name}.lark'), 'r'
        ).read()

        mem_usage = psutil.virtual_memory().percent
        if mem_usage > args.max_mem_usage:
            proposal_cache.clear_cache()
            print()
            print(f'Memory usage greater than max_mem_usage ({args.max_mem_usage}%).')
            print('Evicted proposals from cache:')
            print(f'\t prev_mem_usage={mem_usage}%')
            print(f'\t curr_mem_usage={psutil.virtual_memory().percent}%')

        parallel_proposal = proposal_cache.fetch_or_create_proposal(
            llm=batch_llm.llm,
            grammar=grammar,
            proposal_name=args.proposal,
            n_processes=n_processes,
            proposal_args=proposal_args,
        )

        step_model = BatchStepModel(
            batch_proposal=parallel_proposal,
            batch_llm=batch_llm,
            max_tokens=args.max_tokens,
        )

        prompt = tokenizer.decode(
            tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        )

        step_model.set_prompt(prompt)

        for j in range(0, args.n_replicates - num_already_processed_ex):
            try:
                start_time = time.time()

                if args.sis:
                    particles = importance_sampling(
                        batch_model=step_model,
                        n_particles=args.particles,
                        return_record=True,
                    )
                else:
                    particles = smc(
                        batch_model=step_model,
                        ess_threshold=args.ess_threshold,
                        n_particles=args.particles,
                        return_record=True,
                    )

                end_time = time.time()

            except Exception as e:
                print()
                print(f'Error while running inference run {j} on example {i}')
                print(e)
                print()
                continue

            json_result = {
                'gold': dev_datum.query,
                'db_name': dev_datum.schema_name,
                'question': dev_datum.utterance,
                'record': particles.record,
                'log_ml': particles.log_ml,
                'time': end_time - start_time,
                'results': {},
            }

            print(json.dumps(json_result), file=outfile)

    outfile.close()


if __name__ == '__main__':
    main()
