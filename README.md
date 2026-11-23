# dictation-bench

Test-only harness that compares dictation apps on the same synthetic recordings,
on a GitHub-hosted Windows runner.

- `vm/scenarios.json` and `vm/audio/`: synthetic test sentences (text-to-speech), each
  tagged with the words a good transcript must keep.
- `vm/agent.py`: runs command files pushed to `vm/cmd/` on the runner. Results are
  encrypted before they are pushed to the `results` branch, so nothing readable about
  the run (screens, outputs) is published here.
- `.github/workflows/vm.yml`: starts the runner when `vm/start` changes on `main`.

No credentials or private data are stored in this repository.
