import streamlit as st
from ortools.linear_solver import pywraplp

# 页面基础配置
st.set_page_config(page_title="直线电机型材智能套裁与盘活系统", layout="wide")

st.title("🏭 直线电机模组 - 型材/导轨智能套裁与库存盘活系统")
st.markdown("通过 AI 数学优化算法，**优先消耗尾料/库存**，最大化提升材料利用率，降低仓储沉没成本。")

# 侧边栏：库存管理
st.sidebar.header("📦 仓库库存与尾料设置")
st.sidebar.markdown("输入当前仓库中现有的长料及尾料余量：")

stock_6000 = st.sidebar.number_input("标准长料 6000mm (根)", min_value=0, value=4)
stock_4000 = st.sidebar.number_input("标准长料 4000mm (根)", min_value=0, value=3)
stock_2500 = st.sidebar.number_input("标准长料 2500mm (根)", min_value=0, value=10)
stock_5000 = st.sidebar.number_input("尾料/余料 5000mm (根)", min_value=0, value=5)
stock_1000 = st.sidebar.number_input("尾料/余料 1000mm (根)", min_value=0, value=14)
kerf = st.sidebar.slider("锯口/刀口损耗 (mm)", min_value=0, max_value=10, value=3)

# 主界面：订单录入
st.header("📋 订单需求录入")
col1, col2 = st.columns(2)

with col1:
    req_1479 = st.number_input("零件目标长度 1479 mm 的需求数量 (根)", min_value=0, value=3)

with col2:
    req_939 = st.number_input("零件目标长度 939 mm 的需求数量 (根)", min_value=0, value=6)

# 用户还可以自定义增加其他规格
st.markdown("---")
with st.expander("➕ 添加更多自定义规格（可选）"):
    extra_len = st.number_input("自定义零件长度 (mm)", min_value=0, value=0)
    extra_qty = st.number_input("自定义零件数量 (根)", min_value=0, value=0)

# 计算按钮
if st.button("🚀 开始智能套裁计算", type="primary"):
    # 组装订单需求
    demands = {}
    if req_1479 > 0:
        demands[1479] = req_1479
    if req_939 > 0:
        demands[939] = demands.get(939, 0) + req_939
    if extra_len > 0 and extra_qty > 0:
        length = int(extra_len)
        demands[length] = demands.get(length, 0) + int(extra_qty)

    if not demands:
        st.warning("请至少输入一项有效的订单需求！")
    else:
        # 组装库存
        warehouse_stock = {
            6000: stock_6000,
            4000: stock_4000,
            2500: stock_2500,
            5000: stock_5000,
            1000: stock_1000,
        }
        # 过滤掉库存为0的项
        warehouse_stock = {k: v for k, v in warehouse_stock.items() if v > 0}

        # 调用 OR-Tools 优化求解
        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            st.error("求解器初始化失败")
        else:
            stock_lengths = list(warehouse_stock.keys())
            all_patterns = {}
            for s_len in stock_lengths:
                patterns_for_stock = []
                lengths = list(demands)

                def generate_patterns(index, used_length, piece_count, pattern):
                    if index == len(lengths):
                        if piece_count:
                            patterns_for_stock.append(pattern.copy())
                        return

                    length = lengths[index]
                    max_count = min(
                        demands[length],
                        (s_len - used_length + (kerf if piece_count else 0))
                        // (length + kerf),
                    )
                    for count in range(max_count + 1):
                        additional_length = count * length
                        additional_length += kerf * (
                            count if piece_count else max(0, count - 1)
                        )
                        pattern[length] = count
                        generate_patterns(
                            index + 1,
                            used_length + additional_length,
                            piece_count + count,
                            pattern,
                        )
                    pattern.pop(length, None)

                generate_patterns(0, 0, 0, {})
                all_patterns[s_len] = patterns_for_stock

            x = {}
            for s_len in stock_lengths:
                x[s_len] = []
                for j in range(len(all_patterns[s_len])):
                    max_limit = warehouse_stock[s_len]
                    x[s_len].append(solver.IntVar(0, max_limit, f"x_{s_len}_{j}"))

            for length, qty in demands.items():
                constraint = solver.Constraint(qty, qty)
                for s_len in stock_lengths:
                    for j, pattern in enumerate(all_patterns[s_len]):
                        if length in pattern:
                            constraint.SetCoefficient(x[s_len][j], pattern[length])

            for s_len in stock_lengths:
                constraint = solver.Constraint(0, warehouse_stock[s_len])
                for j in range(len(all_patterns[s_len])):
                    constraint.SetCoefficient(x[s_len][j], 1)

            objective = solver.Objective()
            for s_len in stock_lengths:
                for j, pattern in enumerate(all_patterns[s_len]):
                    piece_count = sum(pattern.values())
                    used_len = sum(length * qty for length, qty in pattern.items())
                    used_len += max(0, piece_count - 1) * kerf
                    waste = s_len - used_len
                    objective.SetCoefficient(x[s_len][j], waste)
            objective.SetMinimization()

            status = solver.Solve()

            if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
                st.success("🎉 计算成功！最优切割方案如下：")
                total_parts_length = sum(
                    length * qty for length, qty in demands.items()
                )
                total_stock_used_length = 0

                results_found = False
                for s_len in stock_lengths:
                    used_count_for_stock = 0
                    stock_output_lines = []
                    for j, pattern in enumerate(all_patterns[s_len]):
                        count = int(x[s_len][j].solution_value())
                        if count > 0:
                            used_count_for_stock += count
                            parts_desc = ", ".join(
                                [
                                    f"{qty}段 {length}mm"
                                    for length, qty in pattern.items()
                                    if qty > 0
                                ]
                            )
                            piece_count = sum(pattern.values())
                            used_length = sum(
                                length * qty for length, qty in pattern.items()
                            )
                            waste = s_len - used_length - max(0, piece_count - 1) * kerf
                            stock_output_lines.append(
                                f"👉 采用此方案 **[ {count} ] 根**: 切出 [{parts_desc}] | "
                                f"产生尾料: **{int(waste)}mm**"
                            )

                    if used_count_for_stock > 0:
                        results_found = True
                        st.markdown(
                            f"### 📦 使用库存 [ 长度 {s_len}mm ] 共消耗 "
                            f"{used_count_for_stock} 根 "
                            f"(库存剩余: {warehouse_stock[s_len] - used_count_for_stock} 根)"
                        )
                        for line in stock_output_lines:
                            st.markdown(line)
                        total_stock_used_length += s_len * used_count_for_stock
                        st.divider()

                if results_found and total_stock_used_length > 0:
                    utilization = (total_parts_length / total_stock_used_length) * 100
                    st.metric(
                        label="🎯 本次切割综合材料利用率", value=f"{utilization:.2f}%"
                    )
            else:
                st.error(
                    "未找到可行解。提示：当前订单需求量可能超过了现有库存型材总长，"
                    "请补充库存或增加标准长料！"
                )
