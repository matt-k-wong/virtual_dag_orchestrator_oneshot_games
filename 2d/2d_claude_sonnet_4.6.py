#!/usr/bin/env python3
"""ROGUE DRONE  —  Neon Cyberpunk Survivor Shooter
Auto-installs pygame-ce (or pygame) if needed. Run with:  python game.py
"""
import sys, subprocess, math, random

# ── AUTO-INSTALL ──────────────────────────────────────────────────────────────
def _ensure_pygame():
    try:
        import pygame
        return pygame
    except ImportError:
        print("[ROGUE DRONE] pygame-ce not found — installing...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pygame-ce", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import pygame
            return pygame
        except Exception:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pygame", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import pygame
            return pygame

pygame = _ensure_pygame()
pygame.init()

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
W, H, FPS = 1280, 720, 60

BG       = (4,   4,  12)
GRID_C   = (14, 14,  32)
C_CYAN   = (0,  240, 210)
C_PINK   = (255,  20, 130)
C_GREEN  = (0,  240,  80)
C_ORANGE = (255, 150,   0)
C_RED    = (255,  50,  50)
C_PURPLE = (200,   0, 255)
C_YELLOW = (255, 220,   0)
C_WHITE  = (240, 240, 255)
C_DARK   = ( 16,  16,  36)

S_MENU, S_PLAY, S_DEAD = 0, 1, 2

# ── HELPERS ───────────────────────────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def norm2(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (0.0, 0.0)
def rvar(col, a=35):
    return tuple(clamp(c + random.randint(-a, a), 0, 255) for c in col)
def glow_blit(surf, x, y, radius, color, alpha=60):
    r = max(2, int(radius))
    g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(g, (*color, alpha), (r, r), r)
    surf.blit(g, (int(x) - r, int(y) - r), special_flags=pygame.BLEND_ADD)

# ── PARTICLES ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','dx','dy','color','life','max_life','size','glow')
    def __init__(self, x, y, dx, dy, color, life, size=3, glow=True):
        self.x, self.y, self.dx, self.dy = x, y, dx, dy
        self.color, self.life, self.max_life = color, life, life
        self.size, self.glow = size, glow

    def update(self, dt):
        self.x += self.dx * dt;  self.y += self.dy * dt
        self.dx *= 0.90;         self.dy *= 0.90
        self.life -= dt

    def draw(self, surf):
        t = max(0.0, self.life / self.max_life)
        s = max(1, int(self.size * t))
        col = tuple(int(c * t) for c in self.color)
        if self.glow and s > 1:
            glow_blit(surf, self.x, self.y, s * 2, col, int(80 * t))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), s)


class Particles:
    def __init__(self): self.pool = []

    def add(self, p): self.pool.append(p)

    def burst(self, x, y, col, n=22, spd=160, sz=4):
        for _ in range(n):
            a = random.uniform(0, math.tau); s = random.uniform(spd * .3, spd)
            self.add(Particle(x, y, math.cos(a)*s, math.sin(a)*s,
                              rvar(col, 40), random.uniform(.25, .85),
                              random.uniform(sz * .5, sz * 1.5)))

    def sparks(self, x, y, col, n=6, spd=80):
        for _ in range(n):
            a = random.uniform(0, math.tau); s = random.uniform(spd * .4, spd)
            self.add(Particle(x, y, math.cos(a)*s, math.sin(a)*s,
                              col, random.uniform(.1, .28), random.uniform(1, 2.5)))

    def trail(self, x, y, col, sz=2):
        self.add(Particle(x, y, random.uniform(-15, 15), random.uniform(-15, 15),
                          col, .14, sz, glow=False))

    def update(self, dt):
        self.pool = [p for p in self.pool if p.life > 0]
        for p in self.pool: p.update(dt)

    def draw(self, surf):
        for p in self.pool: p.draw(surf)


# ── BULLET ────────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, angle, speed, damage, color, is_player, size=4):
        self.x, self.y = x, y
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.damage, self.color = damage, color
        self.is_player, self.size = is_player, size
        self.alive = True; self.trail = []

    def update(self, dt):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7: self.trail.pop(0)
        self.x += self.dx * dt;  self.y += self.dy * dt
        if not (0 < self.x < W and 0 < self.y < H): self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            t = i / max(1, len(self.trail))
            s = max(1, int(self.size * t * .6))
            col = tuple(int(c * t * .5) for c in self.color)
            pygame.draw.circle(surf, col, (int(tx), int(ty)), s)
        glow_blit(surf, self.x, self.y, self.size * 3, self.color, 70)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surf, C_WHITE,   (int(self.x), int(self.y)), max(1, self.size - 2))


# ── PLAYER ────────────────────────────────────────────────────────────────────
class Player:
    R = 18;  SPEED = 290;  MAX_HP = 100;  BASE_CD = .13;  INVULN = .7

    def __init__(self):
        self.x, self.y = W / 2, H / 2
        self.hp = self.MAX_HP;  self.angle = 0.0
        self.shoot_t = 0.0;  self.invuln_t = 0.0;  self.hit_flash = 0.0
        self.rapid_t = 0.0;  self.dmg_boost_t = 0.0
        self.alive = True;  self.score = 0;  self.kills = 0
        self.trail = []

    @property
    def shoot_cd(self): return self.BASE_CD * (.35 if self.rapid_t > 0 else 1.0)
    @property
    def bullet_dmg(self): return 25.0 * (2.0 if self.dmg_boost_t > 0 else 1.0)

    def update(self, dt, keys, mx, my, bullets, fx):
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx or dy:
            ndx, ndy = norm2(dx, dy)
            self.x += ndx * self.SPEED * dt
            self.y += ndy * self.SPEED * dt
            self.trail.append((self.x, self.y))
            if len(self.trail) > 10: self.trail.pop(0)
            if random.random() < .35: fx.trail(self.x, self.y, C_CYAN, 2)
        else:
            if self.trail: self.trail.pop(0)

        self.x = clamp(self.x, self.R, W - self.R)
        self.y = clamp(self.y, self.R, H - self.R)
        self.angle = math.atan2(my - self.y, mx - self.x)

        self.shoot_t     = max(0.0, self.shoot_t     - dt)
        self.invuln_t    = max(0.0, self.invuln_t    - dt)
        self.hit_flash   = max(0.0, self.hit_flash   - dt)
        self.rapid_t     = max(0.0, self.rapid_t     - dt)
        self.dmg_boost_t = max(0.0, self.dmg_boost_t - dt)

        if pygame.mouse.get_pressed()[0] and self.shoot_t <= 0:
            self.shoot_t = self.shoot_cd
            bx = self.x + math.cos(self.angle) * (self.R + 6)
            by = self.y + math.sin(self.angle) * (self.R + 6)
            bullets.append(Bullet(bx, by, self.angle, 700,
                                  self.bullet_dmg, C_CYAN, True, 4))
            fx.sparks(bx, by, C_CYAN, 4, 70)

    def take_hit(self, amount, fx):
        if self.invuln_t > 0: return
        self.hp -= amount;  self.invuln_t = self.INVULN;  self.hit_flash = .2
        fx.burst(self.x, self.y, C_RED, 8, 90, 3)
        if self.hp <= 0 and self.alive:
            self.alive = False
            fx.burst(self.x, self.y, C_CYAN, 45, 220, 6)

    def take_melee(self, dps, dt, fx):
        self.hp -= dps * dt
        self.hit_flash = .08
        if self.hp <= 0 and self.alive:
            self.alive = False
            fx.burst(self.x, self.y, C_CYAN, 45, 220, 6)

    def draw(self, surf):
        # movement trail
        for i, (tx, ty) in enumerate(self.trail):
            t = i / max(1, len(self.trail))
            s = max(1, int(self.R * .45 * t))
            col = tuple(int(c * t * .4) for c in C_CYAN)
            pygame.draw.circle(surf, col, (int(tx), int(ty)), s)
        # invuln flicker
        if self.invuln_t > 0 and int(self.invuln_t * 14) % 2 == 0: return
        col = C_RED if self.hit_flash > 0 else C_CYAN
        glow_blit(surf, self.x, self.y, self.R * 2.6, col, 55)
        # hexagon body
        pts = [(self.x + math.cos(self.angle + i * math.pi / 3) * self.R,
                self.y + math.sin(self.angle + i * math.pi / 3) * self.R)
               for i in range(6)]
        pygame.draw.polygon(surf, col, [(int(p[0]), int(p[1])) for p in pts], 2)
        ipts = [(self.x + math.cos(self.angle + i * math.pi / 3) * self.R * .55,
                 self.y + math.sin(self.angle + i * math.pi / 3) * self.R * .55)
                for i in range(6)]
        pygame.draw.polygon(surf, col, [(int(p[0]), int(p[1])) for p in ipts], 1)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 4)
        # aim pip
        tip_x = self.x + math.cos(self.angle) * (self.R + 10)
        tip_y = self.y + math.sin(self.angle) * (self.R + 10)
        pygame.draw.circle(surf, C_YELLOW, (int(tip_x), int(tip_y)), 3)


# ── ENEMIES ───────────────────────────────────────────────────────────────────
class Enemy:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.alive = True;  self.hit_flash = 0.0;  self.angle = 0.0

    def take_hit(self, dmg, fx):
        self.hp -= dmg;  self.hit_flash = .12
        fx.sparks(self.x, self.y, C_ORANGE, 5, 70)
        if self.hp <= 0:
            self.alive = False;  self._die(fx)

    def _die(self, fx): fx.burst(self.x, self.y, self.COLOR, 28, 190, 5)

    def _draw_hp(self, surf):
        ratio = max(0.0, self.hp / self.MAX_HP)
        bw = self.R * 2
        pygame.draw.rect(surf, C_DARK,  (int(self.x - bw//2), int(self.y - self.R - 9), bw, 4))
        pygame.draw.rect(surf, C_GREEN, (int(self.x - bw//2), int(self.y - self.R - 9),
                                         max(0, int(bw * ratio)), 4))

    def _col(self): return C_WHITE if self.hit_flash > 0 else self.COLOR
    def _tick(self, dt): self.hit_flash = max(0.0, self.hit_flash - dt)


class WalkerBot(Enemy):
    MAX_HP = 60;  SPEED = 95;  R = 16;  SCORE = 100;  MELEE = 22;  COLOR = C_ORANGE

    def __init__(self, x, y): super().__init__(x, y); self.hp = self.MAX_HP

    def update(self, dt, px, py, bullets, fx):
        dx, dy = norm2(px - self.x, py - self.y)
        self.x += dx * self.SPEED * dt;  self.y += dy * self.SPEED * dt
        self.angle = math.atan2(py - self.y, px - self.x);  self._tick(dt)

    def draw(self, surf):
        col = self._col();  hw = self.R
        glow_blit(surf, self.x, self.y, hw * 2, col, 50)
        pygame.draw.rect(surf, col, (int(self.x - hw), int(self.y - hw), hw*2, hw*2), 2)
        ex = self.x + math.cos(self.angle) * hw * .5
        ey = self.y + math.sin(self.angle) * hw * .5
        pygame.draw.circle(surf, col, (int(ex), int(ey)), 4)
        self._draw_hp(surf)


class ShooterBot(Enemy):
    MAX_HP = 40;  SPEED = 60;  R = 14;  SCORE = 150;  MELEE = 12;  COLOR = C_PINK
    PREF_DIST = 290;  SHOOT_RANGE = 360;  SHOOT_CD = 1.2;  BULLET_DMG = 10

    def __init__(self, x, y):
        super().__init__(x, y);  self.hp = self.MAX_HP
        self.shoot_t = random.uniform(0, self.SHOOT_CD)

    def update(self, dt, px, py, bullets, fx):
        d = math.hypot(px - self.x, py - self.y)
        dx, dy = norm2(px - self.x, py - self.y)
        if d > self.PREF_DIST + 40:
            self.x += dx * self.SPEED * dt;  self.y += dy * self.SPEED * dt
        elif d < self.PREF_DIST - 40:
            self.x -= dx * self.SPEED * .5 * dt;  self.y -= dy * self.SPEED * .5 * dt
        else:
            self.x += -dy * self.SPEED * .4 * dt;  self.y += dx * self.SPEED * .4 * dt
        self.angle = math.atan2(py - self.y, px - self.x)
        self.shoot_t -= dt
        if self.shoot_t <= 0 and d < self.SHOOT_RANGE:
            self.shoot_t = self.SHOOT_CD
            bullets.append(Bullet(self.x, self.y, self.angle,
                                  310, self.BULLET_DMG, C_PINK, False, 5))
            fx.sparks(self.x, self.y, C_PINK, 3, 50)
        self._tick(dt)

    def draw(self, surf):
        col = self._col();  r = self.R
        glow_blit(surf, self.x, self.y, r * 2, col, 50)
        pts = [(self.x, self.y-r), (self.x+r, self.y),
               (self.x, self.y+r), (self.x-r, self.y)]
        pygame.draw.polygon(surf, col, [(int(p[0]), int(p[1])) for p in pts], 2)
        ex = self.x + math.cos(self.angle) * r * .5
        ey = self.y + math.sin(self.angle) * r * .5
        pygame.draw.circle(surf, col, (int(ex), int(ey)), 3)
        self._draw_hp(surf)


class TankBot(Enemy):
    MAX_HP = 220;  SPEED = 42;  R = 26;  SCORE = 350;  MELEE = 40;  COLOR = C_PURPLE

    def __init__(self, x, y): super().__init__(x, y);  self.hp = self.MAX_HP

    def update(self, dt, px, py, bullets, fx):
        dx, dy = norm2(px - self.x, py - self.y)
        self.x += dx * self.SPEED * dt;  self.y += dy * self.SPEED * dt
        self.angle = math.atan2(py - self.y, px - self.x);  self._tick(dt)

    def draw(self, surf):
        col = self._col();  r = self.R
        glow_blit(surf, self.x, self.y, r * 2.2, col, 65)
        pts = [(self.x + math.cos(i * math.pi/4) * r,
                self.y + math.sin(i * math.pi/4) * r) for i in range(8)]
        pygame.draw.polygon(surf, col, [(int(p[0]), int(p[1])) for p in pts], 3)
        pygame.draw.line(surf, col,
                         (int(self.x), int(self.y)),
                         (int(self.x + math.cos(self.angle)*r),
                          int(self.y + math.sin(self.angle)*r)), 4)
        self._draw_hp(surf)


# ── PICKUP ────────────────────────────────────────────────────────────────────
class Pickup:
    R = 10;  LIFE = 9.0
    _COLORS = {'health': C_GREEN, 'rapid': C_YELLOW, 'dmg': C_PINK}

    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.color = self._COLORS[kind]
        self.alive = True;  self.age = 0.0

    def update(self, dt):
        self.age += dt
        if self.age > self.LIFE: self.alive = False

    def draw(self, surf):
        pulse = math.sin(self.age * 5) * 2.5
        r = self.R + pulse
        glow_blit(surf, self.x, self.y, r * 2.5, self.color, 75)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), max(2, int(r)), 2)
        pygame.draw.circle(surf, C_WHITE, (int(self.x), int(self.y)), 4)


# ── WAVE MANAGER ──────────────────────────────────────────────────────────────
class WaveManager:
    def __init__(self): self.wave = 0;  self.between = False;  self.btimer = 0.0

    def _configs(self, w):
        out = [WalkerBot] * min(3 + w * 2, 14)
        if w >= 2: out += [ShooterBot] * min((w - 1) * 2, 8)
        if w >= 3: out += [TankBot]    * min(w - 2,       5)
        return out

    def spawn(self, w, px, py):
        enemies = []
        for Cls in self._configs(w):
            sx, sy = float(W // 2), 50.0          # safe default
            for _ in range(30):
                side = random.randint(0, 3)
                if   side == 0: sx, sy = random.uniform(60, W-60), 50.0
                elif side == 1: sx, sy = random.uniform(60, W-60), float(H - 50)
                elif side == 2: sx, sy = 50.0,          random.uniform(60, H-60)
                else:           sx, sy = float(W - 50), random.uniform(60, H-60)
                if math.hypot(sx - px, sy - py) > 220: break
            enemies.append(Cls(sx, sy))
        return enemies


# ── SCREEN SHAKE ──────────────────────────────────────────────────────────────
class Shake:
    def __init__(self): self.trauma = 0.0;  self.off = (0.0, 0.0)

    def add(self, v): self.trauma = min(1.0, self.trauma + v)

    def update(self, dt):
        self.trauma = max(0.0, self.trauma - dt * 2.2)
        s = self.trauma ** 2 * 14
        self.off = (random.uniform(-s, s), random.uniform(-s, s))


# ── BACKGROUND ────────────────────────────────────────────────────────────────
_SCANLINE = None

def make_scanline():
    global _SCANLINE
    _SCANLINE = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 3):
        pygame.draw.line(_SCANLINE, (0, 0, 0, 28), (0, y), (W, y))

def draw_bg(surf, scroll):
    surf.fill(BG)
    g = 64;  off = int(scroll) % g
    for x in range(-g, W + g, g):
        pygame.draw.line(surf, GRID_C, (x - off, 0), (x - off, H), 1)
    for y in range(-g, H + g, g):
        pygame.draw.line(surf, GRID_C, (0, y - off), (W, y - off), 1)
    # corner brackets
    for cx, cy, sx, sy in [(80,80,1,1),(W-80,80,-1,1),(80,H-80,1,-1),(W-80,H-80,-1,-1)]:
        pygame.draw.line(surf, GRID_C, (cx, cy), (cx + sx*30, cy), 2)
        pygame.draw.line(surf, GRID_C, (cx, cy), (cx, cy + sy*30), 2)
    if _SCANLINE:
        surf.blit(_SCANLINE, (0, 0))


# ── HUD ───────────────────────────────────────────────────────────────────────
def draw_hud(surf, player, wm, fL, fM, fS):
    # HP bar
    bx, by, bw, bh = 30, H - 52, 220, 18
    ratio = max(0.0, player.hp / player.MAX_HP)
    hcol = C_GREEN if ratio > .5 else (C_YELLOW if ratio > .25 else C_RED)
    pygame.draw.rect(surf, (10, 10, 25), (bx-2, by-2, bw+4, bh+4))
    pygame.draw.rect(surf, (35, 35, 55), (bx,   by,   bw,   bh))
    pygame.draw.rect(surf, hcol,         (bx,   by,   max(0, int(bw*ratio)), bh))
    pygame.draw.rect(surf, C_WHITE,      (bx-2, by-2, bw+4, bh+4), 1)
    surf.blit(fS.render(f"HP {max(0,int(player.hp))}/{player.MAX_HP}", True, C_WHITE), (bx+4, by+2))
    surf.blit(fS.render("ROGUE DRONE", True, C_CYAN), (bx, by - 24))

    # Score (top right)
    st = fL.render(f"{player.score:08d}", True, C_YELLOW)
    surf.blit(fS.render("SCORE", True, C_WHITE),  (W - st.get_width() - 20, 10))
    surf.blit(st,                                  (W - st.get_width() - 20, 26))

    # Wave (top center)
    wt = fM.render(f"WAVE {wm.wave}", True, C_CYAN)
    surf.blit(wt, (W//2 - wt.get_width()//2, 12))

    # Kills (top left)
    surf.blit(fS.render(f"KILLS: {player.kills}", True, C_WHITE), (30, 12))

    # Powerup timers
    py_ = H - 80
    if player.rapid_t > 0:
        surf.blit(fS.render(f"[!] RAPID FIRE  {player.rapid_t:.1f}s", True, C_YELLOW), (30, py_))
        py_ -= 20
    if player.dmg_boost_t > 0:
        surf.blit(fS.render(f"[*] DMG BOOST  {player.dmg_boost_t:.1f}s", True, C_PINK), (30, py_))

    # Between-wave banner
    if wm.between and wm.wave > 0:
        a = fL.render(f"WAVE {wm.wave} CLEARED!", True, C_GREEN)
        b = fM.render(f"Next wave in {max(0, wm.btimer):.1f}s", True, C_WHITE)
        surf.blit(a, (W//2 - a.get_width()//2, H//2 - 36))
        surf.blit(b, (W//2 - b.get_width()//2, H//2 + 10))


def draw_menu(surf, hi, fT, fL, fM, fS):
    surf.fill(BG)
    if _SCANLINE: surf.blit(_SCANLINE, (0, 0))
    t = pygame.time.get_ticks() / 1000.0
    alpha = clamp(200 + int(math.sin(t * 2.5) * 55), 100, 255)
    ti = fT.render("ROGUE  DRONE", True, C_CYAN);  ti.set_alpha(alpha)
    surf.blit(ti, (W//2 - ti.get_width()//2, 100))
    sub = fM.render("NEON CYBERPUNK SURVIVOR SHOOTER", True, C_PINK)
    surf.blit(sub, (W//2 - sub.get_width()//2, 176))
    # controls
    for i, (k, v) in enumerate([("WASD / ARROWS", "Move"),
                                  ("MOUSE",         "Aim"),
                                  ("LEFT CLICK",    "Shoot"),
                                  ("R",             "Restart"),
                                  ("ESC",           "Quit")]):
        ks = fM.render(k, True, C_YELLOW);  vs = fM.render(f"  -  {v}", True, C_WHITE)
        x = W//2 - 200;  y = 280 + i * 44
        surf.blit(ks, (x, y));  surf.blit(vs, (x + ks.get_width(), y))
    if hi > 0:
        hs = fM.render(f"BEST SCORE: {hi:08d}", True, C_GREEN)
        surf.blit(hs, (W//2 - hs.get_width()//2, 518))
    pulse = int((math.sin(t * 3) + 1) * .5 * 255)
    start = fL.render("[ CLICK TO START ]", True, C_CYAN);  start.set_alpha(pulse)
    surf.blit(start, (W//2 - start.get_width()//2, 585))


def draw_dead(surf, player, wm, fT, fL, fM, fS):
    ov = pygame.Surface((W, H), pygame.SRCALPHA);  ov.fill((0, 0, 5, 170))
    surf.blit(ov, (0, 0))
    dt = fT.render("DRONE  DESTROYED", True, C_RED)
    surf.blit(dt, (W//2 - dt.get_width()//2, 130))
    y = 280
    for line in [f"FINAL SCORE:  {player.score:08d}",
                 f"WAVE REACHED: {wm.wave}",
                 f"BOTS KILLED:  {player.kills}"]:
        s = fL.render(line, True, C_WHITE);  surf.blit(s, (W//2 - s.get_width()//2, y));  y += 58
    t = pygame.time.get_ticks() / 1000.0
    p = int((math.sin(t * 3) + 1) * .5 * 255)
    rs = fM.render("[ PRESS R TO RESTART ]", True, C_CYAN);  rs.set_alpha(p)
    surf.blit(rs, (W//2 - rs.get_width()//2, 510))


# ── GAME ──────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("ROGUE DRONE")
        self.clock = pygame.time.Clock()
        make_scanline()
        _f = "consolas,courier new,courier,monospace"
        self.fT = pygame.font.SysFont(_f, 54, bold=True)
        self.fL = pygame.font.SysFont(_f, 36, bold=True)
        self.fM = pygame.font.SysFont(_f, 24)
        self.fS = pygame.font.SysFont(_f, 16)
        self.hi = 0;  self.state = S_MENU;  self._gs = None

    # ── reset ─────────────────────────────────────────────────────────────────
    def _reset(self):
        self.player = Player()
        self.enemies = [];  self.bullets = []
        self.pickups = []
        self.fx = Particles();  self.shake = Shake()
        self.wm = WaveManager();  self.scroll = 0.0
        self._start_wave(1)

    def _start_wave(self, n):
        self.wm.wave = n;  self.wm.between = False
        self.enemies = self.wm.spawn(n, self.player.x, self.player.y)
        self.bullets = []

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            mx, my = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit();  sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit();  sys.exit()
                    if ev.key == pygame.K_r and self.state in (S_DEAD, S_MENU):
                        self.state = S_PLAY;  self._reset()
                if ev.type == pygame.MOUSEBUTTONDOWN and self.state == S_MENU:
                    self.state = S_PLAY;  self._reset()
            keys = pygame.key.get_pressed()
            if   self.state == S_PLAY: self._update(dt, keys, mx, my);  self._draw()
            elif self.state == S_MENU: draw_menu(self.screen, self.hi, self.fT, self.fL, self.fM, self.fS)
            elif self.state == S_DEAD: self._draw_dead()
            pygame.display.flip()

    # ── update ────────────────────────────────────────────────────────────────
    def _update(self, dt, keys, mx, my):
        self.scroll += dt * 28
        pl = self.player

        pl.update(dt, keys, mx, my, self.bullets, self.fx)
        if not pl.alive:
            self.hi = max(self.hi, pl.score);  self.state = S_DEAD;  return

        for e in self.enemies:
            e.update(dt, pl.x, pl.y, self.bullets, self.fx)
        for b in self.bullets:  b.update(dt)
        for p in self.pickups:  p.update(dt)
        self.fx.update(dt);  self.shake.update(dt)

        # player bullets vs enemies
        for b in self.bullets:
            if not b.alive or not b.is_player: continue
            for e in self.enemies:
                if not e.alive: continue
                if math.hypot(b.x - e.x, b.y - e.y) < e.R + b.size:
                    b.alive = False
                    e.take_hit(b.damage, self.fx)
                    self.shake.add(.15)
                    if not e.alive:
                        pl.score += e.SCORE;  pl.kills += 1
                        if random.random() < .22:
                            kind = random.choice(['health', 'rapid', 'dmg'])
                            self.pickups.append(Pickup(e.x, e.y, kind))

        # enemy bullets vs player
        for b in self.bullets:
            if not b.alive or b.is_player: continue
            if math.hypot(b.x - pl.x, b.y - pl.y) < pl.R + b.size:
                b.alive = False
                pl.take_hit(b.damage, self.fx)
                self.shake.add(.3)

        # enemy melee vs player  (continuous, bypasses invuln)
        for e in self.enemies:
            if not e.alive: continue
            if math.hypot(e.x - pl.x, e.y - pl.y) < e.R + pl.R:
                pl.take_melee(e.MELEE, dt, self.fx)
                self.shake.add(.08)

        # pickups vs player
        for p in self.pickups:
            if not p.alive: continue
            if math.hypot(p.x - pl.x, p.y - pl.y) < pl.R + p.R:
                p.alive = False
                self.fx.burst(p.x, p.y, p.color, 12, 90, 3)
                if   p.kind == 'health': pl.hp = min(pl.MAX_HP, pl.hp + 35)
                elif p.kind == 'rapid':  pl.rapid_t = 5.0
                elif p.kind == 'dmg':    pl.dmg_boost_t = 5.0

        # death check (melee may have killed player)
        if not pl.alive:
            self.hi = max(self.hi, pl.score);  self.state = S_DEAD;  return

        # cleanup
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.pickups = [p for p in self.pickups if p.alive]

        # wave progression
        if not self.wm.between and len(self.enemies) == 0:
            self.wm.between = True;  self.wm.btimer = 3.0
            pl.score += 500 * self.wm.wave
        if self.wm.between:
            self.wm.btimer -= dt
            if self.wm.btimer <= 0:
                self._start_wave(self.wm.wave + 1)

    # ── draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        gs = pygame.Surface((W, H))
        draw_bg(gs, self.scroll)
        for p in self.pickups:  p.draw(gs)
        for b in self.bullets:  b.draw(gs)
        for e in self.enemies:  e.draw(gs)
        self.player.draw(gs)
        self.fx.draw(gs)
        ox, oy = self.shake.off
        self.screen.fill(BG)
        self.screen.blit(gs, (int(ox), int(oy)))
        draw_hud(self.screen, self.player, self.wm, self.fL, self.fM, self.fS)
        self._gs = gs   # cache for death overlay

    def _draw_dead(self):
        if self._gs:
            self.screen.blit(self._gs, (0, 0))
        else:
            self.screen.fill(BG)
        draw_dead(self.screen, self.player, self.wm,
                  self.fT, self.fL, self.fM, self.fS)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
