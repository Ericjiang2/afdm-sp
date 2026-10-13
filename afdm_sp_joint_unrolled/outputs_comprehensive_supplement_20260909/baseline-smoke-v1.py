"""Single bounded engineering batch; invoke only after preflight and tests."""
import torch
from afdm_sp_joint_unrolled.supplement_baseline_run import main
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.cuda.set_per_process_memory_fraction(.25, device=0)
raise SystemExit(main())
