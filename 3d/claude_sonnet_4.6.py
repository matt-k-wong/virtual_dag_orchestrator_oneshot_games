# game.py
#!/usr/bin/env python3
"""
AFTERBURNER ZERO — Pseudo-3D Flight Combat
Controls: WASD/Arrows=Move  SPACE=Fire  SHIFT=Boost  ESC=Quit
"""

# ── Bootstrap ──────────────────────────────────────────────────────────────
import sys, subprocess

def _install_pygame():
    for pkg in ("pygame-ce", "pygame"):
        try:
            __import__("pygame")
            return
        except ImportError:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                __import__("pygame")
                return
            except Exception:
                continue
    print("ERROR: Could not install pygame. Run:  pip install pygame-ce")
    sys.exit(1)

_install_pygame()
import pygame
import math, random
from collections import deque

# ── Display ────────────────────────────────────────────────────────────────
W, H = 1280, 720
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("AFTERBURNER ZERO")
clock  = pygame.time.Clock()
FPS    = 60

def _font(size, bold=False):
    for name in ("consolas", "courier new", "monospace", ""):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f: return f
        except Exception:
            pass
    return pygame.font.Font(None, size)

font_big = _font(66, bold=True)
font_med = _font(34, bold=True)
font_hud = _font(22, bold=True)
font_sm  = _font(18)

# ── Projection & World Constants ───────────────────────────────────────────
FOCAL        = 580       # focal length pixels
HORIZON_Y    = 238       # horizon screen-Y
CAM_HEIGHT   = 130       # camera Y above player
PLAYER_REL_Z = 230       # player's fixed rel_z

# ── Gameplay Tuning ────────────────────────────────────────────────────────
CAM_SPEED      = 750.0
PLAYER_SPEED   = 365.0
BULLET_SPEED   = 5200.0
BULLET_LIFE    = 4.0
ENEMY_SPD_BASE = 185.0
MISSILE_SPD    = 440.0
SPAWN_DIST     = 4500.0
PLAYER_MAX_HP  = 5
TOTAL_WAVES    = 8

# ── Palette ────────────────────────────────────────────────────────────────
SKY_TOP  = (  4,  7, 32)
SKY_MID  = ( 12, 28, 75)
SKY_HOR  = ( 28, 52,140)
GROUND_C = (  9, 26, 14)
GRID_C   = ( 18, 95, 42)
C_PLAYER = (  0,215,255)
C_PLY2   = ( 70,250,195)
C_BULL   = (255,255, 75)
C_ERED   = (255, 55, 55)
C_EORG   = (255,140,  0)
C_MSIL   = (255,160, 35)
C_EXP    = [(255,200,70),(255,115,35),(255,50,15),(210,210,210),(255,255,180)]
C_HUD    = (  0,255,175)
C_WARN   = (255, 75, 75)
C_WHITE  = (255,255,255)
C_BLACK  = (  0,  0,  0)
C_THRUST = [(  0,170,255),(55,205,255),(130,255,255)]

# ── Utilities ──────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def lerp(a, b, t):    return a + (b - a) * t

def project(wx, wy, rel_z, cam_x, cam_y):
    """Project world point → (screen_x, screen_y, scale) or (None,None,0)."""
    if rel_z < 1.0:
        return None, None, 0.0
    sc = FOCAL / rel_z
    return W * 0.5 + (wx - cam_x) * sc, HORIZON_Y - (wy - cam_y) * sc, sc

def blit_text(surf, text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    sh  = font.render(text, True, C_BLACK)
    if center:
        x -= img.get_width()  // 2
        y -= img.get_height() // 2
    surf.blit(sh,  (x + 2, y + 2))
    surf.blit(img, (x,     y    ))

# ── Screen Shake ───────────────────────────────────────────────────────────
_sk_t   = 0.0
_sk_amp = 0.0

def add_shake(amp, dur):
    global _sk_t, _sk_amp
    _sk_t   = max(_sk_t,   dur)
    _sk_amp = max(_sk_amp, amp)

def tick_shake(dt):
    global _sk_t, _sk_amp
    if _sk_t > 0:
        _sk_t  -= dt
        _sk_amp = _sk_amp * max(0.0, 1 - 3 * dt)
    else:
        _sk_amp = 0.0

def get_shake():
    if _sk_t <= 0 or _sk_amp < 0.5:
        return 0, 0
    a = max(1, int(_sk_amp))
    return random.randint(-a, a), random.randint(-a, a)

# ── Particle System ────────────────────────────────────────────────────────
class _P:
    __slots__ = ['x','y','vx','vy','r','g','b','life','ml','sz']
    def __init__(self, x, y, vx, vy, col, life, sz):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.r, self.g, self.b = col
        self.life = self.ml = float(life)
        self.sz   = float(sz)

    def step(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 90.0 * dt
        self.vx *= max(0.0, 1.0 - 2.2 * dt)
        self.life -= dt

    def draw(self, surf):
        t  = max(0.0, self.life / self.ml)
        c  = (int(self.r * t), int(self.g * t), int(self.b * t))
        s  = max(1, int(self.sz * t))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), s)

_parts: list = []

def _add(x, y, vx, vy, col, life, sz):
    _parts.append(_P(x, y, vx, vy, col, life, sz))

def update_parts(dt):
    live = []
    for p in _parts:
        p.step(dt)
        if p.life > 0:
            live.append(p)
    _parts.clear()
    _parts.extend(live)

def draw_parts(surf):
    for p in _parts:
        p.draw(surf)

def spawn_burst(sx, sy, n=30, colors=None, spd=(60, 380), sz=(3, 8), life=(0.4, 1.2)):
    cols = colors if colors else C_EXP
    for _ in range(n):
        a = random.uniform(0, math.tau)
        s = random.uniform(*spd)
        _add(sx, sy, math.cos(a)*s, math.sin(a)*s,
             random.choice(cols), random.uniform(*life), random.uniform(*sz))

def spawn_thrust(sx, sy):
    a = random.uniform(math.pi * 0.62, math.pi * 1.38)
    s = random.uniform(55, 225)
    _add(sx, sy, math.cos(a)*s, math.sin(a)*s,
         random.choice(C_THRUST), random.uniform(0.07, 0.28), random.uniform(2, 5))

# ── Static Background ──────────────────────────────────────────────────────
_sky_surf = pygame.Surface((W, HORIZON_Y))
for _r in range(HORIZON_Y):
    _t = _r / max(1, HORIZON_Y - 1)
    if _t < 0.5:
        _c = tuple(int(lerp(SKY_TOP[i], SKY_MID[i], _t * 2)) for i in range(3))
    else:
        _c = tuple(int(lerp(SKY_MID[i], SKY_HOR[i], (_t - 0.5) * 2)) for i in range(3))
    pygame.draw.line(_sky_surf, _c, (0, _r), (W - 1, _r))

_STARS = [(random.randint(0, W-1), random.randint(2, HORIZON_Y - 12),
           random.uniform(0.4, 2.1)) for _ in range(130)]

def draw_sky(surf, ox=0, oy=0):
    surf.blit(_sky_surf, (ox, oy))
    for bx, by, br in _STARS:
        i = int(br * 80 + 55)
        pygame.draw.circle(surf, (i, i, i), (bx + ox, by + oy), max(1, int(br)))

def draw_ground(surf, cam_x, cam_y, ox=0, oy=0):
    hy = HORIZON_Y + oy
    pygame.draw.rect(surf, GROUND_C, (0 + ox, hy, W, H - hy + abs(oy) + 1))
    # Depth lines
    for d in (280, 440, 680, 1040, 1580, 2380, 3580, 5400):
        _, sy, _ = project(0, 0, d, cam_x, cam_y)
        if sy is None: continue
        syi = int(sy) + oy
        if hy <= syi <= H + abs(oy):
            br = clamp(int(90 - d / 62), 10, 90)
            pygame.draw.line(surf, (0, br, br // 3),
                             (0 + ox, syi), (W - 1 + ox, syi), 1)
    # Lateral lines
    for lx in range(-2200, 2201, 440):
        nsx, nsy, _ = project(lx, 0, 285,  cam_x, cam_y)
        fsx, fsy, _ = project(lx, 0, 5500, cam_x, cam_y)
        if nsx is None or fsx is None: continue
        nsy_c = clamp(nsy, HORIZON_Y, H)
        fsy_c = clamp(fsy, HORIZON_Y, H)
        if nsy_c >= H and fsy_c >= H: continue
        rng = nsy - fsy
        if abs(rng) > 0.5:
            nsx_c = nsx + (fsx - nsx) * (nsy_c - nsy) / rng
            fsx_c = nsx + (fsx - nsx) * (fsy_c - nsy) / rng
        else:
            nsx_c, fsx_c = nsx, fsx
        pygame.draw.line(surf, GRID_C,
                         (int(nsx_c) + ox, int(nsy_c) + oy),
                         (int(fsx_c) + ox, int(fsy_c) + oy), 1)

# ── Player ────────────────────────────────────────────────────────────────
class Player:
    WX_MIN, WX_MAX = -750.0,  750.0
    WY_MIN, WY_MAX =   50.0,  540.0

    def __init__(self):
        self.wx      = 0.0
        self.wy      = 245.0
        self.hp      = PLAYER_MAX_HP
        self.inv_t   = 0.0
        self.shot_cd = 0.0
        self.roll    = 0.0
        self._trail  = deque(maxlen=14)

    def screen_pos(self, cam_x, cam_y):
        return project(self.wx, self.wy, PLAYER_REL_Z, cam_x, cam_y)

    def update(self, dt, keys):
        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - \
             int(keys[pygame.K_LEFT]  or keys[pygame.K_a])
        dy = int(keys[pygame.K_UP]    or keys[pygame.K_w]) - \
             int(keys[pygame.K_DOWN]  or keys[pygame.K_s])
        self.wx = clamp(self.wx + dx * PLAYER_SPEED * dt, self.WX_MIN, self.WX_MAX)
        self.wy = clamp(self.wy + dy * PLAYER_SPEED * dt, self.WY_MIN, self.WY_MAX)
        self.roll    = lerp(self.roll, -dx * 33.0, min(1.0, dt * 9.0))
        self.shot_cd = max(0.0, self.shot_cd - dt)
        self.inv_t   = max(0.0, self.inv_t   - dt)

    def can_shoot(self):
        if self.shot_cd <= 0.0:
            self.shot_cd = 0.11
            return True
        return False

    def hit(self):
        if self.inv_t > 0.0: return False
        self.hp   -= 1
        self.inv_t = 2.0
        add_shake(14, 0.45)
        return True

    def draw(self, surf, cam_x, cam_y):
        sx, sy, sc = self.screen_pos(cam_x, cam_y)
        if sx is None: return

        self._trail.append((int(sx), int(sy)))
        n = len(self._trail)
        for i, (tx, ty) in enumerate(self._trail):
            t = (i + 1) / n
            pygame.draw.circle(surf,
                               (0, int(175 * t), int(255 * t)),
                               (tx, ty), max(1, int(5 * t)))

        if random.random() < 0.78:
            spawn_thrust(sx + random.randint(-6, 6), sy + 12)

        if self.inv_t > 0 and int(self.inv_t * 8) % 2:
            return

        s  = sc * 2.85
        ra = math.radians(self.roll)
        ca, sa = math.cos(ra), math.sin(ra)

        def R(px, py):
            return int(sx + px * ca - py * sa), int(sy + px * sa + py * ca)

        body   = [R(0, -9*s), R(-3*s, 2*s), R(-2*s, 8*s), R(2*s, 8*s), R(3*s, 2*s)]
        wing_l = [R(-3*s, 0), R(-11*s,  6*s), R(-7*s,  6*s)]
        wing_r = [R( 3*s, 0), R( 11*s,  6*s), R( 7*s,  6*s)]
        tail_l = [R(-2*s, 8*s), R(-5*s, 13*s), R(-2*s, 13*s)]
        tail_r = [R( 2*s, 8*s), R( 5*s, 13*s), R( 2*s, 13*s)]

        for pts, fill, border, bw in [
            (body,   C_PLAYER, C_PLY2,   max(1, int(s * 0.4))),
            (wing_l, C_PLAYER, C_PLY2,   1),
            (wing_r, C_PLAYER, C_PLY2,   1),
            (tail_l, C_PLY2,   C_PLAYER, 1),
            (tail_r, C_PLY2,   C_PLAYER, 1),
        ]:
            if len(pts) >= 3:
                pygame.draw.polygon(surf, fill,   pts)
                pygame.draw.polygon(surf, border, pts, bw)

        pygame.draw.circle(surf, (155, 255, 255), R(0, int(-6*s)), max(2, int(3 * s)))

# ── Player Bullet ─────────────────────────────────────────────────────────
class PBullet:
    def __init__(self, wx, wy, abs_wz):
        self.wx, self.wy = float(wx), float(wy)
        self.abs_wz      = float(abs_wz)
        self.life        = BULLET_LIFE
        self.alive       = True

    def update(self, dt, cam_z):
        self.abs_wz += BULLET_SPEED * dt
        self.life   -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, cam_x, cam_y, cam_z):
        rz = self.abs_wz - cam_z
        sx, sy, sc = project(self.wx, self.wy, rz, cam_x, cam_y)
        if sx is None:
            self.alive = False
            return
        if not (-20 < sx < W + 20 and -20 < sy < H + 20):
            self.alive = False
            return
        l = max(2, int(sc * 11))
        w = max(1, int(sc *  2))
        pygame.draw.rect(surf, C_BULL,
                         (int(sx) - w//2, int(sy) - l//2, max(1,w), max(2,l)))
        pygame.draw.circle(surf, (255, 255, 200),
                           (int(sx), int(sy)), max(2, int(sc * 3.5)))

# ── Enemy Bullet / Missile ────────────────────────────────────────────────
class EBullet:
    def __init__(self, wx, wy, abs_wz, pwx, pwy, pabswz, spd=None):
        self.wx, self.wy = float(wx), float(wy)
        self.abs_wz      = float(abs_wz)
        self.alive       = True
        self.life        = 10.0
        speed = spd if spd else MISSILE_SPD
        dx = pwx    - wx
        dy = pwy    - wy
        dz = pabswz - abs_wz  # negative: player is behind
        dist = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.vz = dz / dist * speed  # negative

    def update(self, dt, cam_z):
        self.wx     += self.vx * dt
        self.wy     += self.vy * dt
        self.abs_wz += self.vz * dt
        self.life   -= dt
        rz = self.abs_wz - cam_z
        if self.life <= 0 or rz < -300:
            self.alive = False

    def draw(self, surf, cam_x, cam_y, cam_z):
        rz = self.abs_wz - cam_z
        sx, sy, sc = project(self.wx, self.wy, rz, cam_x, cam_y)
        if sx is None or not (0 < sx < W and 0 < sy < H):
            return
        r = max(2, int(sc * 6))
        pygame.draw.circle(surf, C_MSIL, (int(sx), int(sy)), r)
        pygame.draw.circle(surf, C_WHITE, (int(sx), int(sy)), max(1, r // 2))
        _add(int(sx), int(sy), 0, 0, (255, 130, 20), 0.10, r * 0.7)

# ── Enemy Plane ───────────────────────────────────────────────────────────
class EPlane:
    def __init__(self, wx, wy, abs_wz, tier=0):
        self.wx, self.wy = float(wx), float(wy)
        self.abs_wz      = float(abs_wz)
        self.tier        = tier
        self.hp          = 1 + tier * 2
        self.alive       = True
        self.shot_t      = random.uniform(1.4, 3.0)
        self.phase       = random.uniform(0, math.tau)
        self.bob_amp     = random.uniform(55, 195)
        self.rel_z       = 0.0

    def update(self, dt, cam_z, pwx, pwy, pabswz, eb_out):
        self.abs_wz -= ENEMY_SPD_BASE * (1.0 + self.tier * 0.45) * dt
        self.wx     += (pwx - self.wx) * dt * 0.33
        self.wy     += (pwy - self.wy) * dt * 0.20
        self.phase  += dt * (1.1 + self.tier * 0.55)
        self.wx     += math.sin(self.phase) * self.bob_amp * dt * 0.28
        self.rel_z   = self.abs_wz - cam_z
        self.shot_t -= dt
        if self.shot_t <= 0 and 350 < self.rel_z < 4200:
            self.shot_t = random.uniform(1.5, 3.2)
            eb_out.append(EBullet(self.wx, self.wy, self.abs_wz, pwx, pwy, pabswz))
        if self.rel_z < -150:
            self.alive = False

    def draw(self, surf, cam_x, cam_y):
        sx, sy, sc = project(self.wx, self.wy, self.rel_z, cam_x, cam_y)
        if sx is None or sc < 0.015: return
        if not (-130 < sx < W + 130 and -70 < sy < H + 70): return
        col = C_ERED if self.tier == 0 else C_EORG
        s   = sc * 2.5
        def P(px, py): return int(sx + px * s), int(sy + py * s)
        body  = [P(0, 7), P(-3, -1), P(-1.2, -5), P(1.2, -5), P(3, -1)]
        wingL = [P(-3, 0),  P(-11,  4), P(-4,  4)]
        wingR = [P( 3, 0),  P( 11,  4), P( 4,  4)]
        for pts in (body, wingL, wingR):
            if len(pts) >= 3:
                pygame.draw.polygon(surf, col,     pts)
                pygame.draw.polygon(surf, C_WHITE, pts, max(1, int(s * 0.45)))
        if self.tier > 0 and self.rel_z < 2600:
            bw = max(18, int(40 * sc))
            bx, by = int(sx) - bw // 2, int(sy) - int(28 * sc)
            pygame.draw.rect(surf, (65, 0, 0),  (bx, by, bw, 3))
            fw = int(bw * self.hp / (1 + self.tier * 2))
            pygame.draw.rect(surf, col, (bx, by, max(0, fw), 3))

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
            return True
        add_shake(5, 0.12)
        return False

# ── Enemy Turret ──────────────────────────────────────────────────────────
class ETurret:
    def __init__(self, wx, abs_wz):
        self.wx      = float(wx)
        self.wy      = 0.0
        self.abs_wz  = float(abs_wz)
        self.hp      = 3
        self.alive   = True
        self.shot_t  = random.uniform(0.9, 2.3)
        self.flash_t = 0.0
        self.rel_z   = 0.0

    def update(self, dt, cam_z, pwx, pwy, pabswz, eb_out):
        self.rel_z   = self.abs_wz - cam_z
        self.flash_t = max(0.0, self.flash_t - dt)
        self.shot_t -= dt
        if self.shot_t <= 0 and 290 < self.rel_z < 3900:
            self.shot_t  = random.uniform(1.2, 2.7)
            self.flash_t = 0.20
            eb_out.append(EBullet(self.wx, self.wy, self.abs_wz, pwx, pwy, pabswz))
        if self.rel_z < -350:
            self.alive = False

    def draw(self, surf, cam_x, cam_y):
        sx, sy, sc = project(self.wx, self.wy, self.rel_z, cam_x, cam_y)
        if sx is None or sc < 0.025: return
        if not (0 < sx < W and HORIZON_Y < sy < H + 55): return
        col = (255, 220, 80) if self.flash_t > 0 else (175, 65, 28)
        r   = max(3, int(14 * sc))
        pygame.draw.rect(surf, col, (int(sx) - r, int(sy) - r * 2, r * 2, r * 2))
        pygame.draw.circle(surf, (255, 95, 45), (int(sx), int(sy) - r * 2), max(2, r // 2))

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
            return True
        add_shake(4, 0.11)
        return False

# ── Wave Spawner ──────────────────────────────────────────────────────────
class Spawner:
    def __init__(self):
        self.wave       = 1
        self.between    = False
        self.between_t  = 0.0
        self._remaining = 0
        self._spawn_t   = 1.5
        self._t         = 0.0

    def begin_wave(self, enemies, cam_z, pabswz):
        self._remaining = self.wave * 3 + 2
        self._spawn_t   = max(0.38, 2.5 - self.wave * 0.22)
        self._t         = 1.0
        self.between    = False

    def update(self, dt, enemies, cam_z, pabswz):
        if self.between:
            self.between_t -= dt
            if self.between_t <= 0:
                self.wave += 1
                if self.wave > TOTAL_WAVES:
                    return "win"
                self.begin_wave(enemies, cam_z, pabswz)
            return None
        self._t -= dt
        if self._t <= 0 and self._remaining > 0:
            self._t          = self._spawn_t
            self._remaining -= 1
            self._do_spawn(enemies, cam_z, pabswz)
        if self._remaining <= 0 and len(enemies) == 0:
            self.between   = True
            self.between_t = 4.0
            return "wave_clear"
        return None

    def _do_spawn(self, enemies, cam_z, pabswz):
        base_z = pabswz + SPAWN_DIST + random.uniform(-450, 650)
        r      = random.random()
        wx     = random.uniform(-660, 660)
        wy     = random.uniform(65, 490)
        if self.wave >= 3 and r < 0.22:
            enemies.append(ETurret(wx * 0.65, base_z))
        elif self.wave >= 5 and r > 0.80:
            e    = EPlane(wx, wy, base_z, tier=1)
            e.hp = 4
            enemies.append(e)
        elif r > 0.65 and self.wave >= 2:
            enemies.append(EPlane(wx, wy, base_z, tier=1))
        else:
            enemies.append(EPlane(wx, wy, base_z, tier=0))

# ── HUD ───────────────────────────────────────────────────────────────────
def draw_hud(surf, player, score, spawner, ann_t):
    for i in range(PLAYER_MAX_HP):
        x   = 26 + i * 32
        col = C_HUD if i < player.hp else (32, 32, 32)
        pygame.draw.polygon(surf, col,
                            [(x+9,17),(x+18,30),(x+13,44),(x+5,44),(x,30)])
    blit_text(surf, f"SCORE  {score:07d}", font_hud, C_HUD, W - 278, 15)
    blit_text(surf, f"WAVE {spawner.wave}/{TOTAL_WAVES}", font_hud, C_HUD, W//2 - 62, 15)
    blit_text(surf, f"ALT {int(player.wy):>4}", font_sm, (75, 195, 255), 26, 88)
    cx, cy = W // 2, HORIZON_Y + 62
    pygame.draw.circle(surf, C_HUD, (cx, cy), 14, 1)
    for dx_, dy_ in [(-20,0),(20,0),(0,-20),(0,20)]:
        ex_, ey_ = cx + dx_, cy + dy_
        nx_, ny_ = cx + dx_ * 14//20, cy + dy_ * 14//20
        pygame.draw.line(surf, C_HUD, (nx_, ny_), (ex_, ey_), 1)
    if spawner.between:
        rt = int(spawner.between_t) + 1
        blit_text(surf, "WAVE CLEAR!",        font_med, C_HUD,   W//2, H//2-52, center=True)
        blit_text(surf, f"NEXT WAVE IN {rt}...", font_hud, C_WHITE, W//2, H//2+12, center=True)
    if ann_t > 0:
        a = min(1.0, ann_t)
        blit_text(surf, f"WAVE {spawner.wave}", font_big,
                  (int(255*a), int(255*a), int(75*a)), W//2, H//2-82, center=True)

# ── Menu / Screens ────────────────────────────────────────────────────────
def draw_menu(surf, frame):
    surf.fill(SKY_TOP)
    draw_sky(surf)
    t  = (math.sin(frame * 0.04) + 1) * 0.5
    gc = (int(lerp(0,75,t)), int(lerp(175,255,t)), int(lerp(195,255,t)))
    blit_text(surf, "AFTERBURNER ZERO",       font_big, gc,             W//2, 148, center=True)
    blit_text(surf, "PSEUDO-3D FLIGHT COMBAT",font_med, (55,155,195),   W//2, 242, center=True)
    pt  = (math.sin(frame * 0.075) + 1) * 0.5
    pc  = (int(lerp(75, 255, pt)),) * 3
    blit_text(surf, "\u25b6  PRESS SPACE TO FLY  \u25c0", font_med, pc, W//2, 355, center=True)
    for i, txt in enumerate([
        "WASD / Arrows  \u2014  Move",
        "SPACE  \u2014  Fire cannons",
        "SHIFT  \u2014  Afterburner boost",
        "ESC  \u2014  Quit",
    ]):
        blit_text(surf, txt, font_sm, (175, 215, 255), W//2, 458 + i * 30, center=True)

def draw_gameover(surf, score, wave):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 158))
    surf.blit(ov, (0, 0))
    blit_text(surf, "SHOT DOWN",              font_big, C_WARN,  W//2, 212, center=True)
    blit_text(surf, f"SCORE  {score:07d}",    font_med, C_WHITE, W//2, 322, center=True)
    blit_text(surf, f"WAVE {wave}/{TOTAL_WAVES}", font_med, C_HUD, W//2, 376, center=True)
    blit_text(surf, "PRESS SPACE TO RETRY",   font_hud, C_WHITE, W//2, 468, center=True)

def draw_win(surf, score):
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 22, 0, 158))
    surf.blit(ov, (0, 0))
    blit_text(surf, "MISSION COMPLETE",           font_big, (45,255,125), W//2, 212, center=True)
    blit_text(surf, f"FINAL SCORE  {score:07d}",  font_med, C_WHITE,      W//2, 328, center=True)
    blit_text(surf, "PRESS SPACE TO REPLAY",      font_hud, C_WHITE,      W//2, 458, center=True)

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    global _sk_t, _sk_amp

    state = "menu"
    score = 0
    frame = 0

    cam_z, cam_x, cam_y = 0.0, 0.0, 245.0 + CAM_HEIGHT
    ann_t = 0.0

    player  = Player()
    enemies : list = []
    pbs     : list = []
    ebs     : list = []
    spawner = Spawner()

    def reset():
        nonlocal cam_z, cam_x, cam_y, player, enemies, pbs, ebs, spawner
        nonlocal score, ann_t
        global _sk_t, _sk_amp
        cam_z, cam_x = 0.0, 0.0
        cam_y = 245.0 + CAM_HEIGHT
        score, ann_t = 0, 2.8
        _sk_t = _sk_amp = 0.0
        _parts.clear()
        player  = Player()
        enemies = []
        pbs     = []
        ebs     = []
        spawner = Spawner()
        spawner.begin_wave(enemies, cam_z, cam_z + PLAYER_REL_Z)

    running = True
    while running:
        dt    = min(clock.tick(FPS) / 1000.0, 0.05)
        frame += 1
        keys  = pygame.key.get_pressed()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    if state == "menu":
                        reset(); state = "play"
                    elif state in ("dead", "win"):
                        reset(); state = "play"

        # ── Update ──────────────────────────────────────────────────────
        if state == "play":
            boost  = 1.6 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
            cam_z += CAM_SPEED * boost * dt

            player.update(dt, keys)
            cam_x = lerp(cam_x, player.wx,             min(1.0, dt * 7.0))
            cam_y = lerp(cam_y, player.wy + CAM_HEIGHT, min(1.0, dt * 7.0))

            pabswz = cam_z + PLAYER_REL_Z

            if keys[pygame.K_SPACE] and player.can_shoot():
                for ox in (-12.0, 12.0):
                    pbs.append(PBullet(player.wx + ox, player.wy, pabswz))

            # Bullets
            for b in pbs: b.update(dt, cam_z)
            pbs = [b for b in pbs if b.alive]

            # Enemies
            new_ebs: list = []
            for e in enemies:
                e.update(dt, cam_z, player.wx, player.wy, pabswz, new_ebs)
            ebs.extend(new_ebs)
            enemies = [e for e in enemies if e.alive]

            # Enemy bullets
            for eb in ebs: eb.update(dt, cam_z)
            ebs = [eb for eb in ebs if eb.alive]

            # PBullet × enemy collision
            for b in pbs[:]:
                if not b.alive: continue
                brz = b.abs_wz - cam_z
                for e in enemies:
                    if not e.alive: continue
                    erz = e.abs_wz - cam_z
                    dx  = b.wx - e.wx
                    dy  = b.wy - e.wy
                    dz  = brz  - erz
                    hb  = 92.0 if isinstance(e, ETurret) else 132.0
                    if dx*dx + dy*dy + dz*dz < hb * hb:
                        destroyed = e.hit()
                        b.alive   = False
                        bsx, bsy, _ = project(b.wx, b.wy, brz, cam_x, cam_y)
                        if bsx:
                            n = 48 if destroyed else 14
                            cols = C_EXP if destroyed else [(255,95,28),(200,200,200)]
                            spawn_burst(bsx, bsy, n=n, colors=cols)
                        if destroyed:
                            bonus  = 155 * (1 + getattr(e, 'tier', 0))
                            score += bonus
                            add_shake(9, 0.28)
                        break

            # EBullet × player
            for eb in ebs[:]:
                if not eb.alive: continue
                rz  = eb.abs_wz - cam_z
                dx  = eb.wx  - player.wx
                dy  = eb.wy  - player.wy
                dz  = rz     - PLAYER_REL_Z
                if dx*dx + dy*dy + dz*dz < 87.0 * 87.0:
                    eb.alive = False
                    if player.hit():
                        psx, psy, _ = player.screen_pos(cam_x, cam_y)
                        if psx:
                            spawn_burst(psx, psy, n=24,
                                        colors=[(0,200,255),(255,255,255),(0,145,200)])
                    if player.hp <= 0: state = "dead"

            # Enemy body × player
            for e in enemies:
                if not e.alive: continue
                erz = e.abs_wz - cam_z
                dx  = e.wx - player.wx
                dy  = e.wy - player.wy
                dz  = erz  - PLAYER_REL_Z
                if dx*dx + dy*dy + dz*dz < 98.0 * 98.0:
                    e.alive = False
                    if player.hit():
                        psx, psy, _ = player.screen_pos(cam_x, cam_y)
                        if psx: spawn_burst(psx, psy, n=55)
                        add_shake(18, 0.60)
                    if player.hp <= 0: state = "dead"

            # Wave logic
            ev = spawner.update(dt, enemies, cam_z, pabswz)
            if ev == "wave_clear":
                score += 600
                ann_t  = 2.8
            elif ev == "win":
                state = "win"

            score += max(0, int(CAM_SPEED * boost * dt * 0.015))
            ann_t  = max(0.0, ann_t - dt)
            tick_shake(dt)
            update_parts(dt)

        # ── Draw ────────────────────────────────────────────────────────
        ox, oy = get_shake() if state == "play" else (0, 0)

        draw_sky(screen, ox, oy)

        if state == "menu":
            draw_menu(screen, frame)
        else:
            draw_ground(screen, cam_x, cam_y, ox, oy)

            if state in ("play", "dead"):
                for e in sorted(enemies, key=lambda x: x.abs_wz, reverse=True):
                    e.draw(screen, cam_x, cam_y)
                for eb in ebs:
                    eb.draw(screen, cam_x, cam_y, cam_z)
                for b in pbs:
                    b.draw(screen, cam_x, cam_y, cam_z)
                player.draw(screen, cam_x, cam_y)
                draw_parts(screen)

            if state == "play":
                draw_hud(screen, player, score, spawner, ann_t)
            elif state == "dead":
                draw_hud(screen, player, score, spawner, 0.0)
                draw_gameover(screen, score, spawner.wave)
            elif state == "win":
                draw_win(screen, score)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
