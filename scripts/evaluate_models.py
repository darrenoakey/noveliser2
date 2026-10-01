#!/usr/bin/env python3
"""Run identical, reproducible creative-writing tasks against an existing Ollama server."""
import argparse
import json
import time
import urllib.request
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent
PREMISE = ("In a late-medieval travelling show, a boy joins a magician expecting real sorcery. "
           "He learns every performer uses sleight of hand, but he alone can do the impossible. "
           "The troupe knows exactly how to spot tricks and would recognize a true impossibility. "
           "No one believes supernatural magic exists. Avoid chosen-one prophecies and instant competence.")
TASKS = {
    "plan": ("Design six CAUSALLY LINKED major turning points for a 12-chapter coming-of-age novel. "
             "For each: goal, obstacle, character choice, immediate cost, consequence that CAUSES the next point, "
             "and an unresolved reader question. Include mentor conflict, a credible wider threat, one setup/payoff, "
             "and a relationship changed by the hero's choice. No formulas or vague 'stakes rise'. "
             "Preserve all premise constraints. 450-650 words.\n\nPREMISE: " + PREMISE),
    "continuity": ("Write 850-1050 words of finished third-person limited prose continuing the established canon. "
                   "CANON: Tavi is 14, spent a month with illusionist Orin and apprentice Rhea; no one accepts "
                   "real supernatural magic. In a townhouse performance Tavi made a copper coin pass through "
                   "sealed glass, permanently losing feeling in his index and middle fingers. Rhea alone saw "
                   "the intact seal, and chose to conceal it but now mistrusts Tavi's lie. Orin has not been "
                   "convinced and insists there is an apparatus he has not found. He taught Tavi the practical "
                   "double-bottomed cup and false knot. A week ago Rhea tied a distinctive red thread around "
                   "the weak hinge of their wagon door so it would not swing in wind. Tonight a magistrate's "
                   "men search the travelling troupe for counterfeit coins. Tavi must try to keep the troupe's "
                   "legitimate coin box out of sight without using magic in front of Orin, but his numb fingers "
                   "make the familiar false knot slip. Rhea pursues her own goal: save her mother's signed "
                   "contract from seizure. Make a hard choice with an irreversible, specific cost. Use the red "
                   "thread causally, not as an arbitrary symbol. No healed fingers, other wizards, prophecy, "
                   "explanation of magic, spontaneous time jump, purple prose, or stock cliffhanger. Distinct "
                   "voices and subtext in dialogue; narrative only, no title.\n\nPREMISE: " + PREMISE),
    "prose": ("Write 600-800 words of finished third-person limited prose. The boy (Tavi, 14) has spent "
              "three days with travelling illusionist Orin and knows the double-bottomed cup trick. In a packed "
              "townhouse Orin asks him to assist. Tavi makes a real copper coin pass through sealed glass without "
              "meaning to; it has a physical price (loss of feeling in two fingers). Orin is an exacting, unsentimental "
              "mentor who knows tricks, not real magic. Rhea, a skeptical apprentice his own age, sees one impossible "
              "detail but is unsure. Tavi must choose between covering it up and risking Rhea's trust. End with an "
              "irreversible, concrete consequence rather than a trailer-like cliffhanger. No prophecy, no explanation "
              "of magical system, no purple metaphors or stock phrases. Distinctive voices and subtextual dialogue. "
              "Narrative only, no title.\n\nPREMISE: " + PREMISE),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[11, 37])
    parser.add_argument('--tasks', nargs='+', choices=TASKS, default=['plan', 'prose'])
    parser.add_argument('--max-tokens', type=int, default=1250)
    args = parser.parse_args()
    config = tomllib.loads((ROOT / 'local' / 'config.toml').read_text())
    base_url = config['ollama_url'].rstrip('/')
    out = ROOT / 'output' / 'model_evaluation'
    out.mkdir(parents=True, exist_ok=True)
    for model in args.models:
        for task in args.tasks:
            for seed in args.seeds:
                path = out / f'{model.replace("/", "_").replace(":", "_")}-{task}-{seed}-t{args.max_tokens}.json'
                if path.exists():
                    print('cached', path.name, flush=True)
                    continue
                request = {'model': model, 'messages': [{'role': 'user', 'content': TASKS[task]}],
                           'stream': False, 'think': False,
                           'options': {'temperature': 0.7, 'seed': seed, 'num_predict': args.max_tokens, 'num_ctx': 8192}}
                start = time.monotonic()
                print('start', model, task, seed, flush=True)
                data = json.dumps(request).encode()
                req = urllib.request.Request(base_url + '/api/chat', data=data,
                                             headers={'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(req, timeout=600) as response:
                        result = json.load(response)
                    record = {'model': model, 'task': task, 'seed': seed, 'prompt': TASKS[task],
                              'response': result['message']['content'], 'wall_seconds': time.monotonic()-start,
                              'eval_count': result.get('eval_count'), 'eval_duration_ns': result.get('eval_duration'),
                              'prompt_eval_count': result.get('prompt_eval_count'),
                              'total_duration_ns': result.get('total_duration'), 'done_reason': result.get('done_reason')}
                    path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
                    print('done', path.name, round(record['wall_seconds'], 1), record['eval_count'], flush=True)
                except Exception as error:
                    print('error', model, task, seed, str(error), flush=True)
                    raise


if __name__ == '__main__':
    main()
