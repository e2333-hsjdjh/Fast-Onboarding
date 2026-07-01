"""CLI for the resume generator MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fast_onboarding.resume_mvp import MaterialStore, ResumeMVPWorkflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a targeted Markdown resume and ATS report.")
    parser.add_argument("--profile", required=True, help="Path to candidate profile JSON.")
    parser.add_argument("--jd", required=True, help="Path to job description text.")
    parser.add_argument("--output-dir", default="workspace/mvp-output", help="Directory for generated files.")
    parser.add_argument("--target-role", default="", help="Optional target role override.")
    args = parser.parse_args()

    profile = MaterialStore(args.profile).from_dict(
        json.loads(Path(args.profile).read_text(encoding="utf-8"))
    )
    jd_text = Path(args.jd).read_text(encoding="utf-8")
    result = ResumeMVPWorkflow().run(
        profile=profile,
        jd_text=jd_text,
        output_dir=args.output_dir,
        target_role=args.target_role,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
