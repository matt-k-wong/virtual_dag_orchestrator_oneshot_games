# game.py
import math
import random
import subprocess
import sys
from dataclasses import dataclass


def ensure_pygame():
    try:
        import pygame  # type: ignore
        return pygame
    except Exception:
        for package in ("pygame-ce", "pygame"):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                import pygame  # type: ignore
                return pygame
            except Exception:
                continue
        raise


pygame = ensure_pygame()
Vec2 = pygame.Vector2

WIDTH, HEIGHT = 960, 540
FPS = 60
TITLE = "Nebula Rift"

BG = (8, 11, 24)
BG2 = (14, 19, 40)
WHITE = (235, 245, 255)
CYAN = (108, 232, 255)
CYAN2 = (35, 176, 255)
MAGENTA = (255, 82, 184)
VIOLET = (145, 105, 255)
ORANGE = (255, 163, 70)
RED = (255, 80, 96)
GREEN = (108, 255, 163)
YELLOW = (255, 220, 92)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_to(vec):
    return math.atan2(vec.y, vec.x)


def from_angle(a):
    return Vec2(math.cos(a), math.sin(a))


def draw_text(surf, text, font, color, pos, align="topleft"):
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, align, pos)
    surf.blit(img, rect)
    return rect


def circle_fx(surf, color, pos, radius, alpha, width=0):
    alpha = int(clamp(alpha, 0, 255))
    if alpha <= 0 or radius <= 0:
        return
    pygame.draw.circle(surf, (*color, alpha), (int(pos[0]), int(pos[1])), int(radius), width)


def burst_particles(game, pos, color, count, speed_range=(80, 260), size_range=(2, 5), life_range=(0.25, 0.8)):
    for _ in range(count):
        ang = random.random() * math.tau
        spd = random.uniform(*speed_range)
        vel = from_angle(ang) * spd
        size = random.uniform(*size_range)
        life = random.uniform(*life_range)
        game.particles.append(Particle(Vec2(pos), vel, color, life, size, drag=2.2))


@dataclass
class Particle:
    pos: Vec2
    vel: Vec2
    color: tuple
    life: float
    size: float
    drag: float = 1.5
    shrink: float = 0.92

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            return False
        self.pos += self.vel * dt
        self.vel *= 1.0 / (1.0 + self.drag * dt)
        self.size *= self.shrink ** (dt * 60)
        return self.size > 0.2

    def draw(self, fx):
        if self.life <= 0:
            return
        alpha = 255 * min(1.0, self.life * 2.3)
        circle_fx(fx, self.color, self.pos, self.size * 2.2, alpha * 0.14)
        circle_fx(fx, self.color, self.pos, self.size, alpha)


class Bullet:
    def __init__(self, pos, vel, damage, radius, color, friendly=True, life=1.2):
        self.pos = Vec2(pos)
        self.prev = Vec2(pos)
        self.vel = Vec2(vel)
        self.damage = damage
        self.radius = radius
        self.color = color
        self.friendly = friendly
        self.life = life

    def update(self, dt):
        self.life -= dt
        self.prev = Vec2(self.pos)
        self.pos += self.vel * dt
        if self.life <= 0:
            return False
        if self.pos.x < -60 or self.pos.x > WIDTH + 60 or self.pos.y < -60 or self.pos.y > HEIGHT + 60:
            return False
        return True

    def draw(self, surf, fx):
        trail_len = 10 if self.friendly else 7
        if self.vel.length_squared() > 0:
            back = self.pos - self.vel.normalize() * trail_len
        else:
            back = self.pos
        pygame.draw.line(surf, self.color, self.pos, back, 2 if self.friendly else 3)
        pygame.draw.circle(surf, WHITE if self.friendly else ORANGE, self.pos, self.radius)
        circle_fx(fx, self.color, self.pos, self.radius * 4.0, 38)


class Pickup:
    def __init__(self, pos, kind="heal"):
        self.pos = Vec2(pos)
        self.vel = Vec2(random.uniform(-40, 40), random.uniform(-40, 40))
        self.kind = kind
        self.radius = 12
        self.life = 9.0
        self.bob = random.random() * math.tau

    def update(self, dt):
        self.life -= dt
        self.bob += dt * 4.0
        self.pos += self.vel * dt
        self.vel *= 1 / (1 + 2.4 * dt)
        return self.life > 0

    def draw(self, surf, fx):
        yoff = math.sin(self.bob) * 3
        pos = Vec2(self.pos.x, self.pos.y + yoff)
        color = GREEN if self.kind == "heal" else YELLOW
        circle_fx(fx, color, pos, 22, 35)
        pygame.draw.circle(surf, color, pos, self.radius, 2)
        pygame.draw.line(surf, color, (pos.x - 6, pos.y), (pos.x + 6, pos.y), 2)
        pygame.draw.line(surf, color, (pos.x, pos.y - 6), (pos.x, pos.y + 6), 2)


class Player:
    def __init__(self):
        self.pos = Vec2(WIDTH * 0.5, HEIGHT * 0.65)
        self.vel = Vec2(0, 0)
        self.radius = 16
        self.angle = -math.pi / 2
        self.hp = 5
        self.max_hp = 5
        self.fire_timer = 0.0
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.invuln = 1.1
        self.alive = True
        self.engine_timer = 0.0
        self.weapon_level = 1
        self.flash = 0.0

    def update(self, game, dt):
        keys = pygame.key.get_pressed()
        move = Vec2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if move.length_squared() > 0:
            move = move.normalize()

        accel = 1450
        top_speed = 340
        if self.dash_timer > 0:
            top_speed = 560

        self.vel += move * accel * dt
        self.vel *= 1 / (1 + 4.2 * dt)
        if self.vel.length() > top_speed:
            self.vel.scale_to_length(top_speed)
        self.pos += self.vel * dt

        pad = 18
        if self.pos.x < pad:
            self.pos.x = pad
            self.vel.x *= -0.3
        if self.pos.x > WIDTH - pad:
            self.pos.x = WIDTH - pad
            self.vel.x *= -0.3
        if self.pos.y < pad:
            self.pos.y = pad
            self.vel.y *= -0.3
        if self.pos.y > HEIGHT - pad:
            self.pos.y = HEIGHT - pad
            self.vel.y *= -0.3

        mouse = Vec2(pygame.mouse.get_pos())
        aim = mouse - self.pos
        if aim.length_squared() < 16:
            if self.vel.length_squared() > 20:
                aim = self.vel
            else:
                aim = Vec2(0, -1)
        self.angle = angle_to(aim)

        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt * 5)

        shooting = pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]
        if shooting and self.fire_timer <= 0:
            self.fire(game)

        dash_pressed = any(
            event.type == pygame.KEYDOWN and event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT)
            for event in game.frame_events
        )
        if dash_pressed and self.dash_cooldown <= 0 and move.length_squared() > 0:
            self.vel += move * 420
            self.dash_timer = 0.18
            self.dash_cooldown = 1.15
            self.invuln = max(self.invuln, 0.28)
            game.shake += 8
            burst_particles(game, self.pos, CYAN, 14, speed_range=(120, 340), size_range=(2, 5))

        self.engine_timer -= dt
        if self.engine_timer <= 0 and (move.length_squared() > 0 or self.vel.length_squared() > 250):
            self.engine_timer = 0.03
            rear = self.pos - from_angle(self.angle) * 14
            spread = from_angle(self.angle + math.pi + random.uniform(-0.35, 0.35)) * random.uniform(60, 140)
            game.particles.append(
                Particle(rear, spread + self.vel * 0.25, CYAN, 0.45, random.uniform(2.5, 4.2), drag=2.0)
            )

    def fire(self, game):
        self.fire_timer = 0.12
        forward = from_angle(self.angle)
        right = Vec2(-forward.y, forward.x)
        muzzle = self.pos + forward * 18
        spread = 0.04

        if self.weapon_level == 1:
            dirs = [self.angle + random.uniform(-spread, spread)]
            offsets = [0]
        elif self.weapon_level == 2:
            dirs = [
                self.angle - 0.08 + random.uniform(-spread, spread),
                self.angle + 0.08 + random.uniform(-spread, spread),
            ]
            offsets = [-6, 6]
        else:
            dirs = [
                self.angle - 0.12 + random.uniform(-spread, spread),
                self.angle + random.uniform(-spread, spread),
                self.angle + 0.12 + random.uniform(-spread, spread),
            ]
            offsets = [-7, 0, 7]

        for ang, off in zip(dirs, offsets):
            pos = muzzle + right * off
            vel = from_angle(ang) * 780
            game.bullets.append(Bullet(pos, vel, 24, 4, CYAN, friendly=True, life=1.05))

        self.flash = 0.8
        game.shake += 1.6
        burst_particles(game, muzzle, CYAN, 4, speed_range=(40, 100), size_range=(1.2, 2.5), life_range=(0.14, 0.25))

    def hit(self, game, damage=1):
        if self.invuln > 0:
            return
        self.hp -= damage
        self.invuln = 0.9
        self.flash = 1.0
        game.shake += 12
        burst_particles(game, self.pos, RED, 20, speed_range=(80, 260), size_range=(2, 5), life_range=(0.25, 0.6))
        if self.hp <= 0:
            self.alive = False
            game.trigger_game_over()

    def draw(self, surf, fx):
        blink = self.invuln > 0 and int(self.invuln * 18) % 2 == 0
        if blink:
            return

        forward = from_angle(self.angle)
        right = Vec2(-forward.y, forward.x)
        p1 = self.pos + forward * 20
        p2 = self.pos - forward * 12 + right * 12
        p3 = self.pos - forward * 8
        p4 = self.pos - forward * 12 - right * 12
        wing_l = self.pos - forward * 3 + right * 18
        wing_r = self.pos - forward * 3 - right * 18

        circle_fx(fx, CYAN, self.pos, 28 + self.flash * 10, 18 + self.flash * 55)
        pygame.draw.polygon(surf, (180, 235, 255), [p1, p2, p3, p4])
        pygame.draw.polygon(surf, CYAN2, [p2, wing_l, p3])
        pygame.draw.polygon(surf, CYAN2, [p3, wing_r, p4])
        pygame.draw.polygon(
            surf,
            (26, 40, 78),
            [self.pos + forward * 5, p2 * 0.55 + self.pos * 0.45, p4 * 0.55 + self.pos * 0.45],
        )
        if self.invuln > 0:
            circle_fx(fx, CYAN, self.pos, 30, 44)
            pygame.draw.circle(surf, CYAN, self.pos, 24, 1)


class Enemy:
    def __init__(self, kind, pos, level=1):
        self.kind = kind
        self.pos = Vec2(pos)
        self.vel = Vec2(0, 0)
        self.angle = 0.0
        self.hit_flash = 0.0
        self.shoot_timer = random.uniform(0.5, 1.4)
        self.charge_timer = random.uniform(1.0, 2.0)
        self.radius = 14
        self.hp = 30
        self.max_hp = 30
        self.speed = 110
        self.score_value = 100
        self.color = MAGENTA
        self.contact_damage = 1
        self.level = level

        if kind == "scout":
            self.radius = 13
            self.hp = self.max_hp = 30 + level * 3
            self.speed = 135 + level * 6
            self.score_value = 100
            self.color = MAGENTA
        elif kind == "brute":
            self.radius = 24
            self.hp = self.max_hp = 100 + level * 8
            self.speed = 74 + level * 3
            self.score_value = 240
            self.color = VIOLET
        elif kind == "spitter":
            self.radius = 17
            self.hp = self.max_hp = 46 + level * 5
            self.speed = 110 + level * 5
            self.score_value = 180
            self.color = ORANGE

    def update(self, game, dt):
        player = game.player
        to_player = player.pos - self.pos
        dist = max(1.0, to_player.length())

        if self.kind == "scout":
            desired = to_player.normalize() * self.speed
            self.vel += (desired - self.vel) * min(1.0, dt * 3.5)

        elif self.kind == "brute":
            self.charge_timer -= dt
            desired = to_player.normalize() * self.speed
            if self.charge_timer <= 0:
                self.charge_timer = random.uniform(1.25, 2.1)
                self.vel += to_player.normalize() * (190 + self.level * 8)
                game.particles.append(Particle(Vec2(self.pos), Vec2(), self.color, 0.35, 8, drag=8))
            self.vel += (desired - self.vel) * min(1.0, dt * 1.6)

        elif self.kind == "spitter":
            preferred = 290
            if dist < preferred - 30:
                desired = -to_player.normalize() * self.speed
            elif dist > preferred + 45:
                desired = to_player.normalize() * self.speed
            else:
                side = Vec2(-to_player.y, to_player.x).normalize() * self.speed * 0.7
                desired = side
            self.vel += (desired - self.vel) * min(1.0, dt * 2.4)
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self.shoot_timer = max(0.65, 1.45 - self.level * 0.04) * random.uniform(0.9, 1.15)
                lead = player.pos + player.vel * 0.18
                fire_dir = lead - self.pos
                if fire_dir.length_squared() > 0:
                    vel = fire_dir.normalize() * (240 + self.level * 8)
                    game.enemy_bullets.append(
                        Bullet(self.pos + fire_dir.normalize() * 12, vel, 1, 5, ORANGE, friendly=False, life=3.4)
                    )
                    burst_particles(
                        game,
                        self.pos + fire_dir.normalize() * 14,
                        ORANGE,
                        6,
                        speed_range=(30, 110),
                        size_range=(1.4, 3.0),
                        life_range=(0.15, 0.28),
                    )

        self.vel *= 1 / (1 + 1.1 * dt)
        self.pos += self.vel * dt
        self.angle = angle_to(self.vel) if self.vel.length_squared() > 5 else angle_to(to_player)
        self.hit_flash = max(0.0, self.hit_flash - dt * 4.0)

        if self.pos.x < -70:
            self.pos.x = -70
            self.vel.x *= -0.4
        if self.pos.x > WIDTH + 70:
            self.pos.x = WIDTH + 70
            self.vel.x *= -0.4
        if self.pos.y < -70:
            self.pos.y = -70
            self.vel.y *= -0.4
        if self.pos.y > HEIGHT + 70:
            self.pos.y = HEIGHT + 70
            self.vel.y *= -0.4

    def damage(self, game, amount, impulse):
        self.hp -= amount
        self.vel += impulse
        self.hit_flash = 1.0
        burst_particles(game, self.pos, self.color, 6, speed_range=(20, 100), size_range=(1.6, 3.2), life_range=(0.12, 0.3))
        if self.hp <= 0:
            game.score += self.score_value
            game.kills += 1
            game.shake += 6 if self.kind != "brute" else 10
            burst_particles(
                game,
                self.pos,
                self.color,
                22 if self.kind == "brute" else 14,
                speed_range=(70, 260),
                size_range=(1.8, 5.2),
                life_range=(0.25, 0.75),
            )
            if self.kind in ("brute", "spitter") and random.random() < 0.18:
                game.pickups.append(Pickup(self.pos, "heal"))
            return True
        return False

    def draw(self, surf, fx):
        color = tuple(min(255, int(c + self.hit_flash * 100)) for c in self.color)
        circle_fx(fx, self.color, self.pos, self.radius * 2.2, 24)

        if self.kind == "scout":
            f = from_angle(self.angle)
            r = Vec2(-f.y, f.x)
            pts = [
                self.pos + f * 16,
                self.pos - f * 8 + r * 10,
                self.pos - f * 4,
                self.pos - f * 8 - r * 10,
            ]
            pygame.draw.polygon(surf, color, pts)
            pygame.draw.circle(surf, (30, 12, 45), self.pos, 5)

        elif self.kind == "brute":
            pygame.draw.circle(surf, color, self.pos, self.radius)
            pygame.draw.circle(surf, (40, 22, 65), self.pos, self.radius - 7)
            f = from_angle(self.angle)
            pygame.draw.line(surf, WHITE, self.pos, self.pos + f * 14, 3)
            pygame.draw.circle(surf, WHITE, self.pos + f * 15, 4)

        elif self.kind == "spitter":
            f = from_angle(self.angle)
            r = Vec2(-f.y, f.x)
            body = [
                self.pos + f * 14,
                self.pos + r * 13,
                self.pos - f * 10,
                self.pos - r * 13,
            ]
            pygame.draw.polygon(surf, color, body)
            pygame.draw.circle(surf, (70, 22, 10), self.pos, 5)

        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 0.99:
            rect = pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius - 11, self.radius * 2, 4)
            pygame.draw.rect(surf, (20, 24, 40), rect, border_radius=2)
            fill = rect.copy()
            fill.width = max(1, int(fill.width * hp_ratio))
            pygame.draw.rect(surf, self.color, fill, border_radius=2)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        self.fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font_medium = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_large = pygame.font.SysFont("consolas", 46, bold=True)
        self.frame_events = []
        self.shake = 0.0
        self.running = True
        self.background = self.build_background()
        self.reset()

    def build_background(self):
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(BG)

        neb = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(18):
            color = random.choice([CYAN2, VIOLET, MAGENTA, (70, 120, 255)])
            radius = random.randint(70, 180)
            alpha = random.randint(10, 30)
            pos = (random.randint(0, WIDTH), random.randint(0, HEIGHT))
            pygame.draw.circle(neb, (*color, alpha), pos, radius)
        surf.blit(neb, (0, 0))

        for _ in range(160):
            x = random.randrange(WIDTH)
            y = random.randrange(HEIGHT)
            c = random.choice([(255, 255, 255), (160, 220, 255), (255, 220, 255)])
            surf.set_at((x, y), c)
            if random.random() < 0.08 and x + 1 < WIDTH and y + 1 < HEIGHT:
                surf.set_at((x + 1, y), c)
                surf.set_at((x, y + 1), c)
        return surf

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.particles = []
        self.pickups = []
        self.score = 0
        self.kills = 0
        self.time_alive = 0.0
        self.spawn_timer = 0.4
        self.wave = 1
        self.wave_flash = 2.0
        self.intro_timer = 7.0
        self.game_over = False
        self.final_time = 0.0
        self.shake = 0.0

    def trigger_game_over(self):
        if self.game_over:
            return
        self.game_over = True
        self.final_time = self.time_alive
        burst_particles(self, self.player.pos, CYAN, 28, speed_range=(60, 260), size_range=(2, 6), life_range=(0.3, 1.0))
        burst_particles(self, self.player.pos, RED, 32, speed_range=(80, 300), size_range=(2, 6), life_range=(0.3, 0.9))

    def spawn_enemy(self):
        edge = random.randint(0, 3)
        margin = 60
        if edge == 0:
            pos = Vec2(random.uniform(0, WIDTH), -margin)
        elif edge == 1:
            pos = Vec2(WIDTH + margin, random.uniform(0, HEIGHT))
        elif edge == 2:
            pos = Vec2(random.uniform(0, WIDTH), HEIGHT + margin)
        else:
            pos = Vec2(-margin, random.uniform(0, HEIGHT))

        weights = [("scout", 1.0)]
        if self.wave >= 2:
            weights.append(("spitter", 0.55 + self.wave * 0.03))
        if self.wave >= 3:
            weights.append(("brute", 0.35 + self.wave * 0.025))

        total = sum(w for _, w in weights)
        pick = random.uniform(0, total)
        acc = 0.0
        kind = "scout"
        for k, w in weights:
            acc += w
            if pick <= acc:
                kind = k
                break

        self.enemies.append(Enemy(kind, pos, self.wave))

    def handle_collisions(self):
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if bullet.pos.distance_to(enemy.pos) <= bullet.radius + enemy.radius:
                    impulse = bullet.vel.normalize() * 42 if bullet.vel.length_squared() > 0 else Vec2()
                    if enemy.damage(self, bullet.damage, impulse):
                        self.enemies.remove(enemy)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

        for bullet in self.enemy_bullets[:]:
            if bullet.pos.distance_to(self.player.pos) <= bullet.radius + self.player.radius:
                if bullet in self.enemy_bullets:
                    self.enemy_bullets.remove(bullet)
                self.player.hit(self, bullet.damage)

        if not self.game_over:
            for enemy in self.enemies:
                if enemy.pos.distance_to(self.player.pos) <= enemy.radius + self.player.radius - 2:
                    push = self.player.pos - enemy.pos
                    if push.length_squared() > 0:
                        push.scale_to_length(220)
                        self.player.vel += push * 0.02
                    self.player.hit(self, enemy.contact_damage)
                    enemy.vel *= -0.6
                    enemy.hit_flash = 1.0

            for pickup in self.pickups[:]:
                if pickup.pos.distance_to(self.player.pos) <= pickup.radius + self.player.radius:
                    if pickup.kind == "heal" and self.player.hp < self.player.max_hp:
                        self.player.hp += 1
                    self.pickups.remove(pickup)
                    burst_particles(
                        self,
                        pickup.pos,
                        GREEN,
                        12,
                        speed_range=(40, 160),
                        size_range=(2, 4),
                        life_range=(0.2, 0.5),
                    )

    def update(self, dt):
        if not self.game_over:
            self.time_alive += dt
            new_wave = 1 + int(self.time_alive // 18)
            if new_wave != self.wave:
                self.wave = new_wave
                self.wave_flash = 2.4
                self.shake += 10
                for _ in range(2 + self.wave):
                    self.spawn_enemy()

            self.player.weapon_level = 1 + min(2, self.score // 700)
            self.player.update(self, dt)

            spawn_interval = max(0.18, 1.08 - self.wave * 0.06 - min(0.3, self.time_alive * 0.004))
            self.spawn_timer -= dt
            while self.spawn_timer <= 0:
                self.spawn_enemy()
                self.spawn_timer += spawn_interval * random.uniform(0.8, 1.15)

        self.wave_flash = max(0.0, self.wave_flash - dt)
        self.intro_timer = max(0.0, self.intro_timer - dt)
        self.shake = max(0.0, self.shake - dt * 22)

        for seq in (self.bullets, self.enemy_bullets, self.pickups, self.particles):
            for item in seq[:]:
                if not item.update(dt):
                    seq.remove(item)

        for enemy in self.enemies:
            enemy.update(self, dt)

        self.handle_collisions()

        if self.game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                self.reset()

    def draw_background(self):
        self.scene.blit(self.background, (0, 0))

        pulse = 0.55 + 0.45 * math.sin(self.time_alive * 0.8)
        for i in range(10):
            x = (i * 131 + self.time_alive * (8 + i * 1.3)) % (WIDTH + 80) - 40
            y = (i * 71 + self.time_alive * (4 + i * 0.8)) % (HEIGHT + 80) - 40
            circle_fx(self.fx, CYAN if i % 2 == 0 else VIOLET, (x, y), 16 + (i % 4) * 8, 7 * pulse)

        grid_color = (18, 24, 48)
        for x in range(0, WIDTH + 1, 80):
            pygame.draw.line(self.scene, grid_color, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT + 1, 80):
            pygame.draw.line(self.scene, grid_color, (0, y), (WIDTH, y), 1)

    def draw_hud(self):
        panel = pygame.Rect(16, 14, 315, 76)
        pygame.draw.rect(self.screen, (9, 12, 24), panel, border_radius=12)
        pygame.draw.rect(self.screen, (35, 46, 80), panel, 2, border_radius=12)
        draw_text(self.screen, f"SCORE {self.score:05d}", self.font_medium, WHITE, (30, 24))
        draw_text(self.screen, f"WAVE {self.wave}", self.font_small, CYAN, (30, 54))
        draw_text(self.screen, f"KILLS {self.kills}", self.font_small, WHITE, (130, 54))
        draw_text(self.screen, f"TIME {self.time_alive:05.1f}", self.font_small, WHITE, (220, 54))

        hp_x, hp_y = 26, HEIGHT - 36
        for i in range(self.player.max_hp):
            rect = pygame.Rect(hp_x + i * 26, hp_y, 18, 16)
            color = CYAN if i < self.player.hp else (35, 44, 72)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, (80, 100, 145), rect, 1, border_radius=4)
        draw_text(self.screen, "HULL", self.font_small, WHITE, (26, HEIGHT - 56))

        dash_rect = pygame.Rect(250, HEIGHT - 38, 160, 18)
        pygame.draw.rect(self.screen, (20, 24, 40), dash_rect, border_radius=9)
        dash_fill = dash_rect.copy()
        ratio = 1.0 - self.player.dash_cooldown / 1.15 if self.player.dash_cooldown > 0 else 1.0
        dash_fill.width = max(4, int(dash_fill.width * clamp(ratio, 0.0, 1.0)))
        pygame.draw.rect(self.screen, CYAN, dash_fill, border_radius=9)
        pygame.draw.rect(self.screen, (80, 100, 145), dash_rect, 1, border_radius=9)
        draw_text(self.screen, "DASH", self.font_small, WHITE, (250, HEIGHT - 58))

        level_names = ["SINGLE", "DOUBLE", "TRIPLE"]
        draw_text(self.screen, f"WEAPON {level_names[self.player.weapon_level - 1]}", self.font_small, YELLOW, (450, HEIGHT - 38))

        if self.intro_timer > 0:
            alpha = int(clamp(255 * min(1, self.intro_timer), 0, 255))
            box = pygame.Surface((620, 74), pygame.SRCALPHA)
            pygame.draw.rect(box, (10, 14, 28, min(220, alpha)), box.get_rect(), border_radius=16)
            pygame.draw.rect(box, (60, 90, 150, min(230, alpha)), box.get_rect(), 2, border_radius=16)
            draw_text(box, "WASD / ARROWS move   MOUSE aim   LMB or SPACE fire   SHIFT dash", self.font_small, WHITE, (310, 22), "center")
            draw_text(box, "Survive the rift, break waves, and stay aggressive.", self.font_small, CYAN, (310, 49), "center")
            self.screen.blit(box, box.get_rect(center=(WIDTH // 2, HEIGHT - 82)))

        if self.wave_flash > 0:
            text = f"WAVE {self.wave}"
            alpha = 255 * min(1.0, self.wave_flash)
            y = 120 - (1 - min(1, self.wave_flash)) * 18
            surf = self.font_large.render(text, True, WHITE)
            glow = pygame.Surface((surf.get_width() + 24, surf.get_height() + 24), pygame.SRCALPHA)
            circle_fx(glow, VIOLET, (glow.get_width() // 2, glow.get_height() // 2), max(glow.get_width(), glow.get_height()) // 2, alpha * 0.2)
            glow.blit(surf, (12, 12))
            glow.set_alpha(int(alpha))
            self.screen.blit(glow, glow.get_rect(center=(WIDTH // 2, y)))

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 6, 12, 150))
            self.screen.blit(overlay, (0, 0))

            panel = pygame.Rect(0, 0, 520, 240)
            panel.center = (WIDTH // 2, HEIGHT // 2)
            pygame.draw.rect(self.screen, (11, 16, 28), panel, border_radius=18)
            pygame.draw.rect(self.screen, RED, panel, 2, border_radius=18)

            draw_text(self.screen, "RIFT COLLAPSE", self.font_large, WHITE, (WIDTH // 2, panel.y + 52), "center")
            draw_text(
                self.screen,
                f"Score {self.score}   Kills {self.kills}   Time {self.final_time:.1f}s",
                self.font_medium,
                CYAN,
                (WIDTH // 2, panel.y + 112),
                "center",
            )
            draw_text(self.screen, "Press R to restart   •   Esc to quit", self.font_small, WHITE, (WIDTH // 2, panel.y + 165), "center")

    def draw(self):
        self.scene.fill(BG)
        self.fx.fill((0, 0, 0, 0))
        self.draw_background()

        for pickup in self.pickups:
            pickup.draw(self.scene, self.fx)
        for bullet in self.bullets:
            bullet.draw(self.scene, self.fx)
        for bullet in self.enemy_bullets:
            bullet.draw(self.scene, self.fx)
        for enemy in self.enemies:
            enemy.draw(self.scene, self.fx)
        for particle in self.particles:
            particle.draw(self.fx)
        if self.player.alive:
            self.player.draw(self.scene, self.fx)

        offset = Vec2(0, 0)
        if self.shake > 0:
            offset = Vec2(random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))

        self.screen.fill(BG2)
        self.screen.blit(self.scene, offset)
        self.screen.blit(self.fx, offset)
        self.draw_hud()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(0.033, self.clock.tick(FPS) / 1000.0)
            self.frame_events = pygame.event.get()

            for event in self.frame_events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
