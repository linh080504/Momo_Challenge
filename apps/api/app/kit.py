"""Load the shared and tested scripts from the kit."""

import importlib.util
import sys

from .config import ROOT

SKILLS = ROOT / ".claude" / "skills"


def load_skill(name, script):
    spec = importlib.util.spec_from_file_location(
        f"tkc_{script}", SKILLS / name / "scripts" / f"{script}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


domain_check = load_skill("evidence-tools", "domain_check")
pii_mask = load_skill("pii-guard", "pii_mask")
vietqr = load_skill("vietqr", "vietqr")
