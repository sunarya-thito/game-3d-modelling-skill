"""Small, explicit surface-production helpers for Blender 4.2.

The deterministic triangle atlas is intentionally conservative: no overlap,
uniform world-space density, and independently extended chart gutters, at the
cost of many islands and unused pixels. It is not a production atlas optimizer.
Run with Blender's Python. Only the standard library and Blender are required.
"""

from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import struct
import zlib

import bpy
from mathutils import Vector


def _mesh(obj):
    if obj.type != "MESH" or not obj.data.polygons:
        raise ValueError(f"{obj.name}: a nonempty mesh is required")
    if obj.mode != "OBJECT":
        raise ValueError(f"{obj.name}: finish editing before surface production")
    if any(mod.show_render or mod.show_viewport for mod in obj.modifiers):
        raise ValueError(f"{obj.name}: apply or disable modifiers before measuring UVs")
    return obj.data


def smart_unwrap(obj, texture_size=512, padding_px=8, uv_name="SurfaceUV"):
    """Run Smart UV Project with explicit selection, active object and mode.

    Padding is a requested island margin, NOT a certified minimum. Use the
    triangle atlas below when a guaranteed independent gutter is required.
    Blender's packing may change between versions; pin Blender for this route.
    The original Object-mode selection/active object is restored on exit.
    """
    mesh = _mesh(obj)
    if bpy.context.mode != "OBJECT":
        raise ValueError("smart_unwrap requires Object mode before invocation")
    if texture_size < 16 or not 0 < padding_px < texture_size / 4:
        raise ValueError("invalid texture size or requested padding")
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    uv = mesh.uv_layers.get(uv_name) or mesh.uv_layers.new(name=uv_name)
    mesh.uv_layers.active = uv
    uv.active_render = True
    try:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(
            angle_limit=math.radians(66),
            island_margin=padding_px / texture_size,
            correct_aspect=False,
            scale_to_bounds=True,
        )
    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for previous in selected:
            previous.select_set(True)
        bpy.context.view_layer.objects.active = active
    return uv_report(obj, texture_size, texture_size, uv_name)


def triangle_atlas(objects, texture_size=512, gutter_px=8, uv_name="SurfaceUV"):
    """Assign one un-stretched, uniformly scaled triangle to each atlas cell.

    Input meshes must already be triangulated. Geometry is never changed.
    World-space lengths include object scale. The returned JSON-compatible plan
    is consumed by paint_atlas; rebuilding in the same version is deterministic.
    Each triangle stays at least gutter_px + 1 pixels inside its own cell.
    """
    if texture_size < 16 or gutter_px < 1:
        raise ValueError("texture_size >= 16 and gutter_px >= 1 are required")
    if not objects or len({o.name for o in objects}) != len(objects):
        raise ValueError("provide nonempty, uniquely named mesh objects")
    if len({obj.data for obj in objects}) != len(objects):
        raise ValueError("atlas objects must have single-user mesh data")
    bpy.context.view_layer.update()
    charts = []
    for piece_index, obj in enumerate(objects):
        mesh = _mesh(obj)
        uv = mesh.uv_layers.get(uv_name) or mesh.uv_layers.new(name=uv_name)
        mesh.uv_layers.active = uv
        uv.active_render = True
        for face in mesh.polygons:
            if len(face.vertices) != 3:
                raise ValueError(f"{obj.name}: triangulate final geometry first")
            loops = list(face.loop_indices)
            points = [obj.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co for i in loops]
            if any(not math.isfinite(value) for point in points for value in point):
                raise ValueError(f"{obj.name}: nonfinite world-space point")
            edge = max(range(3), key=lambda i: (points[(i + 1) % 3] - points[i]).length_squared)
            order = [edge, (edge + 1) % 3, (edge + 2) % 3]
            points, loops = [points[i] for i in order], [loops[i] for i in order]
            xaxis = points[1] - points[0]
            length = xaxis.length
            normal = xaxis.cross(points[2] - points[0])
            if length < 1e-9 or normal.length < 1e-10:
                raise ValueError(f"{obj.name}: degenerate triangle {face.index}")
            xaxis /= length
            normal.normalize()
            delta = points[2] - points[0]
            x = delta.dot(xaxis)
            y = delta.dot(normal.cross(xaxis))
            charts.append({
                "object": obj.name, "piece": piece_index, "polygon": face.index,
                "loops": loops, "points": [list(p) for p in points],
                "normal": list(normal), "flat": [[0.0, 0.0], [length, 0.0], [x, y]],
            })
    # Deterministic shelf packing gives narrow/short triangles appropriately
    # sized cells instead of spending a full largest-triangle cell on each one.
    # Binary search chooses the common world-to-pixel scale; it is still a
    # deliberately simple rectangle packer, not globally optimal UV packing.
    def pack(scale):
        rectangles = [(max(1, math.ceil(chart["flat"][1][0] * scale)) + 2 * (gutter_px + 1),
                       max(1, math.ceil(chart["flat"][2][1] * scale)) + 2 * (gutter_px + 1), index)
                      for index, chart in enumerate(charts)]
        rectangles.sort(key=lambda rect: (-rect[1], -rect[0], rect[2]))
        x, y, row_height = 0, 0, 0
        cells = {}
        for width, height, index in rectangles:
            if width > texture_size or height > texture_size:
                return None
            if x + width > texture_size:
                x, y, row_height = 0, y + row_height, 0
            if y + height > texture_size:
                return None
            cells[index] = [x, y, x + width, y + height]
            x += width
            row_height = max(row_height, height)
        return cells
    if pack(0.0) is None:
        raise ValueError("atlas too small for triangle count and requested gutters")
    low, high = 0.0, texture_size / max(chart["flat"][1][0] for chart in charts)
    for _ in range(40):
        middle = (low + high) * 0.5
        if pack(middle) is None:
            high = middle
        else:
            low = middle
    scale = low
    if scale < 1e-6:
        raise ValueError("atlas has no usable interior at the requested gutter")
    cells = pack(scale)
    by_name = {o.name: o for o in objects}
    for index, chart in enumerate(charts):
        chart["cell"] = cells[index]
        x0, y0, _x1, _y1 = chart["cell"]
        chart["pixels"] = [[x0 + gutter_px + 1 + x * scale, y0 + gutter_px + 1 + y * scale]
                           for x, y in chart.pop("flat")]
        data = by_name[chart["object"]].data.uv_layers[uv_name].data
        for loop, point in zip(chart["loops"], chart["pixels"]):
            data[loop].uv = (point[0] / texture_size, point[1] / texture_size)
    return {
        "method": "independent_triangle_cells", "texture_size": texture_size,
        "gutter_px": gutter_px, "minimum_cell_clearance_px": gutter_px + 1,
        "uv_name": uv_name, "density_px_per_world_unit": scale,
        "charts": charts,
    }


def uv_report(obj, width, height=None, uv_name=None):
    """Measure world/UV areas, px/world-unit density, and Jacobian anisotropy.

    Anisotropy is sigma_max / sigma_min of the world-to-pixel Jacobian; 1 means
    no directional stretch. This is not a UV overlap or inter-island gap test.
    Degenerate world/UV triangles and nonfinite/out-of-range UVs are reported.
    """
    if width <= 0 or (height is not None and height <= 0):
        raise ValueError("texture dimensions must be positive")
    height = width if height is None else height
    mesh = _mesh(obj)
    mesh.calc_loop_triangles()
    layer = mesh.uv_layers.get(uv_name) if uv_name else mesh.uv_layers.active
    result = {"object": obj.name, "triangles": len(mesh.loop_triangles),
              "missing_uv": layer is None, "degenerate_world_triangles": 0,
              "degenerate_uv_triangles": 0, "nonfinite_uv_loops": 0,
              "outside_unit_square_loops": 0, "world_area": 0.0, "uv_area": 0.0}
    if layer is None:
        return result
    for loop in layer.data:
        if not all(math.isfinite(v) for v in loop.uv):
            result["nonfinite_uv_loops"] += 1
        elif any(v < -1e-6 or v > 1 + 1e-6 for v in loop.uv):
            result["outside_unit_square_loops"] += 1
    densities, stretches = [], []
    for tri in mesh.loop_triangles:
        a, b, c = [obj.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
        u, v, w = [Vector(layer.data[i].uv) for i in tri.loops]
        e1, e2 = b - a, c - a
        world_area = e1.cross(e2).length * 0.5
        uv1, uv2 = v - u, w - u
        uv_area = abs(uv1.x * uv2.y - uv1.y * uv2.x) * 0.5
        result["world_area"] += world_area
        result["uv_area"] += uv_area if math.isfinite(uv_area) else 0.0
        if world_area < 1e-12:
            result["degenerate_world_triangles"] += 1
            continue
        if not math.isfinite(uv_area) or uv_area < 1e-12:
            result["degenerate_uv_triangles"] += 1
            continue
        density = math.sqrt(uv_area * width * height / world_area)
        length = e1.length
        x, y = e2.dot(e1 / length), 2 * world_area / length
        j00, j10 = uv1.x * width / length, uv1.y * height / length
        j01, j11 = (uv2.x * width - j00 * x) / y, (uv2.y * height - j10 * x) / y
        aa, bb, ab = j00 * j00 + j10 * j10, j01 * j01 + j11 * j11, j00 * j01 + j10 * j11
        trace, delta = aa + bb, math.sqrt(max(0.0, (aa - bb) ** 2 + 4 * ab * ab))
        smallest, largest = (trace - delta) * 0.5, (trace + delta) * 0.5
        stretches.append(math.sqrt(largest / smallest) if smallest > 1e-16 else 1e30)
        densities.append((density, world_area))
    if densities:
        result["density_px_per_world_unit"] = {
            "min": min(d for d, _ in densities), "max": max(d for d, _ in densities),
            "area_weighted_mean": sum(d * a for d, a in densities) / sum(a for _, a in densities),
        }
        result["stretch_anisotropy"] = {"min": min(stretches), "max": max(stretches)}
    return result


def require_uv_metrics(report, density_min=1.0, density_max=1e6, stretch_max=1.02):
    """Fail a declared surface gate rather than silently repairing UVs."""
    bad = [key for key in ("missing_uv", "degenerate_world_triangles", "degenerate_uv_triangles",
                          "nonfinite_uv_loops", "outside_unit_square_loops") if report.get(key)]
    density = report.get("density_px_per_world_unit")
    stretch = report.get("stretch_anisotropy")
    if not density or not density_min <= density["min"] <= density["max"] <= density_max:
        bad.append("density outside contract")
    if not stretch or stretch["max"] > stretch_max:
        bad.append("stretch outside contract")
    if bad:
        raise ValueError(f"{report['object']}: UV gate failed: {', '.join(bad)}")


def _closest_weights(x, y, triangle):
    """Barycentric weights of a point or its closest point on a 2D triangle."""
    (ax, ay), (bx, by), (cx, cy) = triangle
    determinant = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    a = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / determinant
    b = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / determinant
    weights = (a, b, 1 - a - b)
    if min(weights) >= 0:
        return weights
    best = None
    for i, j in ((0, 1), (1, 2), (2, 0)):
        px, py = triangle[i]
        qx, qy = triangle[j]
        dx, dy = qx - px, qy - py
        t = max(0.0, min(1.0, ((x - px) * dx + (y - py) * dy) / (dx * dx + dy * dy)))
        distance = (x - px - t * dx) ** 2 + (y - py - t * dy) ** 2
        if best is None or distance < best[0]:
            answer = [0.0, 0.0, 0.0]
            answer[i], answer[j] = 1 - t, t
            best = (distance, answer)
    return best[1]


def _srgb(value):
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def save_rgba_png(path, width, height, pixels, color_space="sRGB"):
    """Write deterministic RGBA8 PNG from bottom-up LINEAR color or data pixels.

    RGB color is explicitly encoded to sRGB; alpha and Non-Color data are not.
    This avoids ambiguity about generated-image buffers and display transforms.
    No view transform, baked lighting, or external imaging dependency is used.
    """
    if color_space not in {"sRGB", "Non-Color"}:
        raise ValueError("supported color spaces are sRGB and Non-Color")
    if len(pixels) != width * height * 4 or min(width, height) <= 0:
        raise ValueError("pixel array does not match image dimensions")
    raw = bytearray()
    for y in reversed(range(height)):
        raw.append(0)
        for value_index in range(y * width * 4, (y + 1) * width * 4):
            value = float(pixels[value_index])
            if not math.isfinite(value):
                raise ValueError("nonfinite texture pixel")
            value = max(0.0, min(1.0, value))
            if color_space == "sRGB" and value_index % 4 != 3:
                value = _srgb(value)
            raw.append(round(value * 255))
    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content) & 0xFFFFFFFF)
    payload = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    if color_space == "sRGB":
        payload += chunk(b"sRGB", b"\0")
    payload += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = color_space
    return image


def paint_atlas(plan, destination, painter, color_space="sRGB"):
    """Paint every chart cell, extending nearest-edge colors through its gutter.

    painter(world_position, world_normal, piece_index) returns LINEAR RGBA color
    for sRGB images or unencoded RGBA data for Non-Color images. Positions are
    interpolated in world space, so broad layers can remain coherent at seams.
    Each cell is isolated: no dilation can copy another piece's colors.
    """
    size = plan["texture_size"]
    pixels = array("f", [0.0, 0.0, 0.0, 1.0]) * (size * size)
    for chart in plan["charts"]:
        x0, y0, x1, y1 = chart["cell"]
        points = chart["points"]
        for y in range(y0, y1):
            for x in range(x0, x1):
                weights = _closest_weights(x + 0.5, y + 0.5, chart["pixels"])
                position = tuple(sum(weights[i] * points[i][axis] for i in range(3)) for axis in range(3))
                rgba = painter(position, tuple(chart["normal"]), chart["piece"])
                if len(rgba) != 4:
                    raise ValueError("painter must return four linear RGBA components")
                start = (y * size + x) * 4
                pixels[start:start + 4] = array("f", rgba)
    return save_rgba_png(destination, size, size, pixels, color_space)


def principled_textured(name, albedo, roughness=0.65, metallic=0.0,
                       roughness_image=None, metallic_image=None, normal_image=None):
    """Create an exporter-friendly Principled graph with explicit channel roles.

    Albedo: sRGB Color. Roughness: Non-Color green. Metallic: Non-Color blue.
    Normal: Non-Color RGB through a tangent-space Normal Map node. Scalar maps
    can be grayscale; shared roughness/metallic input may use packed G/B data.
    No AO, alpha blending, transmission, animation, or procedural shader bake.
    """
    if albedo is None:
        raise ValueError("an albedo image is required")
    if albedo in [im for im in (roughness_image, metallic_image, normal_image) if im is not None]:
        raise ValueError("one image cannot serve both sRGB color and Non-Color data")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    def texture(image, role, color_space):
        image.colorspace_settings.name = color_space
        node = nodes.new("ShaderNodeTexImage")
        node.name, node.label, node.image = role, role, image
        node.interpolation, node.extension = "Linear", "EXTEND"
        return node
    color = texture(albedo, "Albedo_sRGB", "sRGB")
    links.new(color.outputs["Color"], shader.inputs["Base Color"])
    for image, socket, channel in ((roughness_image, "Roughness", "Green"),
                                   (metallic_image, "Metallic", "Blue")):
        if image:
            node = texture(image, socket + "_data", "Non-Color")
            separate = nodes.new("ShaderNodeSeparateColor")
            separate.mode = "RGB"
            links.new(node.outputs["Color"], separate.inputs["Color"])
            links.new(separate.outputs[channel], shader.inputs[socket])
    if normal_image:
        node = texture(normal_image, "Normal_data", "Non-Color")
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(node.outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return material


def glb_surface_report(path, require_data_texture=False):
    """Inspect the emitted GLB JSON, not the authoring scene. Raise on loss.

    This intentionally accepts only embedded GLB images and requires a base
    color texture on every primitive. It is a focused surface gate, not a full
    glTF validator or material equivalence proof.
    """
    blob = Path(path).read_bytes()
    if len(blob) < 20 or blob[:4] != b"glTF" or struct.unpack_from("<I", blob, 4)[0] != 2:
        raise ValueError("expected a glTF 2.0 binary")
    length, kind = struct.unpack_from("<II", blob, 12)
    if kind != 0x4E4F534A:
        raise ValueError("GLB has no first JSON chunk")
    document = json.loads(blob[20:20 + length])
    materials, textures, images = (document.get(key, []) for key in ("materials", "textures", "images"))
    failures, primitives = [], 0
    used_images = set()
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            primitives += 1
            if "TEXCOORD_0" not in primitive["attributes"]:
                failures.append("primitive missing TEXCOORD_0")
            material_index = primitive.get("material")
            if material_index is None or material_index >= len(materials):
                failures.append("primitive missing material")
                continue
            pbr = materials[material_index].get("pbrMetallicRoughness", {})
            roles = ["baseColorTexture"] + (["metallicRoughnessTexture"] if require_data_texture else [])
            for role in roles:
                reference = pbr.get(role)
                if reference is None or reference.get("index", -1) not in range(len(textures)):
                    failures.append(f"material missing {role}")
                    continue
                if reference.get("texCoord", 0) != 0:
                    failures.append("surface gate currently requires UV set 0")
                image_index = textures[reference["index"]].get("source", -1)
                if image_index not in range(len(images)):
                    failures.append("texture missing image source")
                    continue
                image = images[image_index]
                if "bufferView" not in image or image.get("mimeType") not in {"image/png", "image/jpeg"}:
                    failures.append("texture image is not embedded PNG/JPEG")
                elif image["bufferView"] not in range(len(document.get("bufferViews", []))):
                    failures.append("image bufferView is invalid")
                used_images.add(image_index)
    if not primitives:
        failures.append("GLB contains no mesh primitives")
    if failures:
        raise ValueError("GLB surface gate failed: " + "; ".join(sorted(set(failures))))
    return {"primitives": primitives, "materials": len(materials), "textures": len(textures),
            "images": len(images), "used_images": sorted(used_images),
            "require_data_texture": require_data_texture, "passed": True}


def _upstream_images(socket, seen=None):
    seen = set() if seen is None else seen
    result = set()
    for link in socket.links:
        node = link.from_node
        if node in seen:
            continue
        seen.add(node)
        if node.type == "TEX_IMAGE" and node.image:
            result.add(node.image)
        for input_socket in node.inputs:
            result.update(_upstream_images(input_socket, seen))
    return result


def imported_surface_report(objects, texture_size, require_data_texture=False):
    """Check imported mesh UVs and images actually linked to Principled inputs."""
    objects = [obj for obj in objects if obj.type == "MESH"]
    if not objects:
        raise ValueError("no imported surface meshes")
    report = {"uv": [], "materials": {}}
    for obj in objects:
        measured = uv_report(obj, texture_size)
        require_uv_metrics(measured, stretch_max=1e6)
        report["uv"].append(measured)
        for index in {face.material_index for face in obj.data.polygons}:
            if index >= len(obj.data.materials) or obj.data.materials[index] is None:
                raise ValueError(f"{obj.name}: missing imported material")
            material = obj.data.materials[index]
            if not material.use_nodes:
                raise ValueError(f"{material.name}: missing node graph")
            shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
            if shader is None:
                raise ValueError(f"{material.name}: missing Principled shader")
            channels = {}
            for socket, expected_space in [("Base Color", "sRGB")] + ([("Roughness", "Non-Color")] if require_data_texture else []):
                images = _upstream_images(shader.inputs[socket])
                if not images:
                    raise ValueError(f"{material.name}: no image linked to {socket}")
                for image in images:
                    if min(image.size) <= 0 or not image.has_data:
                        raise ValueError(f"{image.name}: imported image has no pixels")
                    if image.colorspace_settings.name != expected_space:
                        raise ValueError(f"{image.name}: wrong color space for {socket}")
                    if tuple(image.size) != (texture_size, texture_size):
                        raise ValueError(f"{image.name}: unexpected imported dimensions {tuple(image.size)}")
                channels[socket] = sorted(image.name for image in images)
            report["materials"][material.name] = channels
    report["passed"] = True
    return report
