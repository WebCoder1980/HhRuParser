import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "script.py",
    "compress.py",
    "compress2.py",
    "to_sqlite.py",
]

WORKSPACE = Path(__file__).parent


def run_script(name: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"Этап: {name}")
    print(f"{'=' * 60}")
    
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / name)],
        cwd=str(WORKSPACE),
    )
    
    if result.returncode != 0:
        print(f"ОШИБКА: этап {name} завершился с кодом {result.returncode}")
        return False
    return True


def main() -> int:
    print("Pipeline оркестратор")
    print("=" * 60)
    
    for script in SCRIPTS:
        if not run_script(script):
            print("\nPipeline остановлен из-за ошибки.")
            return 1
    
    print("\n" + "=" * 60)
    print("Pipeline завершён успешно.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
