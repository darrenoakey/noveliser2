# Noveliser2 agent notes

Text generation uses the gitignored `local/config.toml` Ollama route. Planning is `qwen3.6:35b-a3b`; prose is `ornith-1.5:35b`. Both live on Boringstack (`10.0.0.42:11434`, router name `boringstack`, MAC `B6:A4:AD:43:12:46`). Never load those models on this laptop. If the host is down, `ether-wake -i br0 B6:A4:AD:43:12:46` from the ASUS router is the wake attempt; a FAILED neighbour means it is powered off, not merely slow.

New plans go through `PremiseGuard` and a frozen `ScheduleContract`. The schedule JSON schema must set `maximum` to the requested chapter count, or the model invents chapter N+1. Repair feedback must quote the exact missing sentence; naming only the setup ID makes the model paste the ID. Resume the acceptance novel with `python3 scripts/acceptance_novel.py output/The_Weight_of_Wonder` after Boringstack answers `/api/tags`. Long generation is always detached, with a log and exit file.
