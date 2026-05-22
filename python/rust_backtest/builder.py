import subprocess
import sys
import os
from pathlib import Path


_engine_path: str | None = None


def get_engine_path(force_rebuild: bool = False) -> str:
    global _engine_path

    if not force_rebuild and _engine_path and os.path.exists(_engine_path):
        return _engine_path

    package_root = Path(__file__).resolve().parent.parent.parent

    candidates = [
        package_root / "target" / "x86_64-unknown-linux-musl" / "release" / "backtest_engine",
        package_root / "target" / "release" / "backtest_engine",
    ]
    for p in candidates:
        if p.exists():
            _engine_path = str(p)
            return _engine_path

    return _build(package_root)


def _build(root: Path) -> str:
    print("Building Rust backtest engine...")
    sys.stdout.flush()

    _ensure_rust()
    cargo = _find_cargo()

    result = subprocess.run(
        [cargo, "build", "--release"],
        cwd=root,
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        _engine_path = str(root / "target" / "release" / "backtest_engine")
        if os.path.exists(_engine_path):
            print("Build complete.")
            return _engine_path

    musl_bin = root / "target" / "x86_64-unknown-linux-musl" / "release" / "backtest_engine"
    if musl_bin.exists():
        _engine_path = str(musl_bin)
        print("Build complete (musl).")
        return _engine_path

    raise RuntimeError(
        f"Build failed.\n{result.stderr}\n\n"
        "Install Rust manually: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    )


def _ensure_rust():
    if _find_cargo():
        return
    print("Rust not found. Installing via rustup...")
    subprocess.run(
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y 2>&1",
        shell=True, check=True,
    )


def _find_cargo() -> str | None:
    cargo = subprocess.run(["which", "cargo"], capture_output=True, text=True)
    if cargo.returncode == 0:
        return cargo.stdout.strip()

    home_cargo = Path.home() / ".cargo" / "bin" / "cargo"
    if home_cargo.exists():
        os.environ["PATH"] = str(home_cargo.parent) + ":" + os.environ.get("PATH", "")
        return str(home_cargo)

    return None
