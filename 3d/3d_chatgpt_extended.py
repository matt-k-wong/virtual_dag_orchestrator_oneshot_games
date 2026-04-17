# game.py
import sys
import math
import random
import subprocess
import importlib
from dataclasses import dataclass

def _load_pygame():
    try:
        import pygame as _pg
        return _pg
    except Exception:
        for pkg in ("pygame-ce", "pygame"):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                return importlib.import_module("pygame")
            except Exception:
                continue
        raise RuntimeError("Could not import or install pygame/pygame-ce.")

pygame = _load_pygame()

W, H = 1280, 720
HALF_W, HALF_H = W // 2, H // 2
FOV = 620.0
DRAW_DIST = 1900.0
NEAR_Z = 8.0
TITLE = "Afterburn Canyon"

def clamp(v, a, b):
    return a if v < a else b if v > b else v

def mix(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )

@dataclass
class Enemy:
    kind: str
    x: float
    y: float
    z: float
    home_x: float
    home_y: float
    amp_x: float
    amp_y: float
    phase: float
    radius: float
    hp: int
    cooldown: float
    alive: bool = True
    flash: float = 0.0

@dataclass
class Bullet:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    radius: float
    life: float
    friendly: bool
    damage: int
    color: tuple

@dataclass
class Gate:
    z: float
    bonus: int
    passed: bool = False

@dataclass
class Particle:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    life: float
    max_life: float
    size: float
    color: tuple

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.font_sm = pygame.font.SysFont("consolas", 20)
        self.font_md = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_lg = pygame.font.SysFont("consolas", 46, bold=True)
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        self.overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        self.bg = self._make_background()
        self.best_score = 0
        self._reset()

    def _reset(self):
        self.rng = random.Random(7)
        self.state = "play"
        self.paused = False
        self.time_alive = 0.0
        self.px = 0.0
        self.py = 0.0
        self.pz = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 150.0
        self.bank = 0.0
        self.health = 100.0
        self.points = 0
        self.combo = 0
        self.player_fire_cd = 0.0
        self.invuln = 0.0
        self.wall_hit_cd = 0.0
        self.flash_red = 0.0
        self.flash_cyan = 0.0
        self.shake = 0.0
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.help_timer = 8.0
        self.wave_flash = 1.4
        self.last_wave = 1
        self.enemies = []
        self.bullets = []
        self.gates = []
        self.particles = []
        self.next_spawn_z = 320.0
        self.next_gate_z = 430.0
        self.spawn_ahead()

    def difficulty(self):
        return 1.0 + self.pz / 1800.0

    def wave(self):
        return 1 + int(self.pz / 1400.0)

    def total_score(self):
        return self.points + int(self.pz * 0.12)

    def _make_background(self):
        surf = pygame.Surface((W, H))
        top = (6, 9, 22)
        mid = (19, 8, 44)
        bot = (10, 15, 24)
        for y in range(H):
            t = y / (H - 1)
            if t < 0.55:
                c = mix(top, mid, t / 0.55)
            else:
                c = mix(mid, bot, (t - 0.55) / 0.45)
            pygame.draw.line(surf, c, (0, y), (W, y))
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        for r, a in ((240, 24), (180, 36), (110, 56)):
            pygame.draw.circle(glow, (70, 180, 255, a), (HALF_W, int(H * 0.52)), r)
        for r, a in ((220, 18), (140, 30), (80, 42)):
            pygame.draw.circle(glow, (255, 80, 180, a), (HALF_W, int(H * 0.6)), r)
        surf.blit(glow, (0, 0))
        stars = random.Random(123)
        for _ in range(220):
            x = stars.randrange(0, W)
            y = stars.randrange(0, int(H * 0.7))
            c = 150 + stars.randrange(80)
            surf.set_at((x, y), (c, c, min(255, c + 30)))
        for i in range(24):
            yy = int(H * 0.52 + i * 6)
            pygame.draw.line(surf, (20, 24, 36), (0, yy), (W, yy), 1)
        return surf

    def tunnel_at(self, z):
        diff = self.difficulty()
        cx = 140.0 * math.sin(z * 0.0052) + 60.0 * math.sin(z * 0.011 + 0.8)
        cy = 85.0 * math.sin(z * 0.0044 + 1.7) + 42.0 * math.cos(z * 0.0091)
        w = max(182.0, 252.0 - diff * 10.5 + 18.0 * math.sin(z * 0.0066))
        h = max(128.0, 192.0 - diff * 7.5 + 15.0 * math.sin(z * 0.0077 + 0.9))
        return cx, cy, w, h

    def project(self, x, y, z):
        relx = x - self.px
        rely = y - self.py
        relz = z - self.pz
        if relz <= NEAR_Z:
            return None
        c = math.cos(-self.bank)
        s = math.sin(-self.bank)
        rx = relx * c - rely * s
        ry = relx * s + rely * c
        scale = FOV / relz
        sx = HALF_W + self.shake_x + rx * scale
        sy = HALF_H + self.shake_y - ry * scale
        return int(sx), int(sy), scale, relz

    def draw_text(self, surf, font, text, x, y, color, align="topleft"):
        img_shadow = font.render(str(text), True, (0, 0, 0))
        rect_shadow = img_shadow.get_rect()
        setattr(rect_shadow, align, (x + 2, y + 2))
        surf.blit(img_shadow, rect_shadow)
        img = font.render(str(text), True, color)
        rect = img.get_rect()
        setattr(rect, align, (x, y))
        surf.blit(img, rect)

    def draw_glow_circle(self, surf, pos, radius, color, alpha=110):
        r = max(1, int(radius))
        x, y = int(pos[0]), int(pos[1])
        if r > 180:
            r = 180
        pygame.draw.circle(surf, (*color, max(20, alpha // 5)), (x, y), max(1, int(r * 2.6)))
        pygame.draw.circle(surf, (*color, max(30, alpha // 2)), (x, y), max(1, int(r * 1.7)))
        pygame.draw.circle(surf, (*color, alpha), (x, y), r)

    def emit_particles(self, x, y, z, color, count=12, speed=120.0):
        for _ in range(count):
            a = self.rng.uniform(0.0, math.tau)
            e = self.rng.uniform(-1.0, 1.0)
            sp = self.rng.uniform(speed * 0.35, speed)
            vx = math.cos(a) * math.cos(e) * sp
            vy = math.sin(a) * math.cos(e) * sp
            vz = math.sin(e) * sp + self.rng.uniform(-55.0, 55.0)
            life = self.rng.uniform(0.35, 0.9)
            self.particles.append(
                Particle(x, y, z, vx, vy, vz, life, life, self.rng.uniform(2.0, 4.8), color)
            )
        if len(self.particles) > 260:
            self.particles = self.particles[-260:]

    def damage(self, amount):
        if self.invuln > 0.0 or self.state != "play":
            return
        self.health = max(0.0, self.health - amount)
        self.invuln = 0.18
        self.combo = 0
        self.flash_red = min(180.0, self.flash_red + 125.0)
        self.shake += amount * 0.35
        self.emit_particles(self.px, self.py, self.pz + 85.0, (255, 110, 80), 10, 110.0)
        if self.health <= 0.0:
            self.best_score = max(self.best_score, self.total_score())
            self.state = "gameover"

    def destroy_enemy(self, enemy):
        if not enemy.alive:
            return
        enemy.alive = False
        base = 145 if enemy.kind == "drone" else 90
        self.points += base + self.combo * 12
        self.combo = min(self.combo + 1, 9)
        self.flash_cyan = min(120.0, self.flash_cyan + 55.0)
        self.shake += 4.0 if enemy.kind == "drone" else 2.5
        color = (255, 120, 80) if enemy.kind == "drone" else (255, 180, 70)
        self.emit_particles(enemy.x, enemy.y, enemy.z, color, 18 if enemy.kind == "drone" else 12, 160.0)

    def fire_player(self):
        if self.player_fire_cd > 0.0 or self.state != "play":
            return
        self.player_fire_cd = 0.11
        for side in (-8.0, 8.0):
            self.bullets.append(
                Bullet(
                    self.px + side,
                    self.py,
                    self.pz + 12.0,
                    self.vx * 0.12 + side * 0.16,
                    self.vy * 0.10,
                    self.speed + 780.0,
                    5.0,
                    1.15,
                    True,
                    1,
                    (80, 240, 255),
                )
            )
        self.flash_cyan = min(110.0, self.flash_cyan + 18.0)
        self.shake += 0.5
        self.emit_particles(self.px, self.py, self.pz + 42.0, (80, 240, 255), 6, 70.0)

    def spawn_enemy_shot(self, enemy):
        tx = self.px + self.vx * 0.25
        ty = self.py + self.vy * 0.25
        tz = self.pz + 12.0
        dx = tx - enemy.x
        dy = ty - enemy.y
        dz = tz - enemy.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        speed = 315.0 + self.difficulty() * 18.0
        self.bullets.append(
            Bullet(
                enemy.x,
                enemy.y,
                enemy.z - 4.0,
                dx / dist * speed,
                dy / dist * speed,
                dz / dist * speed,
                7.0,
                3.0,
                False,
                9,
                (255, 125, 80),
            )
        )

    def spawn_pattern(self, z):
        cx, cy, w, h = self.tunnel_at(z)
        choice = self.rng.random()
        wave = self.wave()
        drone_hp = 2 + (1 if wave >= 4 else 0)

        def add_enemy(kind, fx, fy, dz=0.0):
            ex = cx + fx * w * 0.33
            ey = cy + fy * h * 0.33
            phase = self.rng.uniform(0.0, math.tau)
            if kind == "drone":
                self.enemies.append(
                    Enemy(
                        "drone",
                        ex,
                        ey,
                        z + dz,
                        ex,
                        ey,
                        self.rng.uniform(10.0, 28.0),
                        self.rng.uniform(9.0, 24.0),
                        phase,
                        22.0,
                        drone_hp,
                        self.rng.uniform(0.4, 1.5),
                    )
                )
            else:
                self.enemies.append(
                    Enemy(
                        "mine",
                        ex,
                        ey,
                        z + dz,
                        ex,
                        ey,
                        self.rng.uniform(6.0, 16.0),
                        self.rng.uniform(6.0, 16.0),
                        phase,
                        16.0,
                        1,
                        99.0,
                    )
                )

        if choice < 0.22:
            add_enemy("drone", 0.0, 0.0)
        elif choice < 0.42:
            add_enemy("drone", -0.48, 0.05)
            add_enemy("drone", 0.48, -0.05, 25.0)
        elif choice < 0.60:
            add_enemy("mine", -0.5, 0.0)
            add_enemy("mine", 0.0, 0.18, 24.0)
            add_enemy("mine", 0.5, -0.1, 48.0)
        elif choice < 0.77:
            add_enemy("drone", 0.0, -0.28)
            add_enemy("mine", -0.42, 0.26, 30.0)
            add_enemy("mine", 0.42, 0.26, 60.0)
        else:
            add_enemy("drone", -0.45, -0.22)
            add_enemy("drone", 0.45, -0.22, 28.0)
            if wave >= 3:
                add_enemy("mine", 0.0, 0.35, 58.0)

    def spawn_ahead(self):
        horizon = self.pz + DRAW_DIST
        while self.next_gate_z < horizon:
            self.gates.append(Gate(self.next_gate_z, 75 + self.wave() * 5))
            self.next_gate_z += 360.0
        while self.next_spawn_z < horizon:
            self.spawn_pattern(self.next_spawn_z)
            gap = max(130.0, 245.0 - self.difficulty() * 9.0)
            self.next_spawn_z += gap + self.rng.uniform(-35.0, 35.0)

    def update_gates(self):
        kept = []
        for gate in self.gates:
            if not gate.passed and gate.z <= self.pz + 16.0:
                cx, cy, w, h = self.tunnel_at(gate.z)
                if abs(self.px - cx) < w * 0.22 and abs(self.py - cy) < h * 0.22:
                    gate.passed = True
                    self.points += gate.bonus + self.combo * 10
                    self.combo = min(self.combo + 1, 9)
                    self.health = min(100.0, self.health + 5.0)
                    self.flash_cyan = min(140.0, self.flash_cyan + 60.0)
                    self.shake += 1.6
                    self.emit_particles(cx, cy, gate.z, (110, 255, 210), 20, 135.0)
                else:
                    gate.passed = True
                    self.combo = 0
            if gate.z > self.pz - 120.0:
                kept.append(gate)
        self.gates = kept

    def update_enemies(self, dt):
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            t = self.time_alive + enemy.phase
            enemy.flash = max(0.0, enemy.flash - dt * 4.0)
            if enemy.kind == "drone":
                enemy.x = enemy.home_x + math.sin(t * 1.6) * enemy.amp_x
                enemy.y = enemy.home_y + math.cos(t * 1.9) * enemy.amp_y
                relz = enemy.z - self.pz
                enemy.cooldown -= dt
                if 110.0 < relz < 880.0 and enemy.cooldown <= 0.0:
                    self.spawn_enemy_shot(enemy)
                    enemy.cooldown = max(0.55, 1.65 - self.difficulty() * 0.06) + self.rng.random() * 0.65
            else:
                enemy.x = enemy.home_x + math.sin(t * 1.7) * enemy.amp_x * 0.28
                enemy.y = enemy.home_y + math.sin(t * 1.3 + 1.2) * enemy.amp_y * 0.28

            if enemy.z < self.pz + 18.0:
                dx = enemy.x - self.px
                dy = enemy.y - self.py
                if dx * dx + dy * dy < (enemy.radius + 12.0) ** 2:
                    self.damage(20.0 if enemy.kind == "mine" else 14.0)
                    self.destroy_enemy(enemy)

        self.enemies = [e for e in self.enemies if e.alive and e.z > self.pz - 160.0]

    def update_bullets(self, dt):
        kept = []
        for bullet in self.bullets:
            bullet.x += bullet.vx * dt
            bullet.y += bullet.vy * dt
            bullet.z += bullet.vz * dt
            bullet.life -= dt
            if bullet.life <= 0.0:
                continue

            if bullet.friendly:
                hit = False
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    dz = abs(bullet.z - enemy.z)
                    if dz < max(16.0, enemy.radius * 1.15):
                        rr = bullet.radius + enemy.radius * 0.78
                        dx = bullet.x - enemy.x
                        dy = bullet.y - enemy.y
                        if dx * dx + dy * dy < rr * rr:
                            enemy.hp -= bullet.damage
                            enemy.flash = 1.0
                            self.shake += 0.65
                            if enemy.hp <= 0:
                                self.destroy_enemy(enemy)
                            else:
                                self.emit_particles(enemy.x, enemy.y, enemy.z, (255, 180, 90), 6, 70.0)
                            hit = True
                            break
                if hit:
                    continue
            else:
                if self.pz - 30.0 < bullet.z < self.pz + 18.0:
                    dx = bullet.x - self.px
                    dy = bullet.y - self.py
                    if dx * dx + dy * dy < (bullet.radius + 14.0) ** 2:
                        self.damage(float(bullet.damage))
                        self.emit_particles(self.px, self.py, self.pz + 60.0, (255, 120, 80), 8, 85.0)
                        continue

            if self.pz - 80.0 < bullet.z < self.pz + DRAW_DIST + 100.0:
                kept.append(bullet)
        self.bullets = kept

    def update_particles(self, dt):
        kept = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.z += p.vz * dt
            p.life -= dt
            if p.life > 0.0 and self.pz - 120.0 < p.z < self.pz + DRAW_DIST + 120.0:
                kept.append(p)
        self.particles = kept[-260:]

    def handle_tunnel_collision(self):
        cx, cy, w, h = self.tunnel_at(self.pz + 32.0)
        hw = w * 0.5 - 26.0
        hh = h * 0.5 - 26.0
        hit = False
        if self.px < cx - hw:
            self.px = cx - hw
            self.vx *= -0.22
            hit = True
        elif self.px > cx + hw:
            self.px = cx + hw
            self.vx *= -0.22
            hit = True

        if self.py < cy - hh:
            self.py = cy - hh
            self.vy *= -0.22
            hit = True
        elif self.py > cy + hh:
            self.py = cy + hh
            self.vy *= -0.22
            hit = True

        if hit and self.wall_hit_cd <= 0.0:
            self.damage(10.0)
            self.wall_hit_cd = 0.18
            self.emit_particles(self.px, self.py, self.pz + 95.0, (255, 180, 70), 12, 130.0)

    def update_play(self, dt, keys):
        self.time_alive += dt
        self.help_timer = max(0.0, self.help_timer - dt)
        self.player_fire_cd = max(0.0, self.player_fire_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.wall_hit_cd = max(0.0, self.wall_hit_cd - dt)
        self.flash_red = max(0.0, self.flash_red - dt * 310.0)
        self.flash_cyan = max(0.0, self.flash_cyan - dt * 220.0)
        self.wave_flash = max(0.0, self.wave_flash - dt)
        self.shake = max(0.0, self.shake - dt * 8.0)

        ix = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        iy = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(keys[pygame.K_s] or keys[pygame.K_DOWN])
        boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if keys[pygame.K_SPACE]:
            self.fire_player()

        accel = 430.0
        self.vx += ix * accel * dt
        self.vy += iy * accel * dt
        self.vx *= 0.93 ** (dt * 60.0)
        self.vy *= 0.93 ** (dt * 60.0)
        self.vx = clamp(self.vx, -245.0, 245.0)
        self.vy = clamp(self.vy, -245.0, 245.0)

        self.px += self.vx * dt
        self.py += self.vy * dt

        target_speed = 145.0 + min(100.0, self.difficulty() * 10.0) + (65.0 if boost else 0.0)
        self.speed += (target_speed - self.speed) * 2.6 * dt
        self.pz += self.speed * dt

        bank_target = clamp(-ix * 0.42 - self.vx * 0.0026, -0.6, 0.6)
        self.bank += (bank_target - self.bank) * 4.2 * dt

        current_wave = self.wave()
        if current_wave > self.last_wave:
            self.last_wave = current_wave
            self.wave_flash = 1.45

        self.spawn_ahead()
        self.update_gates()
        self.update_enemies(dt)
        self.update_bullets(dt)
        self.update_particles(dt)
        self.handle_tunnel_collision()

    def render_tunnel(self):
        slices = []
        z = self.pz + 80.0
        while z < self.pz + DRAW_DIST:
            cx, cy, w, h = self.tunnel_at(z)
            corners = [
                (cx - w * 0.5, cy + h * 0.5, z),
                (cx + w * 0.5, cy + h * 0.5, z),
                (cx + w * 0.5, cy - h * 0.5, z),
                (cx - w * 0.5, cy - h * 0.5, z),
            ]
            proj = [self.project(*p) for p in corners]
            center = self.project(cx, cy, z)
            if all(proj) and center:
                slices.append((z, proj, center))
            z += 60.0

        center_points = [s[2][:2] for s in slices]
        if len(center_points) > 2:
            pygame.draw.lines(self.fx, (90, 220, 255, 75), False, center_points, 2)

        for i in range(len(slices) - 2, -1, -1):
            z1, p1, _ = slices[i]
            _, p2, _ = slices[i + 1]
            t = 1.0 - (z1 - self.pz) / DRAW_DIST
            t = clamp(t, 0.0, 1.0)

            left_col = mix((16, 20, 38), (50, 60, 120), t)
            right_col = mix((18, 14, 44), (85, 45, 115), t)
            top_col = mix((12, 10, 24), (35, 22, 62), t)
            bottom_col = mix((10, 18, 28), (18, 62, 82), t)

            left = [p1[0][:2], p1[3][:2], p2[3][:2], p2[0][:2]]
            right = [p1[1][:2], p1[2][:2], p2[2][:2], p2[1][:2]]
            top = [p1[0][:2], p1[1][:2], p2[1][:2], p2[0][:2]]
            bottom = [p1[3][:2], p1[2][:2], p2[2][:2], p2[3][:2]]

            pygame.draw.polygon(self.screen, top_col, top)
            pygame.draw.polygon(self.screen, left_col, left)
            pygame.draw.polygon(self.screen, right_col, right)
            pygame.draw.polygon(self.screen, bottom_col, bottom)

            outline_alpha = int(55 + 95 * t)
            pygame.draw.polygon(self.fx, (110, 235, 255, outline_alpha), left, 1)
            pygame.draw.polygon(self.fx, (190, 80, 255, outline_alpha), right, 1)
            pygame.draw.polygon(self.fx, (70, 120, 255, outline_alpha // 2), top, 1)
            pygame.draw.polygon(self.fx, (60, 255, 180, outline_alpha // 2), bottom, 1)

            if i % 3 == 0:
                ring = [p1[0][:2], p1[1][:2], p1[2][:2], p1[3][:2]]
                pygame.draw.lines(self.fx, (140, 220, 255, 44), True, ring, 1)

    def render_gates(self):
        for gate in self.gates:
            relz = gate.z - self.pz
            if relz < 30.0 or relz > DRAW_DIST:
                continue
            cx, cy, w, h = self.tunnel_at(gate.z)
            gw = w * 0.42
            gh = h * 0.42
            corners = [
                (cx - gw * 0.5, cy + gh * 0.5, gate.z),
                (cx + gw * 0.5, cy + gh * 0.5, gate.z),
                (cx + gw * 0.5, cy - gh * 0.5, gate.z),
                (cx - gw * 0.5, cy - gh * 0.5, gate.z),
            ]
            proj = [self.project(*p) for p in corners]
            if not all(proj):
                continue
            pts = [p[:2] for p in proj]
            pulse = 0.5 + 0.5 * math.sin(self.time_alive * 5.0 + gate.z * 0.01)
            col = (int(100 + 50 * pulse), 255, int(160 + 70 * pulse))
            pygame.draw.lines(self.fx, (*col, 55), True, pts, 7)
            pygame.draw.lines(self.fx, (*col, 125), True, pts, 3)
            pygame.draw.lines(self.screen, col, True, pts, 1)

    def render_particles(self):
        for p in self.particles:
            pr = self.project(p.x, p.y, p.z)
            if not pr:
                continue
            sx, sy, scale, relz = pr
            if relz < 10.0:
                continue
            fade = p.life / p.max_life
            radius = max(1, int(p.size * scale * 0.85))
            alpha = int(180 * fade)
            pygame.draw.circle(self.fx, (*p.color, alpha), (sx, sy), radius)

    def render_bullets(self):
        for b in sorted(self.bullets, key=lambda q: q.z, reverse=True):
            pr = self.project(b.x, b.y, b.z)
            if not pr:
                continue
            sx, sy, scale, relz = pr
            if relz < 12.0:
                continue
            rad = max(2, int(b.radius * scale * 1.4))
            col = b.color
            self.draw_glow_circle(self.fx, (sx, sy), rad * 1.7, col, 100 if b.friendly else 125)
            pygame.draw.circle(self.screen, col, (sx, sy), max(1, rad))

    def render_enemies(self):
        for enemy in sorted(self.enemies, key=lambda e: e.z, reverse=True):
            if not enemy.alive:
                continue
            pr = self.project(enemy.x, enemy.y, enemy.z)
            if not pr:
                continue
            sx, sy, scale, relz = pr
            if relz < 20.0:
                continue
            r = max(3, int(enemy.radius * scale * 1.42))
            if enemy.kind == "drone":
                self.draw_glow_circle(self.fx, (sx, sy), int(r * 1.8), (255, 120, 80), 95)
                body = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
                wing_l = [(sx - r * 2, sy), (sx - r, sy - r * 0.35), (sx - r, sy + r * 0.35)]
                wing_r = [(sx + r * 2, sy), (sx + r, sy - r * 0.35), (sx + r, sy + r * 0.35)]
                fill = (95 + int(100 * enemy.flash), 48 + int(110 * enemy.flash), 55 + int(90 * enemy.flash))
                pygame.draw.polygon(self.screen, fill, body)
                pygame.draw.polygon(self.screen, (180, 80, 70), wing_l)
                pygame.draw.polygon(self.screen, (180, 80, 70), wing_r)
                pygame.draw.lines(self.screen, (255, 220, 170), False, [(sx - r, sy), (sx + r, sy)], 2)
                if enemy.flash > 0.0:
                    self.draw_glow_circle(self.fx, (sx, sy), max(2, int(r * 0.8)), (255, 255, 255), 120)
            else:
                self.draw_glow_circle(self.fx, (sx, sy), int(r * 1.6), (255, 195, 80), 105)
                pts = []
                spikes = 8
                spin = self.time_alive * 3.0 + enemy.phase
                for i in range(spikes * 2):
                    ang = spin + i * math.pi / spikes
                    rr = r * 1.6 if i % 2 == 0 else r * 0.7
                    pts.append((sx + math.cos(ang) * rr, sy + math.sin(ang) * rr))
                pygame.draw.polygon(self.screen, (185, 145, 55), pts)
                pygame.draw.circle(self.screen, (255, 220, 120), (sx, sy), max(2, int(r * 0.55)))

    def render_hud(self):
        score = self.total_score()
        hp_ratio = self.health / 100.0
        hp_col = mix((255, 70, 70), (90, 255, 170), hp_ratio)

        pygame.draw.rect(self.screen, (0, 0, 0), (22, 20, 270, 28), border_radius=6)
        pygame.draw.rect(self.screen, (28, 42, 56), (24, 22, 266, 24), border_radius=5)
        pygame.draw.rect(self.screen, hp_col, (24, 22, int(266 * hp_ratio), 24), border_radius=5)
        pygame.draw.rect(self.screen, (180, 245, 255), (24, 22, 266, 24), 2, border_radius=5)

        self.draw_text(self.screen, self.font_sm, f"HP {int(self.health):03d}", 158, 34, (255, 255, 255), "center")
        self.draw_text(self.screen, self.font_md, f"SCORE {score}", W - 26, 26, (180, 255, 255), "topright")
        self.draw_text(self.screen, self.font_sm, f"DIST {int(self.pz)} m", W - 26, 66, (210, 230, 255), "topright")
        self.draw_text(self.screen, self.font_sm, f"WAVE {self.wave()}", W - 26, 92, (255, 190, 120), "topright")
        self.draw_text(self.screen, self.font_sm, f"COMBO x{self.combo + 1}", W - 26, 118, (120, 255, 220), "topright")
        self.draw_text(self.screen, self.font_sm, f"SPEED {int(self.speed)}", 24, 60, (120, 235, 255), "topleft")

        center = (int(HALF_W + self.shake_x * 0.18), int(HALF_H + self.shake_y * 0.18))
        cx, cy = center
        pygame.draw.circle(self.fx, (90, 240, 255, 55), center, 22, 2)
        pygame.draw.line(self.fx, (90, 240, 255, 90), (cx - 36, cy), (cx - 10, cy), 2)
        pygame.draw.line(self.fx, (90, 240, 255, 90), (cx + 10, cy), (cx + 36, cy), 2)
        pygame.draw.line(self.fx, (90, 240, 255, 90), (cx, cy - 36), (cx, cy - 10), 2)
        pygame.draw.line(self.fx, (90, 240, 255, 90), (cx, cy + 10), (cx, cy + 36), 2)

        hx = math.cos(-self.bank) * 210
        hy = math.sin(-self.bank) * 210
        pygame.draw.line(self.fx, (165, 90, 255, 52), (cx - hx, cy - hy), (cx + hx, cy + hy), 2)

        guide = self.project(*self.tunnel_at(self.pz + 500.0)[:2], self.pz + 500.0)
        if guide:
            gx, gy, _, _ = guide
            diamond = [(gx, gy - 12), (gx + 12, gy), (gx, gy + 12), (gx - 12, gy)]
            pygame.draw.lines(self.fx, (120, 255, 210, 130), True, diamond, 2)

        bottom = H - 72
        pygame.draw.line(self.fx, (90, 220, 255, 80), (130, bottom), (230, H - 28), 2)
        pygame.draw.line(self.fx, (90, 220, 255, 80), (W - 130, bottom), (W - 230, H - 28), 2)
        pygame.draw.line(self.fx, (90, 220, 255, 80), (300, H - 28), (W - 300, H - 28), 2)
        pygame.draw.line(self.fx, (90, 220, 255, 80), (HALF_W - 140, H - 28), (HALF_W - 40, H - 10), 2)
        pygame.draw.line(self.fx, (90, 220, 255, 80), (HALF_W + 140, H - 28), (HALF_W + 40, H - 10), 2)

        t_cx, t_cy, tw, th = self.tunnel_at(self.pz + 40.0)
        danger = max(
            abs(self.px - t_cx) / max(1.0, tw * 0.5 - 26.0),
            abs(self.py - t_cy) / max(1.0, th * 0.5 - 26.0),
        )
        if danger > 0.78 and self.state == "play":
            pulse = 0.5 + 0.5 * math.sin(self.time_alive * 12.0)
            col = (255, int(90 + 100 * pulse), int(90 + 50 * pulse))
            self.draw_text(self.screen, self.font_md, "PULL AWAY", HALF_W, 86, col, "center")

        if self.help_timer > 0.0 and self.state == "play":
            alpha = int(180 * min(1.0, self.help_timer / 2.5))
            self.overlay.fill((0, 0, 0, 0))
            pygame.draw.rect(self.overlay, (0, 0, 0, alpha), (HALF_W - 290, H - 120, 580, 64), border_radius=12)
            pygame.draw.rect(self.overlay, (90, 220, 255, min(220, alpha + 30)), (HALF_W - 290, H - 120, 580, 64), 2, border_radius=12)
            self.screen.blit(self.overlay, (0, 0))
            self.draw_text(
                self.screen,
                self.font_sm,
                "WASD / ARROWS steer   SHIFT boost   SPACE fire   P pause   ESC quit",
                HALF_W,
                H - 88,
                (220, 245, 255),
                "center",
            )

        if self.wave_flash > 0.0 and self.state == "play":
            a = self.wave_flash / 1.45
            col = (255, int(150 + 80 * a), 120)
            self.draw_text(self.screen, self.font_lg, f"WAVE {self.wave()}", HALF_W, 118, col, "center")

    def render_state_overlay(self):
        if self.paused:
            self.overlay.fill((0, 0, 0, 145))
            self.screen.blit(self.overlay, (0, 0))
            self.draw_text(self.screen, self.font_lg, "PAUSED", HALF_W, HALF_H - 40, (220, 245, 255), "center")
            self.draw_text(self.screen, self.font_sm, "Press P to resume", HALF_W, HALF_H + 14, (200, 220, 240), "center")
        elif self.state == "gameover":
            self.overlay.fill((0, 0, 0, 170))
            self.screen.blit(self.overlay, (0, 0))
            self.draw_text(self.screen, self.font_lg, "CRAFT LOST", HALF_W, HALF_H - 94, (255, 125, 95), "center")
            self.draw_text(self.screen, self.font_md, f"Final Score  {self.total_score()}", HALF_W, HALF_H - 20, (220, 245, 255), "center")
            self.draw_text(self.screen, self.font_sm, f"Distance  {int(self.pz)} m", HALF_W, HALF_H + 28, (200, 220, 240), "center")
            self.draw_text(self.screen, self.font_sm, f"Best  {max(self.best_score, self.total_score())}", HALF_W, HALF_H + 60, (120, 255, 210), "center")
            self.draw_text(self.screen, self.font_sm, "Press R to restart   |   ESC to quit", HALF_W, HALF_H + 110, (255, 220, 170), "center")

        if self.flash_red > 0.0:
            self.overlay.fill((170, 24, 24, int(self.flash_red)))
            self.screen.blit(self.overlay, (0, 0))
        if self.flash_cyan > 0.0:
            self.overlay.fill((20, 120, 120, int(self.flash_cyan * 0.5)))
            self.screen.blit(self.overlay, (0, 0))

    def render(self):
        self.shake_x = math.sin(self.time_alive * 47.0) * self.shake * 0.55
        self.shake_y = math.cos(self.time_alive * 51.0) * self.shake * 0.55

        self.screen.blit(self.bg, (0, 0))
        self.fx.fill((0, 0, 0, 0))

        self.render_tunnel()
        self.render_gates()
        self.render_particles()
        self.render_bullets()
        self.render_enemies()

        self.screen.blit(self.fx, (0, 0))
        self.render_hud()
        self.render_state_overlay()

        self.draw_text(self.screen, self.font_sm, TITLE, HALF_W, 22, (120, 240, 255), "center")
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p and self.state == "play":
                        self.paused = not self.paused
                    elif event.key == pygame.K_r and self.state == "gameover":
                        self._reset()

            if self.state == "play" and not self.paused:
                self.update_play(dt, keys)

            self.render()

        pygame.quit()

if __name__ == "__main__":
    Game().run()
