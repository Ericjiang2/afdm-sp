import torch
from afdm_sp_joint_unrolled.supplement_profile import main
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.cuda.set_per_process_memory_fraction(.25,0)
raise SystemExit(main())
