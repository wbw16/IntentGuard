#!/usr/bin/env bash
# =============================================================================
# generate_training_data.sh
# 多模型分批并行生成护卫模型训练数据
#
# 用法：
#   bash scripts/generate_training_data.sh                  # 使用默认参数
#   MAX_SCENARIOS=100 bash scripts/generate_training_data.sh
#   BATCH=2 bash scripts/generate_training_data.sh          # 只跑第二批
# =============================================================================

set -euo pipefail

# ── 配置 ──────────────────────────────────────────────────────────────────────
PYTHON="${PYTHON:-/Users/wbw/miniconda3/envs/IntentGuard/bin/python3}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs/datagen"
MAX_SCENARIOS="${MAX_SCENARIOS:-50}"   # 每数据源最多采集的场景数
STRATEGY="intentguard"
ONLY_BATCH="${BATCH:-}"               # 若设置则只运行指定批次（1-5）

mkdir -p "$LOG_DIR"

# ── 颜色输出 ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓ $*${NC}"; }
fail() { echo -e "${RED}[$(date '+%H:%M:%S')] ✗ $*${NC}"; }
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}"; }

# ── 单模型运行函数 ──────────────────────────────────────────────────────────────
# 用法：run_model <model_name>
# 通过 shell env 覆盖 .env 中的 DEFAULT_MODEL_NAME / STANDALONE_INTENTGUARD_MODEL_NAME
# .env 加载器使用 setdefault，不会覆盖已有 shell 变量
run_model() {
    local model="$1"
    local model_tag="${model//\//_}"
    local log_file="$LOG_DIR/${model_tag}.log"
    local start_ts
    start_ts=$(date +%s)

    log "▶ Starting: ${YELLOW}${model}${NC}"

    STANDALONE_INTENTGUARD_MODEL_NAME="$model" \
    DEFAULT_MODEL_NAME="$model" \
    INTENTGUARD_AUTO_CONFIRM="allow" \
        "$PYTHON" -m scripts.run_data_pipeline \
            --strategy "$STRATEGY" \
            --max-scenarios "$MAX_SCENARIOS" \
        > "$log_file" 2>&1

    local exit_code=$?
    local elapsed=$(( $(date +%s) - start_ts ))

    if [ $exit_code -eq 0 ]; then
        # 从日志里抓取样本数摘要
        local summary
        summary=$(grep "总样本数\|标签分布" "$log_file" 2>/dev/null | tail -2 | tr '\n' ' ')
        ok "Done [${elapsed}s]: ${model} | ${summary}"
    else
        fail "Failed [${elapsed}s]: ${model} → see ${log_file}"
        # 不 exit，让批次内其他模型继续
        return 1
    fi
}

# ── 批次运行函数 ────────────────────────────────────────────────────────────────
run_batch() {
    local batch_num="$1"
    shift
    local models=("$@")

    # 如果 ONLY_BATCH 设置了，只跑指定批次
    if [[ -n "$ONLY_BATCH" && "$ONLY_BATCH" != "$batch_num" ]]; then
        return 0
    fi

    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Batch ${batch_num}: ${#models[@]} models  (parallel)${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"

    local pids=()
    local model_names=()

    for model in "${models[@]}"; do
        run_model "$model" &
        pids+=($!)
        model_names+=("$model")
    done

    # 等待批次内所有进程，统计成功/失败
    local success=0 failed=0
    for i in "${!pids[@]}"; do
        if wait "${pids[$i]}"; then
            (( success++ )) || true
        else
            (( failed++ )) || true
        fi
    done

    echo ""
    echo -e "${BLUE}── Batch ${batch_num} complete: ${GREEN}${success} ok${NC}${BLUE}, ${RED}${failed} failed${NC}${BLUE} ──${NC}"
}

# ── 环境检查 ────────────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

info "Project: $PROJECT_DIR"
info "Python:  $PYTHON"
info "Strategy: $STRATEGY  |  MAX_SCENARIOS: $MAX_SCENARIOS"
info "Log dir: $LOG_DIR"
[[ -n "$ONLY_BATCH" ]] && info "Only running batch: $ONLY_BATCH"

# 快速验证 Python 环境
"$PYTHON" -c "import yaml, openai" 2>/dev/null || {
    fail "Python env missing yaml or openai. Check PYTHON=$PYTHON"
    exit 1
}
ok "Python env OK"

# ── 批次定义 ─────────────────────────────────────────────────────────────────────
BATCH1=(
    "Qwen/Qwen3.5-397B-A17B"
    "Qwen/Qwen3.5-122B-A10B"
    "Qwen/Qwen3.5-35B-A3B"
    "Qwen/Qwen3.5-27B"
    "Qwen/Qwen3.5-9B"
    "Qwen/Qwen3.5-4B"
)

BATCH2=(
    "Qwen/Qwen3-VL-32B-Instruct"
    "Qwen/Qwen2.5-72B-Instruct"
    "Qwen/Qwen2.5-32B-Instruct"
    "Qwen/Qwen2.5-14B-Instruct"
    "Qwen/Qwen2.5-7B-Instruct"
)

BATCH3=(
    "deepseek-ai/DeepSeek-V3.2"
    "deepseek-ai/DeepSeek-R1"
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
    "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
)

BATCH4=(
    "zai-org/GLM-4.6"
    "zai-org/GLM-4.5-Air"
    "THUDM/GLM-Z1-32B-0414"
    "THUDM/GLM-Z1-9B-0414"
)

BATCH5=(
    "inclusionAI/Ling-flash-2.0"
    "inclusionAI/Ling-mini-2.0"
)

# ── 主流程 ────────────────────────────────────────────────────────────────────────
TOTAL_START=$(date +%s)

run_batch 1 "${BATCH1[@]}"
run_batch 2 "${BATCH2[@]}"
run_batch 3 "${BATCH3[@]}"
run_batch 4 "${BATCH4[@]}"
run_batch 5 "${BATCH5[@]}"

# ── 最终汇总 ──────────────────────────────────────────────────────────────────────
TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_START ))
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  All batches complete  (${TOTAL_ELAPSED}s total)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"

# 统计生成的文件
echo ""
info "Generated files:"
ls -lh "$PROJECT_DIR/data/guard_training/samples_"*.jsonl 2>/dev/null \
    | awk '{printf "  %-60s %s lines\n", $NF, ""}' || true

# 汇总各文件行数（= 样本数）
if ls "$PROJECT_DIR/data/guard_training/samples_"*.jsonl &>/dev/null; then
    echo ""
    info "Sample counts:"
    wc -l "$PROJECT_DIR/data/guard_training/samples_"*.jsonl \
        | grep -v "total" \
        | sort -rn \
        | awk '{printf "  %6d  %s\n", $1, $2}'
    total_samples=$(wc -l "$PROJECT_DIR/data/guard_training/samples_"*.jsonl \
        | tail -1 | awk '{print $1}')
    echo ""
    ok "Total samples across all models: $total_samples"
fi

# 显示失败的日志（如果有）
failed_logs=$(grep -l "ERROR\|Traceback\|FAILED" "$LOG_DIR/"*.log 2>/dev/null || true)
if [[ -n "$failed_logs" ]]; then
    echo ""
    echo -e "${RED}── Failed runs (check logs) ──${NC}"
    for f in $failed_logs; do
        echo -e "  ${RED}$(basename "$f")${NC}"
        grep "ERROR\|FAILED" "$f" | tail -2 | sed 's/^/    /'
    done
fi
