"""Helper script to start Celery worker with automatic pool selection.

Usage (PowerShell):
  python scripts/run_worker.py

Logic:
  - If CELERY_FORCE_SOLO=1 or Python >= 3.13 => use solo pool.
  - Else use prefork.
Override explicitly with CELERY_POOL env var (prefork|solo|threads|gevent ...).
"""
import os
import sys
import subprocess


def main():
  py_ver = sys.version_info[:2]
  env_pool = os.getenv("CELERY_POOL")
  force_solo = os.getenv("CELERY_FORCE_SOLO") == "1" or py_ver >= (3, 13)
  pool = env_pool or ("solo" if force_solo else "prefork")
  concurrency = os.getenv("CELERY_CONCURRENCY")  # e.g. 4, 8

  cmd = [
    sys.executable,
    "-m",
    "celery",
    "-A",
    "celery_app.celery_app",
    "worker",
    "-l",
    "info",
    "-P",
    pool,
  ]
  if concurrency and pool != "solo":
    cmd.extend(["-c", concurrency])

  print(
    f"[run_worker] Python {py_ver}, pool={pool}, concurrency={concurrency or ('1(solo)' if pool=='solo' else 'default')}, command={' '.join(cmd)}"
  )
  try:
    subprocess.run(cmd, check=True)
  except subprocess.CalledProcessError as e:
    print(f"[run_worker] Worker exited with {e.returncode}")
    sys.exit(e.returncode)


if __name__ == "__main__":
    main()
