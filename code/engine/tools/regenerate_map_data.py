"""威海海域地图数据统一生成脚本。

从 ``external_toadd/tencent2/map_modified.py`` 中的原始经纬度数据，
通过 ``env.geo_coordinate.GeoConverter`` 统一转换为局部 XY 坐标，
生成可供 ``env.map_loader.load_polygon_file`` 直接读取的数据文件。

输出文件（位于 ``source_codes/env/map_data/``）：
    * ``weihai_map.txt``      —— 合并后的 XY 坐标多边形列表（经投影）
    * ``weihai_raw_lonlat.txt`` —— 合并后的原始经纬度多边形列表

坐标体系：Web Mercator (EPSG:3857)，原点 [122.0, 37.4]，缩放 50.0。
"""

import ast
import os
import sys

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
PROJECT_ROOT = r"d:\Projects\SimEngine"
SOURCE_CODES_DIR = os.path.join(PROJECT_ROOT, "source_codes")
MAP_DATA_DIR = os.path.join(SOURCE_CODES_DIR, "env", "map_data")
TENCENT2_DIR = os.path.join(PROJECT_ROOT, "external_toadd", "tencent2")
MAP_MODIFIED_PATH = os.path.join(TENCENT2_DIR, "map_modified.py")

OUTPUT_XY_PATH = os.path.join(MAP_DATA_DIR, "weihai_map.txt")
OUTPUT_LONLAT_PATH = os.path.join(MAP_DATA_DIR, "weihai_raw_lonlat.txt")

# 原点经纬度与缩放因子（与 GeoConverter 默认值一致）
ORIGIN_LONLAT = [122.0, 37.4]
SCALE = 50.0

# 需要提取的多边形数据变量名（obstacle_circle 是圆形障碍物，格式不同，不处理）
POLYGON_VAR_NAMES = ["fish_region", "island_polygon", "rubbish_region", "coaline", "hrbare"]


def load_raw_data():
    """从 map_modified.py 提取原始经纬度多边形数据。

    使用 ``ast`` 模块解析文件 AST，遍历顶层赋值节点，提取目标变量
    的字面量值。此方案不依赖 numpy / pyproj，纯静态解析，安全可靠。

    Returns
    -------
    dict
        ``{变量名: 多边形列表}``，每个值为 ``[[[lon, lat], ...], ...]``。
    """
    with open(MAP_MODIFIED_PATH, encoding="utf-8") as f:
        full_source = f.read()

    tree = ast.parse(full_source, filename=MAP_MODIFIED_PATH)

    data = {}
    for node in tree.body:
        # 只处理顶层赋值语句 (Assign)
        if not isinstance(node, ast.Assign):
            continue
        # 可能多个 target，逐个检查
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in POLYGON_VAR_NAMES:
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError) as exc:
                    raise RuntimeError(
                        f"无法用 ast.literal_eval 解析变量 {target.id} 的值: {exc}"
                    ) from exc
                data[target.id] = value
                break

    # 校验是否提取到了所有目标变量
    missing = set(POLYGON_VAR_NAMES) - set(data.keys())
    if missing:
        raise RuntimeError(f"ast 解析后仍缺少变量: {missing}\n已提取: {list(data.keys())}")

    print("[OK] 通过 ast 解析成功提取数据")
    return data


def validate_data(data):
    """校验提取的数据格式是否为 ``[[[lon, lat], ...], ...]``。"""
    for name, polygons in data.items():
        if not isinstance(polygons, list):
            raise TypeError(f"{name} 不是列表: {type(polygons)}")
        for i, region in enumerate(polygons):
            if not isinstance(region, list):
                raise TypeError(f"{name}[{i}] 不是列表: {type(region)}")
            for j, vertex in enumerate(region):
                if not (isinstance(vertex, (list, tuple)) and len(vertex) == 2):
                    raise TypeError(f"{name}[{i}][{j}] 不是 [lon, lat] 对: {vertex}")
        print(
            f"  [校验] {name}: {len(polygons)} 个多边形, 共 {sum(len(r) for r in polygons)} 个顶点"
        )


def convert_and_save(data):
    """用 GeoConverter 将经纬度多边形转换为 XY 坐标并保存。

    Parameters
    ----------
    data : dict
        ``{变量名: 经纬度多边形列表}``。

    Returns
    -------
    tuple
        ``(all_xy_polygons, all_lonlat_polygons, stats)``
    """
    # 确保能导入 env.geo_coordinate
    if SOURCE_CODES_DIR not in sys.path:
        sys.path.insert(0, SOURCE_CODES_DIR)
    from env.geo_coordinate import GeoConverter

    converter = GeoConverter(origin_lonlat=ORIGIN_LONLAT, scale=SCALE)

    converted_data = {}
    all_xy_polygons = []
    all_lonlat_polygons = []
    stats = {}

    for name, lonlat_polygons in data.items():
        xy_polygons = converter.convert_polygons(lonlat_polygons)
        converted_data[name] = xy_polygons

        num_polygons = len(xy_polygons)
        num_vertices = sum(len(r) for r in xy_polygons)
        stats[name] = {"polygons": num_polygons, "vertices": num_vertices}

        all_xy_polygons.extend(xy_polygons)
        all_lonlat_polygons.extend(lonlat_polygons)

    # 确保输出目录存在
    os.makedirs(MAP_DATA_DIR, exist_ok=True)

    # 保存 XY 坐标数据（供 map_loader.load_polygon_file 读取）
    GeoConverter.save_polygons(all_xy_polygons, OUTPUT_XY_PATH)

    # 保存原始经纬度数据（source of truth）
    GeoConverter.save_polygons(all_lonlat_polygons, OUTPUT_LONLAT_PATH)

    return all_xy_polygons, all_lonlat_polygons, stats


def compute_xy_bounds(xy_polygons):
    """计算 XY 多边形列表的坐标范围。"""
    if not xy_polygons:
        return None
    all_x = [v[0] for region in xy_polygons for v in region]
    all_y = [v[1] for region in xy_polygons for v in region]
    return {
        "min_x": min(all_x),
        "max_x": max(all_x),
        "min_y": min(all_y),
        "max_y": max(all_y),
        "negative_x": min(all_x) < 0,
        "negative_y": min(all_y) < 0,
    }


def print_statistics(stats, all_xy, all_lonlat, bounds):
    """打印统计信息。"""
    print("\n" + "=" * 70)
    print("威海海域地图数据生成 — 统计报告")
    print("=" * 70)

    print("\n【各数据源统计】")
    print(f"{'数据源':<20} {'多边形数':>10} {'顶点数':>10}")
    print("-" * 42)
    for name, s in stats.items():
        print(f"{name:<20} {s['polygons']:>10} {s['vertices']:>10}")

    total_xy_polygons = len(all_xy)
    total_xy_vertices = sum(len(r) for r in all_xy)
    total_lonlat_polygons = len(all_lonlat)
    total_lonlat_vertices = sum(len(r) for r in all_lonlat)

    print("-" * 42)
    print(f"{'合计(XY)':<20} {total_xy_polygons:>10} {total_xy_vertices:>10}")
    print(f"{'合计(经纬度)':<20} {total_lonlat_polygons:>10} {total_lonlat_vertices:>10}")

    print("\n【XY 坐标范围】")
    if bounds:
        print(f"  X 范围: [{bounds['min_x']:.4f}, {bounds['max_x']:.4f}]")
        print(f"  Y 范围: [{bounds['min_y']:.4f}, {bounds['max_y']:.4f}]")
        print(f"  存在负 X 坐标: {'是' if bounds['negative_x'] else '否'}")
        print(f"  存在负 Y 坐标: {'是' if bounds['negative_y'] else '否'}")
        if bounds["negative_x"] or bounds["negative_y"]:
            print(
                "  [提示] 存在负坐标，下游如需正值可使用 "
                "map_loader.apply_coordinate_offset() 施加偏移"
            )
    else:
        print("  (无数据)")

    print("\n【输出文件】")
    print(f"  XY 坐标:   {OUTPUT_XY_PATH}")
    print(f"  经纬度原始: {OUTPUT_LONLAT_PATH}")
    print("=" * 70)


def verify_output():
    """验证生成的 weihai_map.txt 可被 map_loader 正确加载。"""
    if SOURCE_CODES_DIR not in sys.path:
        sys.path.insert(0, SOURCE_CODES_DIR)
    from env.map_loader import load_polygon_file

    print("\n【验证】用 map_loader.load_polygon_file 加载生成的文件...")
    data = load_polygon_file(OUTPUT_XY_PATH)
    num_polygons = len(data)
    num_vertices = sum(len(p) for p in data)
    print(f"  加载成功: {num_polygons} 个多边形, {num_vertices} 个顶点")

    # 同时验证经纬度文件
    print("  验证经纬度文件...")
    raw_data = load_polygon_file(OUTPUT_LONLAT_PATH)
    print(f"  经纬度文件加载成功: {len(raw_data)} 个多边形, {sum(len(p) for p in raw_data)} 个顶点")

    return num_polygons, num_vertices


def main():
    """主入口。"""
    print("=" * 70)
    print("威海海域地图数据统一生成脚本")
    print("=" * 70)

    # 步骤 1: 提取原始经纬度数据
    print("\n[步骤 1] 提取原始经纬度数据...")
    data = load_raw_data()
    print("\n[校验数据格式]")
    validate_data(data)

    # 步骤 2 & 3: 转换并保存
    print("\n[步骤 2-3] 坐标转换与保存...")
    all_xy, all_lonlat, stats = convert_and_save(data)

    # 统计
    bounds = compute_xy_bounds(all_xy)
    print_statistics(stats, all_xy, all_lonlat, bounds)

    # 步骤 4: 验证
    print("\n[步骤 4] 验证输出...")
    verify_output()

    print("\n[DONE] 数据生成完成！")


if __name__ == "__main__":
    main()
