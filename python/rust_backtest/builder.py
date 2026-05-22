import subprocess
import sys
import os
import urllib.request
import json
import shutil
from pathlib import Path


_engine_path: str | None = None
CACHE_DIR = Path.home() / ".cache" / "rust_backtest"


def _detect_target() -> str:
    import platform
    machine = platform.machine()
    if machine == "x86_64":
        return "x86_64-unknown-linux-musl"
    elif machine in ("aarch64", "arm64"):
        return "aarch64-unknown-linux-musl"
    return f"{machine}-unknown-linux-musl"


def _get_cached_path(target: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"backtest_engine-{target}"


def get_engine_path(force_rebuild: bool = False) -> str:
    global _engine_path

    if not force_rebuild and _engine_path and os.path.exists(_engine_path):
        return _engine_path

    package_root = Path(__file__).resolve().parent.parent.parent
    target = _detect_target()

    cand_bin = _get_cached_path(target)
    if cand_bin.exists():
        _engine_path = str(cand_bin)
        return _engine_path

    for p in [
        package_root / "target" / target / "release" / "backtest_engine",
        package_root / "target" / "release" / "backtest_engine",
    ]:
        if p.exists():
            _engine_path = str(p)
            return _engine_path

    path = _download(target)
    if path:
        _engine_path = path
        return _engine_path

    return _build(package_root)


def _download(target: str) -> str | None:
    from importlib.metadata import version as pkg_version
    try:
        ver = pkg_version("rust-backtest")
    except Exception:
        ver = "v0.2.0"
    if not ver.startswith("v"):
        ver = f"v{ver}"

    cache_path = _get_cached_path(target)
    url = f"https://github.com/ZulferDev/rust-engine/releases/download/{ver}/backtest_engine-{target}"

    print(f"Downloading pre-built engine ({target})...")
    sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, cache_path)
        cache_path.chmod(0o755)
        print("Download complete.")
        return str(cache_path)
    except Exception:
        pass

    url_latest = (
        "https://github.com/ZulferDev/rust-engine/releases/latest/download/"
        f"backtest_engine-{target}"
    )
    try:
        urllib.request.urlretrieve(url_latest, cache_path)
        cache_path.chmod(0o755)
        print("Download complete.")
        return str(cache_path)
    except Exception:
        return None


def _build(root: Path) -> str:
    print("Building Rust backtest engine from source...")
    print("(this takes ~2-3 minutes on first run)")
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

    target = _detect_target()
    musl_bin = root / "target" / target / "release" / "backtest_engine"
    if musl_bin.exists():
        _engine_path = str(musl_bin)
        print("Build complete.")
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
