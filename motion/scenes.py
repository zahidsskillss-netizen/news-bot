"""
Bisram TV — د خبرونو ۳D موشن ګرافیک (Blender / Cycles)
کارول:
  python scenes.py <scene> <out_dir> [start end] [--preview]
  scene: intro | outro | lt_in | lt_out | lt_hold | stinger
"""
import math
import os
import random
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")

BLUE = (0.013, 0.30, 0.89)        # #2196F3 (linear)
NAVY = (0.003, 0.010, 0.040)
RED = (0.78, 0.04, 0.035)
WHITE = (1, 1, 1)
FPS = 30


# ------------------------------------------------------------ بنسټ
def reset(transparent=False, preview=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 6 if preview else 28
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 4
    s.cycles.transparent_max_bounces = 8
    s.render.resolution_x, s.render.resolution_y = (480, 270) if preview else (1920, 1080)
    s.render.fps = FPS
    s.render.film_transparent = transparent
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.render.use_motion_blur = True
    s.render.motion_blur_shutter = 0.5
    # نړۍ: تور شین
    w = bpy.data.worlds.new("W")
    s.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*NAVY, 1)
    bg.inputs[1].default_value = 1.0
    return s


def key_interp(kind):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = kind


def mat(name, color=(1, 1, 1), metal=0.0, rough=0.4, emit=None, emit_strength=0.0,
        coat=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Alpha"].default_value = alpha
    p.inputs["Transmission Weight"].default_value = transmission
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    return m


def image_mat(name, path, strength=1.0, tint=None):
    """انځور (PNG د alpha سره) د ځلېدونکي مواد په توګه."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.interpolation = "Cubic"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if tint:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = (*tint, 1)
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1
        nt.links.new(tex.outputs["Color"], mul.inputs[6])
        nt.links.new(rgb.outputs[0], mul.inputs[7])
        nt.links.new(mul.outputs[2], em.inputs[0])
    else:
        nt.links.new(tex.outputs["Color"], em.inputs[0])
    # د Alpha لپاره د ځانګړې سلایډر (fade) ورزیاتول
    fade = nt.nodes.new("ShaderNodeMath")
    fade.operation = "MULTIPLY"
    fade.inputs[1].default_value = 1.0
    fade.name = "FADE"
    nt.links.new(tex.outputs["Alpha"], fade.inputs[0])
    nt.links.new(fade.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m, tex.image.size[:]


def plane(name, w, h, material, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(material)
    return o


def image_plane(name, path, height, loc=(0, 0, 0), strength=1.0, tint=None):
    m, (iw, ih) = image_mat(name + "_m", path, strength, tint)
    return plane(name, height * iw / ih, height, m, loc), m


def box(name, size, material, loc=(0, 0, 0), bevel=0.0, segs=6):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
        bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def camera(loc, look_at=(0, 0, 0), lens=35):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.data.lens = lens
    t = bpy.data.objects.new("cam_target", None)
    bpy.context.collection.objects.link(t)
    t.location = look_at
    con = c.constraints.new("TRACK_TO")
    con.target = t
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    bpy.context.scene.camera = c
    return c, t


def area_light(loc, energy, size=4, color=(1, 1, 1), look=(0, 0, 0)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    l.visible_camera = False
    con = l.constraints.new("TRACK_TO")
    t = bpy.data.objects.new("lt_t", None)
    bpy.context.collection.objects.link(t)
    t.location = look
    con.target = t
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return l


def kf(obj, frame, **props):
    for k, v in props.items():
        setattr(obj, k, v)
        obj.keyframe_insert(data_path=k, frame=frame)


def kf_fade(material, frame, value):
    n = material.node_tree.nodes["FADE"]
    n.inputs[1].default_value = value
    n.inputs[1].keyframe_insert("default_value", frame=frame)


# ------------------------------------------------------------ ګډې برخې
def globe(loc=(0, 22, 0), radius=10, strength=1.6, spin_frames=180, spin=math.radians(40)):
    """د کرې تارونه (wireframe) — د نړیوالو خبرونو نښه."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=radius, location=loc)
    g = bpy.context.object
    g.name = "globe"
    wf = g.modifiers.new("wf", "WIREFRAME")
    wf.thickness = 0.016
    g.data.materials.append(mat("globe_m", BLUE, emit=(0.08, 0.38, 1.0), emit_strength=strength))
    g.rotation_euler = (math.radians(18), 0, 0)
    key_interp("LINEAR")
    kf(g, 1, rotation_euler=(math.radians(18), 0, 0))
    kf(g, spin_frames, rotation_euler=(math.radians(18), 0, spin))
    key_interp("BEZIER")
    # د کرې شاوخوا حلقه
    bpy.ops.mesh.primitive_torus_add(major_radius=radius * 1.25, minor_radius=0.03,
                                     location=loc, rotation=(math.radians(75), math.radians(-15), 0))
    ring = bpy.context.object
    ring.data.materials.append(mat("ring_m", WHITE, emit=(0.35, 0.65, 1.0), emit_strength=2.5))
    return g


def streaks(n=40, frames=(1, 60), seed=3, z_spread=7, x_spread=16, speed_len=70):
    """د رڼا کرښې چې کمرې ته په چټکۍ راځي."""
    rnd = random.Random(seed)
    m_b = mat("streak_b", BLUE, emit=(0.25, 0.6, 1.0), emit_strength=25)
    m_w = mat("streak_w", WHITE, emit=(1, 1, 1), emit_strength=18)
    m_r = mat("streak_r", RED, emit=(1.0, 0.12, 0.08), emit_strength=18)
    key_interp("LINEAR")
    for i in range(n):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.025, depth=rnd.uniform(3, 9),
                                            rotation=(math.pi / 2, 0, 0))
        s = bpy.context.object
        s.data.materials.append(rnd.choice([m_b, m_b, m_w, m_r]))
        x = rnd.uniform(-x_spread, x_spread)
        z = rnd.uniform(-z_spread, z_spread)
        if abs(x) < 3 and abs(z) < 2:
            x += 5 * (1 if x >= 0 else -1)
        start = rnd.randint(frames[0], frames[1] - 15)
        dur = rnd.randint(10, 22)
        kf(s, start - 1, location=(x, 60, z), hide_render=True)
        kf(s, start, location=(x, 60, z), hide_render=False)
        kf(s, start + dur, location=(x, 60 - speed_len, z))
        kf(s, start + dur + 1, hide_render=True)
    key_interp("BEZIER")


def particles(n=120, seed=7, area=(30, 30, 14), y0=5, strength=8):
    rnd = random.Random(seed)
    m = mat("dust", WHITE, emit=(0.5, 0.8, 1.0), emit_strength=strength)
    key_interp("LINEAR")
    for i in range(n):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rnd.uniform(0.015, 0.05))
        p = bpy.context.object
        p.data.materials.append(m)
        x, y, z = rnd.uniform(-area[0], area[0]), rnd.uniform(y0, y0 + area[1]), rnd.uniform(-area[2], area[2])
        kf(p, 1, location=(x, y, z))
        kf(p, 200, location=(x + rnd.uniform(-1, 1), y - rnd.uniform(2, 6), z + rnd.uniform(-0.5, 1)))
    key_interp("BEZIER")


def badge(loc=(0, 0, 0), w=6.2, h=2.9):
    """د Bisram TV ۳D تخته: شین ځلانده بکس، مخ ته لوګو."""
    body = box("badge", (w, 0.45, h), mat("badge_m", (0.004, 0.12, 0.62), metal=0.25, rough=0.22, coat=0.6,
                                             emit=(0.01, 0.2, 0.9), emit_strength=0.12), loc, bevel=0.22, segs=8)
    # سپینه څنډه
    rim = box("rim", (w + 0.12, 0.3, h + 0.12), mat("rim_m", WHITE, metal=1, rough=0.15,
                                                     emit=(0.7, 0.85, 1), emit_strength=0.6),
              (loc[0], loc[1] + 0.12, loc[2]), bevel=0.26, segs=8)
    lg, lg_m = image_plane("logo", os.path.join(A, "logo_hd.png"), h * 0.72,
                           (loc[0], loc[1] - 0.24, loc[2]), strength=2.4)
    for o in (rim, lg):
        o.parent = body
        o.matrix_parent_inverse = body.matrix_world.inverted()
    return body, lg_m


def glass_panels(n=8, seed=11, final_y=4, frames=(10, 70)):
    rnd = random.Random(seed)
    m = mat("glass", (0.01, 0.05, 0.2), metal=0.5, rough=0.1, coat=1, alpha=0.55,
            emit=(0.04, 0.22, 0.9), emit_strength=0.35)
    m_edge = mat("glass_edge", WHITE, emit=(0.3, 0.65, 1.0), emit_strength=6)
    out = []
    for i in range(n):
        ang = (i / n) * math.tau
        fx, fz = math.cos(ang) * rnd.uniform(9.5, 12), math.sin(ang) * rnd.uniform(4.5, 6.5)
        pnl = box(f"panel{i}", (rnd.uniform(2.2, 3.6), 0.06, rnd.uniform(1.2, 2.0)), m,
                  bevel=0.04, segs=3)
        edge = box(f"edge{i}", (0.05, 0.08, pnl.dimensions.z), m_edge)
        edge.location.x = -pnl.dimensions.x / 2
        edge.parent = pnl
        st = rnd.randint(frames[0], frames[1] - 30)
        kf(pnl, st, location=(fx * 3.5, final_y + 40, fz * 3),
           rotation_euler=(rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(-2, 2)))
        kf(pnl, st + 35, location=(fx, final_y + rnd.uniform(2, 6), fz),
           rotation_euler=(0, 0, math.atan2(fz, fx) * 0.15))
        out.append(pnl)
    return out


# ------------------------------------------------------------ صحنې
def scene_intro(preview):
    s = reset(preview=preview)
    s.frame_start, s.frame_end = 1, 180
    cam, tgt = camera((0, -16, 0.6), (0, 0, 0.3), lens=40)
    kf(cam, 1, location=(-3.5, -24, 2.5))
    kf(cam, 110, location=(0.4, -15.5, 0.8))
    kf(cam, 180, location=(0, -14.2, 0.6))
    area_light((-8, -10, 8), 2500, 6, (0.8, 0.9, 1.0))
    area_light((9, -6, -2), 900, 5, (0.3, 0.6, 1.0))
    sweep = area_light((-12, -6, 2), 0, 1.2, (1, 1, 1), look=(0, 0, 0))
    sweep.data.shape = "RECTANGLE"
    sweep.data.size, sweep.data.size_y = 0.4, 10
    kf(sweep, 110, location=(-12, -6, 2))
    sweep.data.energy = 0
    sweep.data.keyframe_insert("energy", frame=108)
    sweep.data.energy = 9000
    sweep.data.keyframe_insert("energy", frame=112)
    kf(sweep, 150, location=(12, -6, 2))
    sweep.data.keyframe_insert("energy", frame=148)
    sweep.data.energy = 0
    sweep.data.keyframe_insert("energy", frame=154)

    globe(loc=(0, 26, 0), radius=12, spin_frames=180)
    streaks(n=46, frames=(1, 95))
    particles()
    glass_panels(frames=(15, 90))

    b, logo_m = badge((0, 0, 0.6))
    kf(b, 55, location=(0, 30, 0.6), rotation_euler=(0, 0, math.radians(-200)), scale=(0.3, 0.3, 0.3))
    kf(b, 105, location=(0, 0, 0.6), rotation_euler=(math.radians(4), 0, math.radians(-8)), scale=(1, 1, 1))
    kf(b, 180, location=(0, 0, 0.6), rotation_euler=(0, 0, math.radians(3)))

    # «د ورځې خبرونه» او سره کرښه
    t, t_m = image_plane("daily", os.path.join(A, "t_daily.png"), 1.35, (0, -0.4, -1.75), strength=2.2)
    kf_fade(t_m, 112, 0.0)
    kf_fade(t_m, 128, 1.0)
    kf(t, 112, location=(0, -0.4, -2.3))
    kf(t, 132, location=(0, -0.4, -1.75))
    bar = box("redbar", (5.2, 0.12, 0.1), mat("red_m", RED, rough=0.3, emit=(0.9, 0.02, 0.01), emit_strength=0.9),
              (0, -0.3, -2.55))
    kf(bar, 118, scale=(0.001, 1, 1))
    kf(bar, 140, scale=(1, 1, 1))
    # د زمکې ځلانده سطحه
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 10, -5))
    bpy.context.object.data.materials.append(mat("floor", (0.004, 0.012, 0.04), metal=0.6, rough=0.12))
    return s


def scene_outro(preview):
    s = reset(preview=preview)
    s.frame_start, s.frame_end = 1, 180
    cam, tgt = camera((0, -16, 0.5), (0, 0, 0.2), lens=40)
    kf(cam, 1, location=(2.5, -18, 1.6))
    kf(cam, 180, location=(-0.6, -15.3, 0.4))
    area_light((-8, -10, 8), 2500, 6, (0.8, 0.9, 1.0))
    area_light((9, -6, -2), 900, 5, (0.3, 0.6, 1.0))
    globe(loc=(0, 26, 0), radius=12, spin_frames=180, spin=math.radians(-35))
    particles(seed=21)
    streaks(n=18, frames=(1, 60), seed=9)

    b, _ = badge((0, 0, 2.3), w=4.6, h=2.15)
    kf(b, 1, location=(0, 0, 2.3), rotation_euler=(0, 0, math.radians(180)), scale=(0.01, 0.01, 0.01))
    kf(b, 30, location=(0, 0, 2.3), rotation_euler=(0, 0, math.radians(-6)), scale=(1, 1, 1))
    kf(b, 180, location=(0, 0, 2.3), rotation_euler=(0, 0, math.radians(4)))

    t, tm = image_plane("sub_txt", os.path.join(A, "t_sub.png"), 0.85, (0, -0.4, 0.2), strength=1.4)
    kf_fade(tm, 28, 0)
    kf_fade(tm, 44, 1)
    kf(t, 28, location=(0, -0.4, -0.3))
    kf(t, 46, location=(0, -0.4, 0.2))

    # سور SUBSCRIBE تڼۍ
    btn = box("btn", (3.6, 0.45, 0.95), mat("btn_m", RED, rough=0.25, coat=1,
                                             emit=(1, 0.08, 0.05), emit_strength=0.6),
              (0, 0, -1.25), bevel=0.42, segs=10)
    bt, btm = image_plane("btn_txt", os.path.join(A, "t_subscribe.png"), 0.62, (0, -0.24, -1.25), strength=2)
    bt.parent = btn
    bt.matrix_parent_inverse = btn.matrix_world.inverted()
    kf(btn, 40, scale=(0.001, 0.001, 0.001), rotation_euler=(math.radians(90), 0, 0))
    kf(btn, 58, scale=(1.12, 1.12, 1.12), rotation_euler=(0, 0, 0))
    kf(btn, 66, scale=(1, 1, 1))
    # «ټک» — تڼۍ کښته کېږي
    kf(btn, 96, scale=(1, 1, 1), location=(0, 0, -1.25))
    kf(btn, 100, scale=(0.93, 0.93, 0.93), location=(0, 0.12, -1.25))
    kf(btn, 106, scale=(1, 1, 1), location=(0, 0, -1.25))

    h, hm = image_plane("handle", os.path.join(A, "t_handle.png"), 0.62, (0, -0.4, -2.55), strength=1.2,
                        tint=(0.55, 0.8, 1.0))
    kf_fade(hm, 62, 0)
    kf_fade(hm, 80, 1)

    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 10, -5))
    bpy.context.object.data.materials.append(mat("floor", (0.004, 0.012, 0.04), metal=0.6, rough=0.12))
    return s


def lower_third_rig(s):
    """د Lower third ۳D پټۍ (شفاف شالید). سرلیک وروسته په Python کې ورځي."""
    cam, _ = camera((0, -20, 0), (0, 0, 0), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 16
    area_light((-6, -10, 6), 1800, 6)
    area_light((6, -8, -3), 600, 5, (0.4, 0.7, 1))
    # ۱۶:۹ ortho → پلنوالی ۱۶، لوړوالی ۹ (z له −4.5 تر 4.5)
    root = bpy.data.objects.new("lt_root", None)
    bpy.context.collection.objects.link(root)
    root.location = (-0.6, 0, -2.9)
    main = box("lt_main", (12.2, 0.35, 1.45), mat("lt_main_m", (0.003, 0.07, 0.42), metal=0.3, rough=0.22,
                                                    coat=0.8, emit=(0.01, 0.12, 0.6), emit_strength=0.25),
               (0.35, 0, 0), bevel=0.05, segs=4)
    label = box("lt_label", (2.7, 0.6, 1.85), mat("lt_label_m", (0.002, 0.012, 0.05), metal=0.4, rough=0.2,
                                                    coat=1), (6.75, -0.12, 0.05), bevel=0.12, segs=6)
    edge = box("lt_edge", (0.09, 0.62, 1.85), mat("lt_edge_m", WHITE, emit=(0.3, 0.6, 1), emit_strength=5),
               (5.43, -0.14, 0.05))
    tag = box("lt_tag", (2.5, 0.4, 0.62), mat("lt_tag_m", RED, rough=0.3, coat=1,
                                               emit=(0.9, 0.03, 0.02), emit_strength=0.5),
              (4.0, -0.05, 1.05), bevel=0.05, segs=4)
    tag_t, _ = image_plane("lt_tag_t", os.path.join(A, "t_tazakhabar.png"), 0.6, (4.0, -0.27, 1.05), strength=2.0)
    strip = box("lt_strip", (12.2, 0.3, 0.09), mat("lt_strip_m", WHITE, emit=(0.8, 0.9, 1), emit_strength=2),
                (0.35, -0.05, -0.79))
    lg, _ = image_plane("lt_logo", os.path.join(A, "logo_hd.png"), 1.05, (6.75, -0.45, 0.05), strength=2.4)
    for o in (main, label, edge, tag, tag_t, strip, lg):
        o.parent = root
    tag_t.parent = tag
    tag_t.location = (0, -0.22, 0)
    lg.parent = label
    lg.location = (0, -0.33, 0)
    edge.parent = label
    edge.location = (-1.32, -0.02, 0)
    return root, main, label, strip, tag


def scene_lt_in(preview):
    s = reset(transparent=True, preview=preview)
    s.frame_start, s.frame_end = 1, 30
    root, main, label, strip, tag = lower_third_rig(s)
    kf(label, 1, location=(11, -0.12, 0.05), rotation_euler=(0, 0, math.radians(-90)))
    kf(label, 13, location=(6.75, -0.12, 0.05), rotation_euler=(0, 0, 0))
    kf(main, 5, scale=(0.001, 1, 1), location=(5.6, 0, 0), rotation_euler=(math.radians(-80), 0, 0))
    kf(main, 20, scale=(1, 1, 1), location=(0.35, 0, 0), rotation_euler=(0, 0, 0))
    kf(strip, 12, scale=(0.001, 1, 1), location=(5.6, -0.05, -0.79))
    kf(strip, 25, scale=(1, 1, 1), location=(0.35, -0.05, -0.79))
    kf(tag, 14, location=(4.0, -0.05, 0.3), rotation_euler=(math.radians(90), 0, 0))
    kf(tag, 26, location=(4.0, -0.05, 1.05), rotation_euler=(0, 0, 0))
    return s


def scene_lt_hold(preview):
    s = reset(transparent=True, preview=preview)
    s.frame_start, s.frame_end = 1, 1
    lower_third_rig(s)
    return s


def scene_lt_out(preview):
    s = reset(transparent=True, preview=preview)
    s.frame_start, s.frame_end = 1, 18
    root, main, label, strip, tag = lower_third_rig(s)
    kf(tag, 1, location=(4.0, -0.05, 1.05), rotation_euler=(0, 0, 0))
    kf(tag, 8, location=(4.0, -0.05, 0.3), rotation_euler=(math.radians(-90), 0, 0))
    kf(main, 2, scale=(1, 1, 1), location=(0.35, 0, 0), rotation_euler=(0, 0, 0))
    kf(main, 14, scale=(0.001, 1, 1), location=(5.6, 0, 0), rotation_euler=(math.radians(80), 0, 0))
    kf(strip, 1, scale=(1, 1, 1), location=(0.35, -0.05, -0.79))
    kf(strip, 10, scale=(0.001, 1, 1), location=(5.6, -0.05, -0.79))
    kf(label, 8, location=(6.75, -0.12, 0.05), rotation_euler=(0, 0, 0))
    kf(label, 18, location=(11, -0.12, 0.05), rotation_euler=(0, 0, math.radians(90)))
    return s


def scene_stinger(preview):
    """د خبرونو ترمنځ Transition: ۳D پینلونه ټوله پرده پټوي او بېرته ځي."""
    s = reset(transparent=True, preview=preview)
    s.frame_start, s.frame_end = 1, 24
    cam, _ = camera((0, -20, 0), (0, 0, 0), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 16
    area_light((-6, -10, 6), 2000, 6)
    m1 = mat("st1", BLUE, metal=0.2, rough=0.2, coat=1, emit=BLUE, emit_strength=0.3)
    m2 = mat("st2", NAVY, metal=0.4, rough=0.25, coat=1)
    m3 = mat("st3", RED, rough=0.25, coat=1, emit=(1, 0.08, 0.05), emit_strength=0.4)
    for i, (m, delay) in enumerate([(m3, 0), (m2, 2), (m1, 4)]):
        p = box(f"st{i}", (6, 0.3, 14), m, bevel=0.05)
        p.rotation_euler = (0, math.radians(-18), 0)
        kf(p, 1 + delay, location=(-14 - i * 0.3, -i * 0.4, 0), scale=(1, 1, 1))
        kf(p, 9 + delay, location=(0, -i * 0.4, 0), scale=(3.2, 1, 1))
        kf(p, 15 + delay, location=(0, -i * 0.4, 0), scale=(3.2, 1, 1))
        kf(p, 22 + delay, location=(15 + i * 0.3, -i * 0.4, 0), scale=(1, 1, 1))
    lg, lgm = image_plane("st_logo", os.path.join(A, "logo_hd.png"), 2.4, (0, -1.6, 0), strength=1.6)
    kf_fade(lgm, 8, 0)
    kf_fade(lgm, 11, 1)
    kf_fade(lgm, 15, 1)
    kf_fade(lgm, 18, 0)
    s.frame_end = 26
    return s


SCENES = {"intro": scene_intro, "outro": scene_outro, "lt_in": scene_lt_in,
          "lt_hold": scene_lt_hold, "lt_out": scene_lt_out, "stinger": scene_stinger}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    preview = "--preview" in sys.argv
    name, out_dir = args[0], args[1]
    s = SCENES[name](preview)
    start = int(args[2]) if len(args) > 2 else s.frame_start
    end = int(args[3]) if len(args) > 3 else s.frame_end
    frames = [int(x) for x in args[4].split(",")] if len(args) > 4 else range(start, end + 1)
    os.makedirs(out_dir, exist_ok=True)
    for f in frames:
        s.frame_set(f)
        s.render.filepath = os.path.join(out_dir, f"{name}_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {name} {f}", flush=True)
