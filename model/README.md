# Model Metadata

This repository keeps the metadata required to understand the hardware mapping while excluding large model binaries and redistributable payloads.

- Model: PANNs LeeNet11
- Input: 320,000 mono PCM16 samples at 32 kHz (10 s)
- Conv: Conv1~Conv9, kernel size 3
- Global: temporal max + rounded mean
- FC1: 256 -> 512 + ReLU
- FC2: 512 -> 527 AudioSet logits
- Parameters: 748,367
- Activation/weight: signed INT16
- Accumulator/bias effective width: signed 48-bit
- Final output: 527 signed INT16 Q10 logits

See `model_manifest.json` and `layer_config.csv` for the runtime mapping.
