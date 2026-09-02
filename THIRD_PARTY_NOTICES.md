# Third-Party and Provenance Notes

- The reference model is **PANNs LeeNet11** from `qiuqiangkong/audioset_tagging_cnn`. The upstream source repository carries the MIT License.
- The pretrained LeeNet11 checkpoint used for the validated handoff is `LeeNet11_mAP=0.266.pth` (MD5 `61ba7a7a85542fe4e97240db974eb158`), distributed by the PANNs authors through Zenodo record 3987831. This source import does not redistribute the original checkpoint.
- AudioSet metadata describes 527 sound classes used by the model. Demo audio in the full v6 release was selected from AudioSet-referenced YouTube segments; raw demo audio is intentionally omitted from this source repository pending redistribution review.
- Vitis platform support files in `software/vitis/**/src` retain their original AMD/Xilinx SPDX and copyright notices.
- Vivado-generated project/IP metadata retains AMD/Xilinx notices where present.

No project-wide license is assigned by this import. Project owners should select a license only after confirming compatibility with all retained and separately distributed components.
