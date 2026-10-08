"""威海海域统一坐标转换模块。

本模块将 map_modified.py 中分散的坐标投影函数（translate_lat_lon_to_xy /
translate_xy_to_lat_lon / convert_to_position / pos2lonlat / save_list_to_file）
整合为单一的 ``GeoConverter`` 类，并修复了原始实现中正向与反向转换不对称的缺陷。

背景
----
原始 ``map_modified.py`` 的坐标体系存在一个不一致：
    * ``convert_to_position``（正向）先做 Web Mercator 投影（EPSG:4326 -> 3857），
      减去原点的 Mercator 坐标，再除以 scale（50）；
    * ``pos2lonlat``（反向）却用简单线性公式
      ``x / (20 * lon_per_degree) + left_corner[0]`` 做近似反算。
两者并非互逆运算，反向结果存在较大误差。

本模块统一使用 Web Mercator 投影，正向与反向严格互逆：正向投影后减原点再缩放，
反向则先反缩放、加回原点再逆投影。这样 ``xy_to_lonlat(lonlat_to_xy(lon, lat))``
可精确还原原始经纬度。

坐标体系
--------
* 原点经纬度：[122.0, 37.4]（威海海域）
* 缩放因子：50.0
* 投影：Web Mercator（EPSG:3857），输入/输出经纬度为 EPSG:4326
"""

from collections.abc import Sequence

import pyproj


class GeoConverter:
    """威海海域统一坐标转换器。

    使用 Web Mercator (EPSG:3857) 投影，以 [122.0, 37.4] 为原点，
    缩放因子 50.0。正反向互为精确逆运算。

    Parameters
    ----------
    origin_lonlat : list or tuple of float, optional
        原点经纬度 [lon, lat]，默认 [122.0, 37.4]（威海海域左下角）。
    scale : float, optional
        坐标缩放因子，默认 50.0。正向变换将 Mercator 米除以该值，
        反向变换先乘以该值。

    Attributes
    ----------
    origin_lonlat : list
        原点经纬度。
    scale : float
        缩放因子。
    _fwd : pyproj.Transformer
        正向投影器（4326 -> 3857），``always_xy=True`` 故参数顺序为 (lon, lat)。
    _inv : pyproj.Transformer
        逆向投影器（3857 -> 4326），``always_xy=True`` 故返回 (lon, lat)。
    _basex : float
        原点的 Mercator X 坐标（米）。
    _basey : float
        原点的 Mercator Y 坐标（米）。

    Notes
    -----
    相对原始 ``convert_to_position`` / ``pos2lonlat`` 的关键修复：
        * ``pos2lonlat`` 原先使用 ``lon_per_degree`` 的线性近似，与正向的 Web
          Mercator 投影不对称，反算误差可达数百米乃至更大；
        * 本实现反向变换严格使用 ``Transformer 3857 -> 4326`` 逆投影，与正向
          互逆，``xy_to_lonlat(lonlat_to_xy(lon, lat))`` 可在浮点精度内还原
          原始经纬度。
    """

    def __init__(self, origin_lonlat: Sequence[float] = [122.0, 37.4], scale: float = 50.0):
        if origin_lonlat is None or len(origin_lonlat) < 2:
            raise ValueError("origin_lonlat 必须至少包含 [lon, lat] 两个分量")
        if scale == 0:
            raise ValueError("scale 不能为 0")

        self.origin_lonlat: list[float] = [float(origin_lonlat[0]), float(origin_lonlat[1])]
        self.scale: float = float(scale)

        # 创建正/逆向 Web Mercator 投影器（always_xy=True 保证参数/返回顺序为
        # (lon, lat)，与原始 map_modified.py 一致）。
        crs_geo = pyproj.CRS.from_epsg(4326)
        crs_web = pyproj.CRS.from_epsg(3857)
        self._fwd = pyproj.Transformer.from_crs(crs_geo, crs_web, always_xy=True)
        self._inv = pyproj.Transformer.from_crs(crs_web, crs_geo, always_xy=True)

        # 预计算原点的 Mercator 坐标，作为后续平移基准。
        self._basex, self._basey = self._fwd.transform(self.origin_lonlat[0], self.origin_lonlat[1])

    def lonlat_to_xy(self, lon: float, lat: float) -> tuple[float, float]:
        """经纬度 -> 局部 XY 坐标。

        步骤：Web Mercator 投影 -> 减去原点 Mercator 坐标 -> 除以 scale。

        Parameters
        ----------
        lon : float
            经度。
        lat : float
            纬度。

        Returns
        -------
        tuple of float
            ``(x, y)`` 局部平面坐标（无量纲，米/scale）。
        """
        x0, y0 = self._fwd.transform(lon, lat)
        x = (x0 - self._basex) / self.scale
        y = (y0 - self._basey) / self.scale
        return x, y

    def xy_to_lonlat(self, x: float, y: float) -> tuple[float, float]:
        """局部 XY 坐标 -> 经纬度（``lonlat_to_xy`` 的精确逆运算）。

        步骤：乘以 scale -> 加回原点 Mercator 坐标 -> Web Mercator 逆投影。

        这修复了原始 ``pos2lonlat`` 使用 ``lon_per_degree`` 线性近似导致正反
        向不对称的 bug。

        Parameters
        ----------
        x : float
            局部 X 坐标。
        y : float
            局部 Y 坐标。

        Returns
        -------
        tuple of float
            ``(lon, lat)`` 经纬度。
        """
        x0 = x * self.scale + self._basex
        y0 = y * self.scale + self._basey
        lon, lat = self._inv.transform(x0, y0)
        return lon, lat

    def convert_polygons(self, lonlat_polygons: list[list[list[float]]]) -> list[list[list[float]]]:
        """批量将经纬度多边形列表转换为局部 XY 坐标。

        输入 / 输出结构相同：``[[[lon, lat], [lon, lat], ...], ...]`` ->
        ``[[[x, y], [x, y], ...], ...]``。

        Parameters
        ----------
        lonlat_polygons : list
            多边形列表，每个多边形为 ``[[lon, lat], ...]`` 顶点序列。

        Returns
        -------
        list
            与输入同结构的 XY 坐标多边形列表。
        """
        converted: list[list[list[float]]] = []
        for region in lonlat_polygons:
            converted_region = []
            for vertex in region:
                lon, lat = vertex[0], vertex[1]
                x, y = self.lonlat_to_xy(lon, lat)
                converted_region.append([x, y])
            converted.append(converted_region)
        return converted

    def reverse_polygons(self, xy_polygons: list[list[list[float]]]) -> list[list[list[float]]]:
        """批量将局部 XY 多边形列表逆向转换为经纬度。

        输入 / 输出结构相同：``[[[x, y], [x, y], ...], ...]`` ->
        ``[[[lon, lat], [lon, lat], ...], ...]``。

        Parameters
        ----------
        xy_polygons : list
            XY 坐标多边形列表。

        Returns
        -------
        list
            与输入同结构的经纬度多边形列表。
        """
        reverted: list[list[list[float]]] = []
        for region in xy_polygons:
            reverted_region = []
            for vertex in region:
                x, y = vertex[0], vertex[1]
                lon, lat = self.xy_to_lonlat(x, y)
                reverted_region.append([lon, lat])
            reverted.append(reverted_region)
        return reverted

    @staticmethod
    def save_polygons(data, file_path: str) -> None:
        """将多边形数据以 ``repr()`` 字符串形式写入文件。

        来自 ``map_modified.py`` 的 ``save_list_to_file``。写出的内容是有效的
        Python 字面量表达式，可被 ``ast.literal_eval`` 安全还原。

        Parameters
        ----------
        data : list
            任意可被 ``repr()`` 序列化的多边形数据。
        file_path : str
            输出文件路径。
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(repr(data))
        print(f"列表已成功保存到文件：{file_path}")


# 模块级便捷实例：默认威海海域转换器，便于直接 ``from env.geo_coordinate
# import default_converter`` 后调用，无需手动构造。
default_converter = GeoConverter()
