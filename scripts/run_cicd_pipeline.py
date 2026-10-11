#!/usr/bin/env python3
"""
NetDevOps CI/CD Master Pipeline Orchestrator
Executes all stages of the Network Infrastructure-as-Code (IaC) pipeline.
Used locally by network engineers and in GitHub Actions CI/CD workflows.
"""

import os
import sys
import time
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE_DIR, "build")

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def run_stage(stage_num, stage_name, cmd_args, stop_on_fail=True):
    print_banner(f"STAGE {stage_num}: {stage_name.upper()}")
    start_time = time.time()
    
    cmd_str = " ".join(cmd_args)
    print(f"[*] Executing: {cmd_str}\n")
    
    res = subprocess.run(cmd_args, cwd=BASE_DIR)
    elapsed = time.time() - start_time
    
    if res.returncode == 0:
        print(f"\n[\033[92mSTAGE {stage_num} PASSED\033[0m] {stage_name} ({elapsed:.2f}s)")
        return True
    else:
        print(f"\n[\033[91mSTAGE {stage_num} FAILED\033[0m] {stage_name} (Exit code {res.returncode}, {elapsed:.2f}s)")
        if stop_on_fail:
            print("\n\033[91mPipeline aborted due to stage failure.\033[0m")
            sys.exit(res.returncode)
        return False

def generate_consolidated_report(reports_dir):
    """Combine diff report and verification report into a consolidated summary."""
    summary_path = os.path.join(reports_dir, "cicd_pipeline_summary.md")
    diff_report = os.path.join(reports_dir, "diff_report.md")
    ver_report = os.path.join(reports_dir, "verification_report.md")

    content = "# 🛡️ NetDevOps End-to-End Network CI/CD Pipeline Summary\n\n"
    content += f"**Execution Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`\n\n"

    if os.path.exists(diff_report):
        with open(diff_report, "r") as f:
            content += f.read() + "\n\n---\n\n"

    if os.path.exists(ver_report):
        with open(ver_report, "r") as f:
            content += f.read() + "\n\n"

    with open(summary_path, "w") as sf:
        sf.write(content)

    print(f"\n[✓] Consolidated CI/CD Summary written to: {summary_path}")
    return summary_path

def main():
    parser = argparse.ArgumentParser(description="NetDevOps Master CI/CD Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deployment (do not apply changes to live devices)")
    parser.add_argument("--device", help="Target specific device (e.g. R1, S1)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip Stage 4 network health verification")
    parser.add_argument("--stagger", type=float, default=1.0, help="Delay between device deployments")
    args = parser.parse_args()

    os.makedirs(BUILD_DIR, exist_ok=True)
    diff_md = os.path.join(BUILD_DIR, "diff_report.md")
    ver_md = os.path.join(BUILD_DIR, "verification_report.md")

    pipeline_start = time.time()
    print("=" * 80)
    print("      NETDEVOPS END-TO-END CI/CD PIPELINE FOR ROUTERS & SWITCHES")
    print(f"      Mode: {'DRY-RUN SIMULATION' if args.dry_run else 'ENFORCE / PRODUCTION'}")
    print(f"      Scope: {args.device if args.device else 'All Network Nodes (R1-R5, S1-S4)'}")
    print("=" * 80)

    # Stage 1: Static Linting & Secret Detection
    run_stage(1, "Static Linting & Secret Scan", ["python3", "scripts/validate_iac_syntax.py"])

    # Stage 2: Configuration Compilation & Diff
    stage2_cmd = ["python3", "scripts/generate_and_diff_configs.py", "--markdown", diff_md]
    if args.device:
        stage2_cmd.extend(["--device", args.device])
    run_stage(2, "IaC Config Generation & Diffs", stage2_cmd)

    # Stage 3: Automated Deployment
    stage3_cmd = ["python3", "scripts/deploy_device_configs.py", "--stagger", str(args.stagger)]
    if args.dry_run:
        stage3_cmd.append("--dry-run")
    if args.device:
        stage3_cmd.extend(["--device", args.device])
    run_stage(3, "Device Configuration Deployment", stage3_cmd)

    # Stage 4: Post-Deployment Verification
    if not args.skip_tests:
        run_stage(4, "Network Health & Observability Verification", ["python3", "scripts/verify_network_health.py", "--markdown", ver_md])

    # Generate Report
    summary_file = generate_consolidated_report(BUILD_DIR)

    total_time = time.time() - pipeline_start
    print_banner(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {total_time:.2f} SECONDS")

if __name__ == "__main__":
    main()
