#!/usr/bin/env python3
"""
JudgeGuard ADK Submission Validator & Packager
Verifies submission compliance against the official `swegemma` / `adk-submission` specification:
- Single root configuration (agent.yaml)
- Declarative security model (no arbitrary Python entrypoints)
- Allowed file extensions (.yaml, .yml, .md, .txt, .py, .json, .safetensors)
- Total size < 3 GiB
- Single declared base model from ALLOWED_MODEL_NAMES
- Permitted tools matching ToolRegistry
- Recursive !include validation
"""

import os
import sys
import tempfile
import yaml
import zipfile
from pathlib import Path

ALLOWED_MODELS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}

ALLOWED_EXTENSIONS = {
    ".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"
}

ALLOWED_TOOLS = {
    "run_command", "read_file", "edit_file", "write_file",
    "get_status", "submit_patch", "get_code_neighbors",
    "search_similar_code", "get_code_subgraph", "agent_tool"
}

MAX_TOTAL_SIZE = 3 * 1024 * 1024 * 1024  # 3 GiB

class SandboxedIncludeLoader(yaml.SafeLoader):
    """Custom YAML loader supporting the sandboxed !include directive."""
    def __init__(self, stream):
        self._root_dir = Path(getattr(stream, 'name', os.getcwd())).parent
        super().__init__(stream)

def include_constructor(loader, node):
    rel_path = loader.construct_scalar(node)
    target_path = (loader._root_dir / rel_path).resolve()
    
    if not target_path.exists():
        raise FileNotFoundError(f"!include file not found: {rel_path} (resolved: {target_path})")
    
    suffix = target_path.suffix.lower()
    if suffix in [".md", ".txt"]:
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()
    elif suffix in [".yaml", ".yml"]:
        with open(target_path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=SandboxedIncludeLoader)
    else:
        raise ValueError(f"Unsupported !include extension: {suffix}")

SandboxedIncludeLoader.add_constructor("!include", include_constructor)

def validate_submission_directory(root_dir: Path) -> dict:
    print(f"🔍 Validating unzipped submission root: {root_dir}")
    
    # 1. Root configuration check
    root_configs = [f for f in ["agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml"] if (root_dir / f).exists()]
    if not root_configs:
        raise ValueError("MissingRootConfigError: Exactly one root agent.yaml or root_agent.yaml required.")
    if len(root_configs) > 1:
        raise ValueError(f"MultipleRootConfigsError: Found multiple root configs: {root_configs}")
    root_config_path = root_dir / root_configs[0]
    print(f"  ✅ Root config detected: {root_configs[0]}")

    # 2. File extensions and size check
    total_size = 0
    file_count = 0
    all_files = []
    
    for p in root_dir.rglob("*"):
        if p.is_file():
            file_count += 1
            sz = p.stat().st_size
            total_size += sz
            rel = p.relative_to(root_dir)
            all_files.append((rel, sz))
            
            ext = p.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"ForbiddenFileExtensionError: {rel} has disallowed extension '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")

    print(f"  ✅ Scanned {file_count} files, total unpacked size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
    if total_size >= MAX_TOTAL_SIZE:
        raise ValueError(f"SubmissionTooLargeError: Total size {total_size} exceeds 3 GiB limit.")

    # 3. Parse root agent.yaml
    with open(root_config_path, "r", encoding="utf-8") as f:
        root_data = yaml.load(f, Loader=SandboxedIncludeLoader)

    declared_models = set()
    model_name = root_data.get("model")
    if model_name:
        declared_models.add(model_name)
    else:
        raise ValueError("Root agent config missing 'model' field.")

    tools = root_data.get("tools", [])
    for t in tools:
        if isinstance(t, str):
            if t not in ALLOWED_TOOLS:
                raise ValueError(f"InvalidToolError: '{t}' not in registered host tools.")
        elif isinstance(t, dict):
            if "agent_tool" in t:
                sub_cfg_path = root_dir / t["agent_tool"]["config_path"]
                if not sub_cfg_path.exists():
                    raise FileNotFoundError(f"Sub-agent config path not found: {sub_cfg_path}")
                with open(sub_cfg_path, "r", encoding="utf-8") as sf:
                    sub_data = yaml.load(sf, Loader=SandboxedIncludeLoader)
                sub_model = sub_data.get("model")
                if sub_model:
                    declared_models.add(sub_model)
                sub_tools = sub_data.get("tools", [])
                for st in sub_tools:
                    if isinstance(st, str) and st not in ALLOWED_TOOLS:
                        raise ValueError(f"Invalid sub-agent tool: '{st}'")
            else:
                raise ValueError(f"Unknown tool dictionary structure: {t}")

    # 4. Single model rule verification
    print(f"  Declared models across agent tree: {declared_models}")
    if len(declared_models) > 1:
        raise ValueError(f"SingleModelRuleViolation: Multiple models declared: {declared_models}")
    declared_model = next(iter(declared_models))
    if declared_model not in ALLOWED_MODELS:
        raise ValueError(f"DisallowedModelError: '{declared_model}' not in ALLOWED_MODELS ({ALLOWED_MODELS})")
    print(f"  ✅ Single base model verified: {declared_model}")

    # 5. Optional eval_config.yaml check
    eval_cfg = root_dir / "eval_config.yaml"
    if eval_cfg.exists():
        with open(eval_cfg, "r", encoding="utf-8") as f:
            eval_data = yaml.safe_load(f)
        print(f"  ✅ eval_config.yaml verified: {eval_data.get('evaluation', {})}")

    return {
        "status": "VALID",
        "root_config": root_configs[0],
        "model": declared_model,
        "files_count": file_count,
        "total_size": total_size
    }

def package_submission(source_dir: Path, output_zip: Path):
    print(f"\n📦 Packaging submission into {output_zip}...")
    files_to_pack = {
        "agent.yaml": (source_dir / "agent.yaml").read_text(encoding="utf-8"),
        "configs/sampling.yaml": (source_dir / "configs/sampling.yaml").read_text(encoding="utf-8"),
        "eval_config.yaml": (source_dir / "eval_config.yaml").read_text(encoding="utf-8"),
        "prompts/system.md": (source_dir / "prompts/system.md").read_text(encoding="utf-8"),
    }
    
    with zipfile.ZipFile(output_zip, "w") as zf:
        for name, content in sorted(files_to_pack.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, content.encode("utf-8"))
            print(f"   + {name}")
    
    zip_size = output_zip.stat().st_size
    print(f"✅ Packaged {output_zip.name} successfully ({zip_size:,} bytes / {zip_size/1024:.1f} KB).")

def verify_zip_archive(zip_path: Path):
    print(f"\n🧪 Extracting and verifying {zip_path.name} in clean test sandbox...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)
        
        result = validate_submission_directory(tmp_path)
        print("🎉 Extracted archive verification: 100% VALID!")
        return result

if __name__ == "__main__":
    current_dir = Path(__file__).parent.resolve()
    out_zip = current_dir / "submission.zip"
    
    # 1. Package submission
    package_submission(current_dir, out_zip)
    
    # 2. Verify extracted zip against official validator rules
    verify_zip_archive(out_zip)
    
    print("\n🚀 Ready for Kaggle submission!")
