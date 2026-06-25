#!/usr/bin/env bash
# =============================================================================
# run_security_tests.sh — Prompt 注入攻防对比测试一键运行脚本
# 用法：bash run_security_tests.sh [--before | --after | --all]
# =============================================================================

set -euo pipefail
cd "$(dirname "$0")"   # 脚本所在目录即项目根目录

TARGET="${1:---all}"
REPORT_DIR="tests/security"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     AgentForge — Prompt 注入攻防对比测试                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

run_pytest() {
    local MARK="$1"
    local LABEL="$2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "▶ 运行 [$LABEL] 测试..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    PYTHONPATH=src python -m pytest tests/security/test_prompt_injection.py \
        -v --tb=short --no-header \
        ${MARK:+-m "$MARK"} \
        2>&1 | tee "${REPORT_DIR}/result_${LABEL}_${TIMESTAMP}.txt"
    echo ""
}

case "$TARGET" in
    --before)
        echo "📌 仅运行"无防护"测试（演示漏洞现状）"
        echo ""
        run_pytest "before_defense" "before"
        echo "💡 提示：xfail = 漏洞已确认；passed = 防护意外生效；failed = 测试本身有问题"
        ;;
    --after)
        echo "🛡 仅运行"有防护"测试（验证防护有效性）"
        echo ""
        run_pytest "after_defense" "after"
        echo "💡 提示：passed = 防护生效；skip = 防护尚未实现；failed = 防护有缺陷"
        ;;
    --all | *)
        echo "🔍 运行全部测试（before + after 对比）"
        echo ""

        echo "【第一阶段：无防护基线 (before_defense)】"
        PYTHONPATH=src python -m pytest tests/security/test_prompt_injection.py \
            -v --tb=short --no-header -m "before_defense" \
            2>&1 | tee "${REPORT_DIR}/result_before_${TIMESTAMP}.txt" || true

        echo ""
        echo "【第二阶段：有防护验证 (after_defense)】"
        PYTHONPATH=src python -m pytest tests/security/test_prompt_injection.py \
            -v --tb=short --no-header -m "after_defense" \
            2>&1 | tee "${REPORT_DIR}/result_after_${TIMESTAMP}.txt" || true

        echo ""
        echo "【第三阶段：通用单元测试 (unit, 含误报检测)】"
        PYTHONPATH=src python -m pytest tests/security/test_prompt_injection.py \
            -v --tb=short --no-header -m "unit and not before_defense and not after_defense" \
            2>&1 | tee "${REPORT_DIR}/result_unit_${TIMESTAMP}.txt" || true

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 汇总报告："
        echo "   before: ${REPORT_DIR}/result_before_${TIMESTAMP}.txt"
        echo "   after:  ${REPORT_DIR}/result_after_${TIMESTAMP}.txt"
        echo "   unit:   ${REPORT_DIR}/result_unit_${TIMESTAMP}.txt"
        echo ""
        echo "图例："
        echo "  PASSED   → 断言通过（预期行为）"
        echo "  XFAIL    → 预期失败（已知漏洞/待实现防护，需要修复）"
        echo "  XPASS    → 意外通过（原本预期会失败，但防护意外生效）"
        echo "  SKIPPED  → 跳过（防护代码尚未实现，等待编码）"
        echo "  FAILED   → 断言失败（非预期行为，需要调查）"
        ;;
esac
