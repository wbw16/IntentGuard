"""evaluation — 评测框架。

包含指标计算、评测运行器、消融实验和报告生成。
"""

from .metrics import EvalMetrics, compute_metrics_from_meta, load_and_compute
from .eval_runner import EvalRunner
from .ablation import AblationRunner
from .report_generator import ReportGenerator
