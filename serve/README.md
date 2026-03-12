# Serve

Responsibilities:

- one `vLLM` serving baseline
- one Modal deployment path
- benchmark artifact writing
- metric and trace export

Planned first input:

- one workload artifact from `bench/`

Planned first outputs:

- `manifest.json`
- `results.json`
- `stdout.log`
- `stderr.log`
- replay-capable `kvtrace` event file

Non-goals:

- custom serving kernels
- distributed serving fabric
- broad API surface
