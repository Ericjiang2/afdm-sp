#!/Users/guoyikun/.local/share/uv/tools/openevolve/bin/python
"""Run OpenEvolve over subscription CLIs (agy / codex / claude) without raw API keys.

  ~/.local/share/uv/tools/openevolve/bin/python evolve_cli.py <initial.py> <eval.py> -i 10 -o <out_dir> [--backend agy|codex|claude] [--model MODEL]
"""
import argparse, asyncio, os, subprocess, tempfile
from pathlib import Path
from openevolve import OpenEvolve
from openevolve.config import LLMModelConfig, load_config
from openevolve.llm.base import LLMInterface

DEFAULTS = dict(agy='gemini-4-neon-high', codex='gpt-6.2-sol', claude='sonnet')


class AgyCLILLM(LLMInterface):
    def __init__(self, cfg):
        self.model = cfg.name
        self.timeout = cfg.timeout or 300
        self.agy_bin = os.environ.get('AGY_BIN', str(Path.home() / '.local/bin/agy'))
        self.cwd = Path(tempfile.gettempdir()) / 'openevolve-agy-cwd'
        self.cwd.mkdir(parents=True, exist_ok=True)

    async def generate(self, prompt: str, **kwargs) -> str:
        sys_msg = kwargs.pop('system_message', None) or ''
        return await self.generate_with_context(sys_msg, [{'role': 'user', 'content': prompt}], **kwargs)

    async def generate_with_context(self, system_message: str, messages, **kwargs) -> str:
        body = '\n\n'.join(f"[{m.get('role', 'user')}]\n{m.get('content', '')}" for m in messages)
        full = f"{system_message}\n\n{body}".strip() if system_message else body
        timeout = int(kwargs.get('timeout', self.timeout))
        cmd = [self.agy_bin, '-p', full, '--model', self.model, '--mode', 'plan',
               '--sandbox', '--output-format', 'text', '--print-timeout', f'{timeout}s']
        loop = asyncio.get_running_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, timeout=timeout + 30),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            raise RuntimeError(f"agy failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}")
        return proc.stdout.strip()


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('initial_program')
    ap.add_argument('evaluation_file')
    ap.add_argument('-c', '--config', default=None)
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('-i', '--iterations', type=int, default=10)
    ap.add_argument('-t', '--target-score', type=float, default=None)
    ap.add_argument('--backend', choices=('agy', 'codex', 'claude'), default='agy')
    ap.add_argument('--model', default=None)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--checkpoint', default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not args.config:
        cfg.evaluator.cascade_evaluation = False
    model_name = args.model or DEFAULTS[args.backend]
    if args.backend == 'agy':
        mcfg = LLMModelConfig(name=model_name, weight=1.0, timeout=args.timeout, init_client=AgyCLILLM)
    elif args.backend == 'codex':
        mcfg = LLMModelConfig(name=model_name, provider='codex_app_server', weight=1.0,
                              timeout=args.timeout, reasoning_effort='high')
    else:
        mcfg = LLMModelConfig(name=model_name, provider='claude_code', weight=1.0, timeout=args.timeout)
    cfg.llm.models = [mcfg]

    ev = OpenEvolve(initial_program_path=args.initial_program, evaluation_file=args.evaluation_file,
                    config=cfg, output_dir=args.output)
    best = await ev.run(iterations=args.iterations, target_score=args.target_score, checkpoint_path=args.checkpoint)
    print('best_metrics:', best.metrics)
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
