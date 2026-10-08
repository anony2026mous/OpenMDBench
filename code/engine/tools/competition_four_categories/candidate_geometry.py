"""Conservative data-only collision proxies for the frozen exact-sweep API."""
from copy import deepcopy
import math

SURFACE_SHAPE_REF = "shape.competition-picket-sphere@1.0.0"
SITE_SHAPE_REF = "shape.competition-site-sphere@1.0.0"
SITE_PLATFORM_REF = "platform.competition-shore-site@1.0.0"


def enclosing_sphere(resource, exact_ref):
    source = resource["content"]
    if source.get("shape") not in {"aabb", "obb"}:
        raise ValueError("conservative proxy requires declared box extents")
    extents = source.get("half_extents_m")
    if not isinstance(extents, (list, tuple)) or len(extents) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in extents):
        raise ValueError("invalid source collision extent")
    radius = math.sqrt(sum(x*x for x in extents))
    result = deepcopy(resource)
    identifier, version = exact_ref.rsplit("@", 1)
    result.update(id=identifier, version=version)
    result["content"] = {k: deepcopy(v) for k,v in source.items() if k not in {"shape", "half_extents_m"}}
    result["content"].update(shape="sphere", radius_m=radius)
    return result


def resources(templates):
    vessel = enclosing_sphere(templates["shape.picket-usv"], SURFACE_SHAPE_REF)
    site = enclosing_sphere(templates["shape.fixed-site"], SITE_SHAPE_REF)
    platform = deepcopy(templates["platform.shore-defence-site"])
    platform.update(id=SITE_PLATFORM_REF.split("@")[0], version="1.0.0")
    platform["content"]["collision_shape_ref"] = SITE_SHAPE_REF
    return [vessel, site, platform]
