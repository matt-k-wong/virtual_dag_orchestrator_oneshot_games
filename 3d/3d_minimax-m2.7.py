# game.py
""" NEON SKIES - Arcade Flight Combat
A pseudo-3D arcade shooter with neon aesthetics.
Controls: WASD/Arrows to move, SPACE to shoot, P to pause, R to restart
"""
import pygame
import random
import math
import sys
import os

# Auto-install pygame-ce if needed
try:
    import pygame_ce as pygame
except ImportError:
    try:
        import pygame
    except ImportError:
        os.system(f"{sys.executable} -m pip install pygame-ce pygame")
        import pygame_ce as pygame

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
HORIZON_Y = SCREEN_HEIGHT * 0.3

# Colors
COLORS = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'cyan': (0, 220, 255),
    'cyan_bright': (0, 255, 255),
    'cyan_dark': (0, 180, 220),
    'red': (255, 50, 50),
    'red_bright': (255, 80, 80),
    'orange': (255, 150, 50),
    'magenta': (180, 50, 180),
    'purple': (100, 0, 150),
    'purple_dark': (60, 20, 80),
    'purple_light': (80, 30, 100),
    'yellow': (255, 255, 100),
    'gray': (150, 150, 170),
    'gray_dark': (30, 10, 50),
}

class Particle:
    def __init__(self):
        self.active = False
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0
        self.life = 0
        self.max_life = 0
        self.color = (255, 255, 255)
        self.size = 5

    def spawn(self, x, y, color, vx, vy, life, size):
        self.active = True
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt):
        if not self.active:
            return
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += 0.2 * dt * 60
        self.life -= dt * 1000
        if self.life <= 0:
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        alpha = int(255 * (self.life / self.max_life))
        current_size = max(1, int(self.size * (self.life / self.max_life)))
        s = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (current_size, current_size), current_size)
        screen.blit(s, (int(self.x - current_size), int(self.y - current_size)))

class ParticlePool:
    def __init__(self, max_particles=150):
        self.particles = [Particle() for _ in range(max_particles)]

    def spawn_explosion(self, x, y, color, count=15):
        spawned = 0
        for p in self.particles:
            if not p.active and spawned < count:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed - 2
                variation = random.randint(-30, 30)
                c = (min(255, color[0] + variation), min(255, color[1] + variation), min(255, color[2] + variation))
                p.spawn(x, y, c, vx, vy, random.randint(300, 600), random.randint(4, 8))
                spawned += 1

    def spawn_trail(self, x, y, color):
        for p in self.particles:
            if not p.active:
                p.spawn(x + random.uniform(-5, 5), y + random.uniform(-5, 5), color, random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 200, 3)
                break

    def update(self, dt):
        for p in self.particles:
            p.update(dt)

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

    def reset(self):
        for p in self.particles:
            p.active = False

class ScreenEffects:
    def __init__(self):
        self.shake_timer = 0
        self.shake_intensity = 0
        self.shake_offset_x = 0
        self.shake_offset_y = 0
        self.hit_flash = 0

    def shake(self, intensity, duration_ms):
        self.shake_intensity = intensity
        self.shake_timer = duration_ms

    def update(self, dt):
        if self.shake_timer > 0:
            self.shake_timer -= dt * 1000
            self.shake_offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0
        if self.hit_flash > 0:
            self.hit_flash -= dt * 1000

    def get_offset(self):
        return self.shake_offset_x, self.shake_offset_y

    def trigger_hit_flash(self):
        self.hit_flash = 50

class SpeedLines:
    def __init__(self, max_lines=30):
        self.lines = []
        self.max_lines = max_lines

    def update(self, dt):
        for line in self.lines[:]:
            line['y'] += line['speed'] * dt * 60
            if line['y'] > SCREEN_HEIGHT:
                self.lines.remove(line)
        if len(self.lines) < self.max_lines and random.random() < 0.3:
            side = random.choice(['left', 'right'])
            x = random.randint(0, 100) if side == 'left' else random.randint(SCREEN_WIDTH - 100, SCREEN_WIDTH)
            self.lines.append({
                'x': x, 'y': HORIZON_Y,
                'length': random.randint(30, 80),
                'speed': random.uniform(8, 15)
            })

    def draw(self, screen):
        for line in self.lines:
            alpha = int(80 * (line['y'] / SCREEN_HEIGHT))
            if alpha > 10:
                s = pygame.Surface((2, line['length']), pygame.SRCALPHA)
                s.fill((255, 255, 255, alpha))
                screen.blit(s, (int(line['x']), int(line['y'])))

class Background:
    def __init__(self):
        self.grid_offset = 0
        self.grid_speed = 3
        self.horizon_y = HORIZON_Y
        self.mountain_layers = [
            self.generate_mountains(4, 0.3),
            self.generate_mountains(4, 0.5),
            self.generate_mountains(3, 0.7),
        ]

    def generate_mountains(self, count, height_factor):
        mountains = []
        for i in range(count):
            x = random.randint(0, SCREEN_WIDTH)
            width = random.randint(150, 400)
            height = int(100 * height_factor)
            mountains.append({'x': x, 'width': width, 'height': height})
        return mountains

    def update(self, dt):
        self.grid_offset = (self.grid_offset + self.grid_speed * dt * 60) % 50

    def draw(self, screen):
        screen.fill(COLORS['black'])
        # Draw grid
        for i in range(0, 25):
            x_offset = (i * 50 - self.grid_offset) % (SCREEN_WIDTH + 200) - 100
            alpha = int(100 + (i / 25) * 100)
            end_x = x_offset
            for j in range(int(SCREEN_HEIGHT - self.horizon_y) // 30 + 1):
                y = self.horizon_y + j * 30
                if 0 <= end_x <= SCREEN_WIDTH:
                    pygame.draw.line(screen, (*COLORS['purple'], alpha), (end_x, y), (end_x + 5, y + 10), 1)
        # Horizontal grid lines
        for i in range(1, 10):
            y = self.horizon_y + (i / 10) * (SCREEN_HEIGHT - self.horizon_y)
            alpha = int(50 + (i / 10) * 100)
            pygame.draw.line(screen, (*COLORS['purple'], alpha), (0, int(y)), (SCREEN_WIDTH, int(y)), 1)
        # Draw mountains
        colors = [COLORS['gray_dark'], COLORS['purple_dark'], COLORS['purple_light']]
        scroll_offsets = [0.5, 1.0, 1.5]
        for layer_idx, (layer, color, scroll) in enumerate(zip(self.mountain_layers, colors, scroll_offsets)):
            for m in layer:
                x = int(((m['x'] + self.grid_offset * scroll) % (SCREEN_WIDTH + 400)) - 100)
                base_y = self.horizon_y + layer_idx * 30
                points = [(x, base_y), (x + m['width'] // 2, base_y - m['height']), (x + m['width'], base_y)]
                pygame.draw.polygon(screen, color, points)

class Projectile:
    def __init__(self):
        self.active = False
        self.x = 0
        self.y = 0
        self.z = 0.5
        self.speed = 0.015

    def spawn(self, x, y):
        self.active = True
        self.x = x
        self.y = y - 25
        self.z = 0.5

    def update(self, dt):
        if not self.active:
            return
        self.z += self.speed * dt * 60
        if self.z >= 1.0:
            self.active = False

    def get_screen_pos(self):
        screen_y = HORIZON_Y + (self.z ** 0.7) * (SCREEN_HEIGHT - HORIZON_Y)
        screen_x = self.x
        scale = 0.2 + (self.z ** 0.8) * 0.8
        return screen_x, screen_y, scale

    def draw(self, screen):
        if not self.active:
            return
        sx, sy, scale = self.get_screen_pos()
        size = max(2, int(4 * scale))
        pygame.draw.circle(screen, COLORS['yellow'], (int(sx), int(sy)), size)
        pygame.draw.circle(screen, COLORS['white'], (int(sx), int(sy)), max(1, size // 2))

    def get_rect(self):
        sx, sy, scale = self.get_screen_pos()
        size = max(4, int(8 * scale))
        return pygame.Rect(int(sx - size / 2), int(sy - size / 2), size, size)

    def reset(self):
        self.active = False

class ProjectilePool:
    def __init__(self, size=50):
        self.projectiles = [Projectile() for _ in range(size)]

    def fire(self, x, y):
        for p in self.projectiles:
            if not p.active:
                p.spawn(x, y)
                return True
        return False

    def update(self, dt):
        for p in self.projectiles:
            p.update(dt)

    def draw(self, screen):
        for p in self.projectiles:
            p.draw(screen)

    def check_collision(self, enemy_rect):
        for p in self.projectiles:
            if p.active and p.get_rect().colliderect(enemy_rect):
                p.active = False
                return True
        return False

    def reset(self):
        for p in self.projectiles:
            p.reset()

class Enemy:
    def __init__(self):
        self.active = False
        self.x = 0
        self.y = 0
        self.z = 0.01
        self.speed = 0.008
        self.health = 1
        self.max_health = 1
        self.points = 10
        self.color = COLORS['red']
        self.base_size = 30

    def spawn(self, x, z=0.01, speed=0.008, health=1, points=10, color=COLORS['red'], base_size=30):
        self.active = True
        self.x = x
        self.y = SCREEN_HEIGHT // 2 - 50
        self.z = z
        self.speed = speed
        self.health = health
        self.max_health = health
        self.points = points
        self.color = color
        self.base_size = base_size

    def update(self, dt, player_x=0, player_y=0, tracking=0):
        if not self.active:
            return
        self.z += self.speed * dt * 60
        if self.z >= 0.95:
            self.active = False
        if tracking > 0 and self.z > 0.1:
            dx = player_x - self.x
            self.x += dx * tracking * dt * 60

    def get_screen_pos(self):
        screen_y = HORIZON_Y + (self.z ** 0.7) * (SCREEN_HEIGHT - HORIZON_Y)
        center_x = SCREEN_WIDTH // 2
        screen_x = center_x + (self.x - center_x) * (0.1 + self.z * 0.9)
        scale = 0.2 + (self.z ** 0.8) * 0.8
        return screen_x, screen_y, scale

    def draw(self, screen):
        if not self.active:
            return
        sx, sy, scale = self.get_screen_pos()
        size = max(4, int(self.base_size * scale))
        # Draw glow
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 50), (size * 2, size * 2), int(size * 1.5))
        screen.blit(glow_surf, (int(sx - size * 2), int(sy - size * 2)))
        # Draw enemy shape (triangle pointing down toward player)
        points = [
            (int(sx), int(sy + size)),
            (int(sx - size * 0.7), int(sy - size * 0.5)),
            (int(sx + size * 0.7), int(sy - size * 0.5))
        ]
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, COLORS['white'], points, 1)

    def get_rect(self):
        sx, sy, scale = self.get_screen_pos()
        size = max(8, int(self.base_size * scale))
        return pygame.Rect(int(sx - size / 2), int(sy - size / 2), size, size)

    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            self.active = False
            return True
        return False

class Seeker(Enemy):
    def __init__(self):
        super().__init__()
        self.tracking_strength = 0.3
        self.color = COLORS['orange']
        self.points = 25
        self.speed = 0.006
        self.base_size = 25

    def draw(self, screen):
        if not self.active:
            return
        sx, sy, scale = self.get_screen_pos()
        size = max(4, int(self.base_size * scale))
        # Glow
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 50), (size * 2, size * 2), int(size * 1.5))
        screen.blit(glow_surf, (int(sx - size * 2), int(sy - size * 2)))
        # Diamond shape
        points = [
            (int(sx), int(sy - size)),
            (int(sx - size * 0.7), int(sy)),
            (int(sx), int(sy + size)),
            (int(sx + size * 0.7), int(sy))
        ]
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, COLORS['white'], points, 1)

    def update(self, dt, player_x, player_y, tracking=0):
        super().update(dt, player_x, player_y, self.tracking_strength)

class Heavy(Enemy):
    def __init__(self):
        super().__init__()
        self.color = COLORS['magenta']
        self.health = 3
        self.max_health = 3
        self.points = 50
        self.speed = 0.004
        self.base_size = 50

    def draw(self, screen):
        if not self.active:
            return
        sx, sy, scale = self.get_screen_pos()
        size = max(6, int(self.base_size * scale))
        # Glow
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60), (size * 2, size * 2), int(size * 1.5))
        screen.blit(glow_surf, (int(sx - size * 2), int(sy - size * 2)))
        # Hexagon shape
        points = []
        for i in range(6):
            angle = math.pi / 2 + i * math.pi / 3
            points.append((int(sx + math.cos(angle) * size), int(sy + math.sin(angle) * size)))
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, COLORS['white'], points, 2)
        # Health indicator
        if self.health < self.max_health:
            for i in range(self.health):
                pygame.draw.circle(screen, COLORS['red'], (int(sx - 10 + i * 10), int(sy)), 3)

class Asteroid(Enemy):
    def __init__(self):
        super().__init__()
        self.color = COLORS['gray']
        self.points = 15
        self.speed = 0.01
        self.base_size = 35
        self.rotation = 0
        self.rotation_speed = random.uniform(-2, 2)
        self.vertices = [(random.uniform(0.5, 1.0), random.uniform(0, math.pi * 2)) for _ in range(7)]

    def update(self, dt, player_x=0, player_y=0, tracking=0):
        super().update(dt, player_x, player_y, tracking)
        self.rotation += self.rotation_speed * dt * 60

    def draw(self, screen):
        if not self.active:
            return
        sx, sy, scale = self.get_screen_pos()
        size = max(4, int(self.base_size * scale))
        # Glow
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 40), (size * 2, size * 2), int(size * 1.2))
        screen.blit(glow_surf, (int(sx - size * 2), int(sy - size * 2)))
        # Irregular polygon
        points = []
        for v_scale, v_angle in self.vertices:
            angle = v_angle + self.rotation
            px = sx + math.cos(angle) * size * v_scale
            py = sy + math.sin(angle) * size * v_scale
            points.append((int(px), int(py)))
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, COLORS['white'], points, 1)

class EnemyManager:
    def __init__(self):
        self.enemies = []
        self.wave_number = 1
        self.spawn_timer = 0
        self.spawn_delay = 2000
        self.enemies_spawned = 0
        self.enemies_per_wave = 5
        self.difficulty = 1.0
        self.wave_complete = False

    def spawn_enemy(self, enemy_type='drone'):
        enemy_pool = self.enemies + []
        for e in enemy_pool:
            if not e.active:
                if enemy_type == 'drone':
                    x = random.randint(200, SCREEN_WIDTH - 200)
                    e.spawn(x, z=0.01, speed=0.006 * self.difficulty, health=1, points=10, color=COLORS['red'], base_size=30)
                elif enemy_type == 'seeker':
                    x = random.randint(300, SCREEN_WIDTH - 300)
                    e.spawn(x, z=0.01, speed=0.005 * self.difficulty, health=1, points=25, color=COLORS['orange'], base_size=25)
                elif enemy_type == 'heavy':
                    x = random.randint(400, SCREEN_WIDTH - 400)
                    e.spawn(x, z=0.01, speed=0.003 * self.difficulty, health=3, points=50, color=COLORS['magenta'], base_size=50)
                elif enemy_type == 'asteroid':
                    x = random.randint(200, SCREEN_WIDTH - 200)
                    e.spawn(x, z=0.01, speed=0.008 * self.difficulty, health=1, points=15, color=COLORS['gray'], base_size=35)
                return True
        # Create new enemy if pool exhausted
        if enemy_type == 'drone':
            e = Enemy()
            x = random.randint(200, SCREEN_WIDTH - 200)
            e.spawn(x, z=0.01, speed=0.006 * self.difficulty, health=1, points=10, color=COLORS['red'], base_size=30)
        elif enemy_type == 'seeker':
            e = Seeker()
            x = random.randint(300, SCREEN_WIDTH - 300)
            e.spawn(x, z=0.01, speed=0.005 * self.difficulty, health=1, points=25, color=COLORS['orange'], base_size=25)
        elif enemy_type == 'heavy':
            e = Heavy()
            x = random.randint(400, SCREEN_WIDTH - 400)
            e.spawn(x, z=0.01, speed=0.003 * self.difficulty, health=3, points=50, color=COLORS['magenta'], base_size=50)
        elif enemy_type == 'asteroid':
            e = Asteroid()
            x = random.randint(200, SCREEN_WIDTH - 200)
            e.spawn(x, z=0.01, speed=0.008 * self.difficulty, health=1, points=15, color=COLORS['gray'], base_size=35)
        self.enemies.append(e)
        return True

    def update(self, dt, player_x, player_y):
        # Spawn logic
        self.spawn_timer -= dt * 1000
        if self.spawn_timer <= 0 and self.enemies_spawned < self.enemies_per_wave:
            roll = random.random()
            if self.wave_number <= 3:
                self.spawn_enemy('drone')
            elif self.wave_number <= 6:
                if roll < 0.7:
                    self.spawn_enemy('drone')
                else:
                    self.spawn_enemy('seeker')
            else:
                if roll < 0.5:
                    self.spawn_enemy('drone')
                elif roll < 0.8:
                    self.spawn_enemy('seeker')
                elif roll < 0.95:
                    self.spawn_enemy('heavy')
                else:
                    self.spawn_enemy('asteroid')
            self.enemies_spawned += 1
            self.spawn_timer = self.spawn_delay
        # Update all enemies
        for e in self.enemies:
            if isinstance(e, Seeker):
                e.update(dt, player_x, player_y)
            elif isinstance(e, Heavy):
                e.update(dt, player_x, player_y)
            elif isinstance(e, Asteroid):
                e.update(dt, player_x, player_y)
            else:
                e.update(dt, player_x, player_y)
        # Check wave complete
        active_count = sum(1 for e in self.enemies if e.active)
        if self.enemies_spawned >= self.enemies_per_wave and active_count == 0:
            self.wave_complete = True

    def advance_wave(self):
        self.wave_number += 1
        self.enemies_per_wave = min(15, self.enemies_per_wave + 2)
        self.spawn_delay = max(500, self.spawn_delay - 100)
        self.difficulty += 0.1
        self.enemies_spawned = 0
        self.wave_complete = False
        self.spawn_timer = 1000

    def draw(self, screen):
        # Sort by z for proper depth ordering (far to near)
        sorted_enemies = sorted([e for e in self.enemies if e.active], key=lambda e: e.z)
        for e in sorted_enemies:
            e.draw(screen)

    def check_player_collision(self, player_rect):
        for e in self.enemies:
            if e.active and e.get_rect().colliderect(player_rect):
                return e
        return None

    def check_projectile_collision(self, projectile_rect):
        for e in self.enemies:
            if e.active and e.get_rect().colliderect(projectile_rect):
                return e
        return None

    def reset(self):
        for e in self.enemies:
            e.active = False
        self.wave_number = 1
        self.enemies_per_wave = 5
        self.spawn_delay = 2000
        self.difficulty = 1.0
        self.enemies_spawned = 0
        self.wave_complete = False
        self.spawn_timer = 1000

class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 100
        self.width = 40
        self.height = 50
        self.speed = 5.5
        self.health = 3
        self.max_health = 3
        self.shoot_cooldown = 0
        self.shoot_delay = 150
        self.invincible = False
        self.invincible_timer = 0
        self.invincible_duration = 1500
        self.trail = []
        self.max_trail = 15
        self.vx = 0
        self.vy = 0
        self.inertia = 0.85
        self.flash_timer = 0

    def update(self, dt, keys):
        # Handle input
        target_vx = 0
        target_vy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            target_vx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            target_vx = self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            target_vy = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            target_vy = self.speed
        # Apply inertia
        self.vx = self.vx * self.inertia + target_vx * (1 - self.inertia)
        self.vy = self.vy * self.inertia + target_vy * (1 - self.inertia)
        # Move
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        # Clamp position
        self.x = max(20, min(SCREEN_WIDTH - 20, self.x))
        self.y = max(SCREEN_HEIGHT // 2, min(SCREEN_HEIGHT - 30, self.y))
        # Update trail
        self.trail.insert(0, (self.x, self.y))
        if len(self.trail) > self.max_trail:
            self.trail.pop()
        # Update cooldowns
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt * 1000
        if self.invincible:
            self.invincible_timer -= dt * 1000
            self.flash_timer += dt * 1000
            if self.invincible_timer <= 0:
                self.invincible = False
                self.flash_timer = 0

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = self.shoot_delay
            return True
        return False

    def take_damage(self):
        if not self.invincible:
            self.health -= 1
            self.invincible = True
            self.invincible_timer = self.invincible_duration
            self.flash_timer = 0
            return True
        return False

    def draw(self, screen):
        # Draw trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(150 * (1 - i / self.max_trail))
            size = max(2, int(8 * (1 - i / self.max_trail)))
            if alpha > 0:
                s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*COLORS['cyan'], alpha), (size, size), size)
                screen.blit(s, (int(tx - size), int(ty - size)))
        # Draw ship
        if self.invincible and (self.flash_timer // 100) % 2 == 0:
            return  # Flash effect
        # Glow
        glow_surf = pygame.Surface((self.width * 2 + 20, self.height * 2 + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (*COLORS['cyan_bright'], 40), (10, 10, self.width * 2, self.height * 2))
        screen.blit(glow_surf, (int(self.x - self.width - 10), int(self.y - self.height // 2 - 10)))
        # Ship body (triangle)
        points = [
            (int(self.x), int(self.y - self.height // 2)),
            (int(self.x - self.width // 2), int(self.y + self.height // 2)),
            (int(self.x + self.width // 2), int(self.y + self.height // 2))
        ]
        pygame.draw.polygon(screen, COLORS['cyan'], points)
        pygame.draw.polygon(screen, COLORS['cyan_bright'], points, 2)
        # Engine glow
        engine_size = 8 + int(4 * abs(math.sin(pygame.time.get_ticks() / 100)))
        pygame.draw.circle(screen, COLORS['orange'], (int(self.x), int(self.y + self.height // 2 - 5)), engine_size)
        pygame.draw.circle(screen, COLORS['yellow'], (int(self.x), int(self.y + self.height // 2 - 5)), engine_size // 2)

    def get_rect(self):
        return pygame.Rect(int(self.x - self.width // 2), int(self.y - self.height // 2), self.width, self.height)

    def reset(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 100
        self.health = 3
        self.shoot_cooldown = 0
        self.invincible = False
        self.invincible_timer = 0
        self.flash_timer = 0
        self.vx = 0
        self.vy = 0
        self.trail = []

class ScoreManager:
    def __init__(self):
        self.score = 0
        self.multiplier = 1.0
        self.kill_streak = 0
        self.high_score = 0

    def add_kill(self, points):
        self.kill_streak += 1
        self.multiplier = min(4.0, 1.0 + (self.kill_streak // 5) * 0.5)
        self.score += int(points * self.multiplier)

    def take_damage(self):
        self.kill_streak = 0
        self.multiplier = 1.0

    def reset(self):
        if self.score > self.high_score:
            self.high_score = self.score
        self.score = 0
        self.multiplier = 1.0
        self.kill_streak = 0

    def reset_all(self):
        if self.score > self.high_score:
            self.high_score = self.score
        self.score = 0
        self.multiplier = 1.0
        self.kill_streak = 0
        self.high_score = 0

class HUD:
    def __init__(self):
        try:
            self.font_large = pygame.font.Font(None, 64)
            self.font_medium = pygame.font.Font(None, 48)
            self.font_small = pygame.font.Font(None, 28)
        except:
            self.font_large = pygame.font.SysFont('arial', 48)
            self.font_medium = pygame.font.SysFont('arial', 36)
            self.font_small = pygame.font.SysFont('arial', 20)
        self.score_popups = []

    def add_score_popup(self, points, x, y, multiplier=1.0):
        text = f"+{int(points * multiplier)}"
        color = COLORS['yellow'] if multiplier >= 2 else COLORS['white']
        self.score_popups.append({
            'text': text,
            'x': x,
            'y': y,
            'life': 800,
            'color': color
        })

    def update(self, dt):
        for popup in self.score_popups[:]:
            popup['y'] -= 1 * dt * 60
            popup['life'] -= dt * 1000
            if popup['life'] <= 0:
                self.score_popups.remove(popup)

    def draw_health(self, screen, health, max_health):
        for i in range(max_health):
            x = 30 + i * 45
            y = 30
            if i < health:
                # Filled ship icon
                points = [(x, y), (x - 12, y + 25), (x + 12, y + 25)]
                pygame.draw.polygon(screen, COLORS['cyan'], points)
            else:
                # Empty outline
                points = [(x, y), (x - 12, y + 25), (x + 12, y + 25)]
                pygame.draw.polygon(screen, (80, 80, 80), points, 2)

    def draw_score(self, screen, score, multiplier):
        score_text = self.font_large.render(f"{score}", True, COLORS['cyan'])
        screen.blit(score_text, (SCREEN_WIDTH - score_text.get_width() - 30, 20))
        if multiplier > 1.0:
            mult_text = self.font_medium.render(f"x{multiplier:.1f}", True, COLORS['yellow'])
            screen.blit(mult_text, (SCREEN_WIDTH - mult_text.get_width() - 30, 80))

    def draw_wave(self, screen, wave):
        text = self.font_medium.render(f"WAVE {wave}", True, COLORS['white'])
        screen.blit(text, ((SCREEN_WIDTH - text.get_width()) // 2, 20))

    def draw_score_popups(self, screen):
        for popup in self.score_popups:
            alpha = int(255 * (popup['life'] / 800))
            text = self.font_small.render(popup['text'], True, popup['color'])
            s = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            s.fill((0, 0, 0, 0))
            s.blit(text, (0, 0))
            s.set_alpha(alpha)
            screen.blit(s, (int(popup['x']), int(popup['y'])))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("NEON SKIES")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 'playing'
        
        self.background = Background()
        self.player = Player()
        self.enemy_manager = EnemyManager()
        self.projectile_pool = ProjectilePool(50)
        self.particle_pool = ParticlePool(150)
        self.screen_effects = ScreenEffects()
        self.speed_lines = SpeedLines(30)
        self.score_manager = ScoreManager()
        self.hud = HUD()
        
        self.keys = {}
        
    def reset(self):
        self.player.reset()
        self.enemy_manager.reset()
        self.projectile_pool.reset()
        self.particle_pool.reset()
        self.score_manager.reset_all()
        self.state = 'playing'
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            if event.type == pygame.KEYDOWN:
                self.keys[event.key] = True
                if event.key == pygame.K_p:
                    if self.state == 'playing':
                        self.state = 'paused'
                    elif self.state == 'paused':
                        self.state = 'playing'
                if event.key == pygame.K_r and self.state == 'game_over':
                    self.reset()
            if event.type == pygame.KEYUP:
                self.keys[event.key] = False
        return True
        
    def update(self, dt):
        if self.state != 'playing':
            return
            
        keys = pygame.key.get_pressed()
        
        # Player
        self.player.update(dt, keys)
        
        # Shooting
        if keys[pygame.K_SPACE] and self.player.shoot():
            self.projectile_pool.fire(self.player.x, self.player.y - 20)
            
        # Background
        self.background.update(dt)
        
        # Enemies
        self.enemy_manager.update(dt, self.player.x, self.player.y)
        
        # Projectiles
        self.projectile_pool.update(dt)
        
        # Particles
        self.particle_pool.update(dt)
        
        # Speed lines
        self.speed_lines.update(dt)
        
        # Screen effects
        self.screen_effects.update(dt)
        
        # HUD
        self.hud.update(dt)
        
        # Collisions: Projectiles vs Enemies
        for enemy in self.enemy_manager.enemies:
            if not enemy.active:
                continue
            enemy_rect = enemy.get_rect()
            if self.projectile_pool.check_collision(enemy_rect):
                if enemy.take_damage():
                    sx, sy, _ = enemy.get_screen_pos()
                    self.particle_pool.spawn_explosion(sx, sy, enemy.color, 15)
                    self.score_manager.add_kill(enemy.points)
                    self.hud.add_score_popup(enemy.points, sx, sy, self.score_manager.multiplier)
                    self.screen_effects.shake(5, 100)
                else:
                    sx, sy, _ = enemy.get_screen_pos()
                    self.particle_pool.spawn_explosion(sx, sy, enemy.color, 5)
                    
        # Collisions: Player vs Enemies
        player_rect = self.player.get_rect()
        enemy = self.enemy_manager.check_player_collision(player_rect)
        if enemy:
            if self.player.take_damage():
                sx, sy, _ = enemy.get_screen_pos()
                self.particle_pool.spawn_explosion(sx, sy, COLORS['red'], 20)
                self.screen_effects.shake(10, 200)
                self.screen_effects.trigger_hit_flash()
                self.score_manager.take_damage()
                if self.player.health <= 0:
                    self.state = 'game_over'
                    
        # Wave completion
        if self.enemy_manager.wave_complete:
            self.enemy_manager.advance_wave()
            self.score_manager.score += 500 * self.enemy_manager.wave_number
            
    def render(self):
        offset_x, offset_y = self.screen_effects.get_offset()
        
        # Background
        self.background.draw(self.screen)
        
        # Speed lines
        self.speed_lines.draw(self.screen)
        
        # Particles (behind)
        self.particle_pool.draw(self.screen)
        
        # Enemies
        self.enemy_manager.draw(self.screen)
        
        # Projectiles
        self.projectile_pool.draw(self.screen)
        
        # Player
        self.player.draw(self.screen)
        
        # Hit flash overlay
        if self.screen_effects.hit_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 0, 0, 50))
            self.screen.blit(flash_surf, (0, 0))
            
        # HUD
        self.hud.draw_health(self.screen, self.player.health, self.player.max_health)
        self.hud.draw_score(self.screen, self.score_manager.score, self.score_manager.multiplier)
        self.hud.draw_wave(self.screen, self.enemy_manager.wave_number)
        self.hud.draw_score_popups(self.screen)
        
        # Paused
        if self.state == 'paused':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            text = self.hud.font_large.render("PAUSED", True, COLORS['white'])
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(text, rect)
            sub = self.hud.font_medium.render("Press P to Resume", True, COLORS['gray'])
            sub_rect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(sub, sub_rect)
            
        # Game Over
        if self.state == 'game_over':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            text = self.hud.font_large.render("GAME OVER", True, COLORS['red'])
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
            self.screen.blit(text, rect)
            score_text = self.hud.font_medium.render(f"Final Score: {self.score_manager.score}", True, COLORS['cyan'])
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(score_text, score_rect)
            wave_text = self.hud.font_small.render(f"Wave Reached: {self.enemy_manager.wave_number}", True, COLORS['white'])
            wave_rect = wave_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
            self.screen.blit(wave_text, wave_rect)
            restart_text = self.hud.font_small.render("Press R to Restart", True, COLORS['gray'])
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
            self.screen.blit(restart_text, restart_rect)
            
        pygame.display.flip()
        
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if not self.handle_events():
                break
            self.update(dt)
            self.render()
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()

