"""地图数据加载与格式适配模块。

本模块将 ``test_weihai2_plot.py`` 中分散的文件读取逻辑（``load_list_from_file``
及其后续的批量加载调用）整合为统一的地图加载接口，并补充了坐标偏移工具，
用于消除 ``display_list_data.txt`` 等数据文件中存在的负坐标（X[-408]、
Y[-777]），避免下游哈希函数溢出。

职责分离
--------
本模块只负责文件解析与格式适配：
    * 读取 ``repr()`` 序列化的 Python 字面量多边形文件；
    * 合并多个多边形文件为单一列表；
    * 施加坐标偏移使全部顶点为正值；
    * 序列化保存。

坐标投影（Web Mercator 等）由 ``env.geo_coordinate`` 负责，本模块不包含任何
投影逻辑。``load_map`` 返回的多边形列表格式为 ``[[[x, y], ...], ...]``，与
``Sim2Sea.setup_line_obstacles`` 的入参格式一致，可直接喂入。
"""

import ast
import os
from collections.abc import Sequence
from pathlib import Path

# 复用 geo_coordinate 中的序列化实现，避免重复逻辑。
# 采用 try/except 包裹以降低硬依赖：即便在没有 geo_coordinate 的最小化环境里，
# map_loader 仍可独立工作（save_polygons 会回退到本模块内置实现）。
try:
    from env.geo_coordinate import GeoConverter

    _save_polygons_impl = GeoConverter.save_polygons
except Exception:  # pragma: no cover - 仅在依赖缺失时回退
    _save_polygons_impl = None


def _project_root() -> Path:
    """推断项目根目录（``source_codes`` 目录）。

    本文件位于 ``source_codes/env/map_loader.py``，因此项目根为
    ``Path(__file__).parent.parent``。``load_map`` 中的相对 ``data_dir`` 将
    以此为基准解析，与 ``from env.xxx import ...`` 的运行根保持一致。
    """
    return Path(__file__).resolve().parent.parent


def load_polygon_file(file_path: str) -> list:
    """读取单个多边形数据文件。

    使用 ``ast.literal_eval`` 安全地将文件中的 Python 字面量字符串还原为
    Python 对象（来自 ``test_weihai2_plot.py`` 第 331-339 行
    ``load_list_from_file``）。相比 ``eval``，``ast.literal_eval`` 只解析字面量
    结构（list/tuple/dict/number/str 等），不会执行任意代码，安全性高。

    Parameters
    ----------
    file_path : str
        多边形数据文件路径。文件内容应为 ``repr()`` 序列化的 Python 列表，
        例如 ``[[[x1, y1], [x2, y2], ...], ...]``。

    Returns
    -------
    list
        还原后的多边形列表。

    Raises
    ------
    FileNotFoundError
        文件不存在时抛出。
    ValueError
        文件内容不是合法的 Python 字面量时抛出。
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    data = ast.literal_eval(content)
    return data


def load_map(data_dir: str, map_files: Sequence[str]) -> list[list[list[float]]]:
    """加载并合并多个多边形文件。

    依次读取 ``data_dir`` 下 ``map_files`` 中的每个文件，将所有多边形合并为
    单一列表。``data_dir`` 为相对于项目根目录（``source_codes``）的路径。

    返回格式为 ``[[[x, y], [x, y], ...], ...]``，与
    ``Sim2Sea.setup_line_obstacles`` 的入参格式一致，可直接喂入。

    Parameters
    ----------
    data_dir : str
        相对于项目根目录的数据目录路径，例如 ``"data"`` 或
        ``"../external_toadd/tencent2"``。
    map_files : sequence of str
        要加载的文件名列表，例如 ``["list_data.txt", "display_list_data.txt"]``。

    Returns
    -------
    list
        合并后的多边形列表，每个多边形为 ``[[x, y], ...]`` 顶点序列。

    Notes
    -----
    本函数仅做文件解析与列表拼接，不做任何坐标投影。若源数据为经纬度，
    需先用 ``env.geo_coordinate.GeoConverter.convert_polygons`` 投影后再调用
    本函数，或在本函数返回后投影。
    """
    root = _project_root()
    base_dir = root / data_dir if not os.path.isabs(data_dir) else Path(data_dir)

    merged: list[list[list[float]]] = []
    for name in map_files:
        fpath = base_dir / name
        polygons = load_polygon_file(str(fpath))
        merged.extend(polygons)
    return merged


def apply_coordinate_offset(
    polygons: list[list[list[float]]], margin: float = 10.0
) -> tuple[list[list[list[float]]], float, float]:
    """对多边形列表施加坐标偏移，使全部顶点坐标为正值。

    ``display_list_data.txt`` 等数据文件经投影后可能包含负坐标（实测
    X 最小约 -408、Y 最小约 -777），直接送入哈希网格会导致下标溢出。本函数
    计算所有顶点的全局最小值并施加偏移，使新的最小值等于 ``margin``。

    偏移量公式：``offset = -min_value + margin``，保证
    ``new_min = min_value + offset = margin > 0``，且所有顶点均不小于
    ``margin``。

    Parameters
    ----------
    polygons : list
        多边形列表，格式 ``[[[x, y], ...], ...]``。
    margin : float, optional
        偏移后最小坐标的余量，默认 10.0。

    Returns
    -------
    tuple
        ``(offset_polygons, offset_x, offset_y)``：
            * ``offset_polygons`` —— 偏移后的多边形列表（新对象，不修改原数据）；
            * ``offset_x`` —— X 方向偏移量；
            * ``offset_y`` —— Y 方向偏移量。
    """
    if not polygons:
        return [], 0.0, 0.0

    min_x = min(vertex[0] for region in polygons for vertex in region)
    min_y = min(vertex[1] for region in polygons for vertex in region)

    offset_x = -min_x + margin
    offset_y = -min_y + margin

    offset_polygons: list[list[list[float]]] = []
    for region in polygons:
        offset_region = [[vertex[0] + offset_x, vertex[1] + offset_y] for vertex in region]
        offset_polygons.append(offset_region)
    return offset_polygons, offset_x, offset_y


def save_polygons(data, file_path: str) -> None:
    """将多边形数据以 ``repr()`` 字符串形式写入文件。

    优先复用 ``env.geo_coordinate.GeoConverter.save_polygons`` 的实现以保持
    行为一致；当 ``geo_coordinate`` 不可用时回退到本模块内置实现。写出的
    内容是有效的 Python 字面量，可被 ``ast.literal_eval`` 安全还原（与本
    模块 ``load_polygon_file`` 配对使用）。

    Parameters
    ----------
    data : list
        任意可被 ``repr()`` 序列化的多边形数据。
    file_path : str
        输出文件路径。
    """
    if _save_polygons_impl is not None:
        _save_polygons_impl(data, file_path)
        return
    # 回退实现（geo_coordinate 不可用时）
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(repr(data))
    print(f"列表已成功保存到文件：{file_path}")
