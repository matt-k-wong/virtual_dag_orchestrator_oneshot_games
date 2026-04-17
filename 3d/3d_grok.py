# game.py
import subprocess
import sys
import math
import random
import time

def install_pygame():
    try:
        import pygame
        return pygame
    except ImportError:
        print("pygame not found. Installing pygame-ce (fastest) via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
            import pygame
            print("pygame-ce installed successfully!")
            return pygame
        except:
            print("pygame-ce failed. Trying standard pygame...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
            import pygame
            print("pygame installed successfully!")
            return pygame

pygame = install_pygame()
pygame.init()  # CRITICAL FIX: Initialize pygame before any fonts, display, or other modules

# ====================== 3D MATH ======================
class Vec3:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Vec3(self.x, self.y, self.z)

    def add(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def sub(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def mul(self, scalar):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        l = self.length()
        if l == 0: return Vec3()
        return self.mul(1 / l)

# Simple rotation helpers (Euler)
def rotate_x(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(v.x, v.y * c - v.z * s, v.y * s + v.z * c)

def rotate_y(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c)

def rotate_z(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(v.x * c - v.y * s, v.x * s + v.y * c, v.z)

# ====================== CAMERA & PROJECTION ======================
class Camera:
    def __init__(self):
        self.pos = Vec3(0, 0, 0)
        self.pitch = 0
        self.yaw = 0
        self.roll = 0
        self.focal = 600

    def project(self, world_point):
        # Translate
        p = world_point.sub(self.pos)
        # Rotate (order: yaw -> pitch -> roll)
        p = rotate_y(p, -self.yaw)
        p = rotate_x(p, -self.pitch)
        p = rotate_z(p, -self.roll)
        if p.z <= 0:
            return None  # Behind camera
        scale = self.focal / p.z
        screen_x = 640 + p.x * scale
        screen_y = 360 - p.y * scale
        return (int(screen_x), int(screen_y), p.z, scale)

# ====================== PARTICLES ======================
class Particle:
    def __init__(self, pos, vel, life, color, size):
        self.pos = pos.copy()
        self.vel = vel.copy()
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, pos, count, color, speed=4):
        for _ in range(count):
            vel = Vec3(random.uniform(-speed, speed), random.uniform(-speed, speed), random.uniform(-speed, speed))
            life = random.randint(15, 35)
            self.particles.append(Particle(pos.copy(), vel, life, color, random.randint(2, 5)))

    def update(self):
        for p in self.particles[:]:
            p.pos = p.pos.add(p.vel)
            p.vel = p.vel.mul(0.95)
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, screen, cam):
        for p in self.particles:
            proj = cam.project(p.pos)
            if proj:
                x, y, z, scale = proj
                alpha = int(255 * (p.life / p.max_life))
                size = max(1, int(p.size * scale / 30))
                s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.color, alpha), (size, size), size)
                screen.blit(s, (x - size, y - size))

# ====================== GAME OBJECTS ======================
class PlayerShip:
    def __init__(self):
        self.pos = Vec3(0, 0, 0)
        self.vel = Vec3(0, 0, 8)
        self.pitch = 0
        self.yaw = 0
        self.roll = 0
        self.boost = 0

    def update(self, keys, dt):
        # Controls
        if keys[pygame.K_w]: self.pitch = max(self.pitch - 2, -45)
        if keys[pygame.K_s]: self.pitch = min(self.pitch + 2, 45)
        if keys[pygame.K_a]: self.yaw = max(self.yaw - 2, -45)
        if keys[pygame.K_d]: self.yaw = min(self.yaw + 2, 45)
        if keys[pygame.K_q]: self.roll = max(self.roll - 3, -60)
        if keys[pygame.K_e]: self.roll = min(self.roll + 3, 60)

        # Decay angles
        self.pitch *= 0.92
        self.yaw *= 0.92
        self.roll *= 0.88

        # Apply rotation to velocity
        forward = Vec3(0, 0, 1)
        forward = rotate_x(forward, math.radians(self.pitch))
        forward = rotate_y(forward, math.radians(self.yaw))
        forward = rotate_z(forward, math.radians(self.roll))
        forward = forward.normalize()

        speed = 8 + self.boost * 6
        self.vel = forward.mul(speed)

        self.pos = self.pos.add(self.vel.mul(dt * 60))

        if keys[pygame.K_SPACE]:
            self.boost = min(self.boost + 0.1, 1)
        else:
            self.boost = max(self.boost - 0.08, 0)

    def get_model_points(self):
        # Simple neon fighter
        points = [
            Vec3(0, 0, 15),   # nose
            Vec3(-8, 0, -5),  # left wing
            Vec3(8, 0, -5),   # right wing
            Vec3(0, -4, -5),  # bottom
            Vec3(0, 4, -5),   # top
        ]
        for i in range(len(points)):
            p = points[i]
            p = rotate_x(p, math.radians(self.pitch))
            p = rotate_y(p, math.radians(self.yaw))
            p = rotate_z(p, math.radians(self.roll))
            points[i] = p
        return points

class Asteroid:
    def __init__(self, pos):
        self.pos = pos
        self.size = random.uniform(4, 12)
        self.rot_speed = random.uniform(-0.02, 0.02)
        self.rot = 0

    def update(self, player):
        self.rot += self.rot_speed
        to_player = player.pos.sub(self.pos)
        dist = to_player.length()
        if dist > 0:
            self.pos = self.pos.add(to_player.normalize().mul(1.5))

    def get_model(self):
        pts = []
        for i in range(8):
            a = i * 0.8 + self.rot
            r = self.size * (0.8 + random.random() * 0.4)
            pts.append(Vec3(math.cos(a) * r, math.sin(a) * r * 0.6, math.cos(a * 2) * r * 0.3))
        return pts

class Drone:
    def __init__(self, pos):
        self.pos = pos
        self.size = 5

    def update(self, player):
        to_player = player.pos.sub(self.pos)
        dist = to_player.length()
        if dist > 0:
            self.pos = self.pos.add(to_player.normalize().mul(3.5))

    def get_model(self):
        return [
            Vec3(-self.size, 0, 0),
            Vec3(self.size, 0, 0),
            Vec3(0, -self.size, 0),
            Vec3(0, self.size, 0),
            Vec3(0, 0, self.size * 1.5),
        ]

class Ring:
    def __init__(self, pos):
        self.pos = pos
        self.radius = 18
        self.passed = False

    def check_pass(self, player):
        if self.passed: return False
        dist = player.pos.sub(self.pos).length()
        if dist < self.radius + 4 and abs(player.pos.z - self.pos.z) < 10:
            self.passed = True
            return True
        return False

class Projectile:
    def __init__(self, pos, dir_vec):
        self.pos = pos.copy()
        self.vel = dir_vec.normalize().mul(25)
        self.life = 60

    def update(self):
        self.pos = self.pos.add(self.vel)
        self.life -= 1

# ====================== MAIN GAME ======================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("VOIDWING - 3D Space Flight Simulator")
        self.clock = pygame.time.Clock()
        # Portable fonts (None = default system font, works everywhere)
        self.font = pygame.font.SysFont(None, 24)
        self.big_font = pygame.font.SysFont(None, 72, bold=True)

        self.cam = Camera()
        self.player = PlayerShip()
        self.particles = ParticleSystem()
        self.asteroids = []
        self.drones = []
        self.rings = []
        self.projectiles = []

        self.score = 0
        self.distance = 0
        self.game_over = False
        self.paused = False
        self.start_time = time.time()
        self.difficulty_timer = 0

        # FIXED: Pre-generated starfield (no flicker)
        self.stars = []
        for _ in range(120):
            self.stars.append([
                random.randint(-800, 800),
                random.randint(-500, 500),
                random.randint(50, 800)
            ])

        # Initial objects
        self.spawn_initial()

    def spawn_initial(self):
        for i in range(12):
            z = 200 + i * 80
            x = random.uniform(-120, 120)
            y = random.uniform(-80, 80)
            self.asteroids.append(Asteroid(Vec3(x, y, z)))
        for i in range(4):
            z = 300 + i * 120
            self.rings.append(Ring(Vec3(random.uniform(-60, 60), random.uniform(-60, 60), z)))

    def spawn_wave(self):
        for _ in range(6 + int(self.difficulty_timer // 30)):
            z = self.cam.pos.z + 400 + random.uniform(0, 100)
            x = random.uniform(-180, 180)
            y = random.uniform(-120, 120)
            self.asteroids.append(Asteroid(Vec3(x, y, z)))
        if len(self.drones) < 3 + int(self.difficulty_timer // 40):
            z = self.cam.pos.z + 350
            x = random.uniform(-100, 100)
            y = random.uniform(-80, 80)
            self.drones.append(Drone(Vec3(x, y, z)))
        if len(self.rings) < 3:
            z = self.cam.pos.z + 280
            x = random.uniform(-70, 70)
            y = random.uniform(-70, 70)
            self.rings.append(Ring(Vec3(x, y, z)))

    def update(self):
        if self.game_over or self.paused: return
        dt = self.clock.get_time() / 1000.0
        keys = pygame.key.get_pressed()

        self.player.update(keys, dt)

        # Camera follows player with lag
        self.cam.pos = self.cam.pos.add((self.player.pos.sub(self.cam.pos)).mul(0.15))
        self.cam.pitch = self.player.pitch * 0.6
        self.cam.yaw = self.player.yaw * 0.6
        self.cam.roll = self.player.roll * 0.8

        self.particles.update()

        # Asteroids
        for a in self.asteroids[:]:
            a.update(self.player)
            if (a.pos.sub(self.player.pos)).length() < a.size + 6:
                self.crash()
                return
            if a.pos.z < self.cam.pos.z - 50:
                self.asteroids.remove(a)

        # Drones
        for d in self.drones[:]:
            d.update(self.player)
            if (d.pos.sub(self.player.pos)).length() < d.size + 8:
                self.crash()
                return
            if d.pos.z < self.cam.pos.z - 50:
                self.drones.remove(d)

        # Rings
        for r in self.rings[:]:
            if r.check_pass(self.player):
                self.score += 250
                self.particles.emit(r.pos, 40, (255, 100, 255))
                self.rings.remove(r)
            if r.pos.z < self.cam.pos.z - 50:
                self.rings.remove(r)

        # Projectiles
        for p in self.projectiles[:]:
            p.update()
            hit = False
            for a in self.asteroids[:]:
                if (p.pos.sub(a.pos)).length() < a.size + 3:
                    self.asteroids.remove(a)
                    self.particles.emit(p.pos, 25, (255, 200, 50))
                    hit = True
                    self.score += 50
                    break
            if hit:
                self.projectiles.remove(p)
                continue
            if p.life <= 0:
                self.projectiles.remove(p)

        # Distance & score
        self.distance += self.player.vel.z * dt * 60
        self.score = int(self.distance / 2 + self.score)

        # Difficulty
        self.difficulty_timer = time.time() - self.start_time
        if random.random() < 0.03:
            self.spawn_wave()

        # Thrust particles
        if random.random() < 0.6 + self.player.boost * 0.8:
            thrust_pos = self.player.pos.sub(Vec3(0, 0, 12))
            thrust_pos = rotate_z(thrust_pos, math.radians(self.player.roll))
            self.particles.emit(thrust_pos, 3, (100, 255, 255), speed=6)

        self.cam.pos.z += self.player.vel.z * dt * 0.6

    def crash(self):
        self.game_over = True
        self.particles.emit(self.player.pos, 80, (255, 80, 80), speed=12)

    def fire(self):
        if len(self.projectiles) > 8: return
        nose = self.player.pos.add(Vec3(0, 0, 18))
        dir_vec = Vec3(0, 0, 1)
        dir_vec = rotate_x(dir_vec, math.radians(self.player.pitch))
        dir_vec = rotate_y(dir_vec, math.radians(self.player.yaw))
        dir_vec = rotate_z(dir_vec, math.radians(self.player.roll))
        self.projectiles.append(Projectile(nose, dir_vec))
        self.particles.emit(nose, 8, (255, 255, 100), speed=2)

    def draw_3d_object(self, points, color, cam, filled=False):
        projected = []
        for p in points:
            proj = cam.project(p)
            if proj:
                projected.append(proj)
        if len(projected) < 2: return
        for i in range(len(projected)):
            p1 = projected[i]
            p2 = projected[(i + 1) % len(projected)]
            pygame.draw.line(self.screen, color, (p1[0], p1[1]), (p2[0], p2[1]), max(1, int(3 * p1[3] / 80)))
        if filled and len(projected) > 3:
            pts2d = [(p[0], p[1]) for p in projected]
            pygame.draw.polygon(self.screen, (*color, 60), pts2d)

    def draw(self):
        self.screen.fill((5, 2, 18))

        # FIXED: Stable starfield with depth parallax
        for star in self.stars:
            x = (star[0] + self.cam.pos.x * 0.3) % 1280
            y = (star[1] + self.cam.pos.y * 0.3) % 720
            z = star[2]
            scale = 400 / z
            pygame.draw.circle(self.screen, (220, 220, 255), (int(x), int(y)), max(1, int(scale)))

        # Draw rings
        for r in self.rings:
            for depth in [-6, 6]:
                ring_pts = []
                for i in range(24):
                    a = i * (math.pi * 2 / 24)
                    px = r.pos.x + math.cos(a) * r.radius
                    py = r.pos.y + math.sin(a) * r.radius
                    pz = r.pos.z + depth
                    proj = self.cam.project(Vec3(px, py, pz))
                    if proj:
                        ring_pts.append((proj[0], proj[1]))
                if len(ring_pts) > 6:
                    pygame.draw.lines(self.screen, (255, 80, 255), True, ring_pts, 4)

        # Draw asteroids
        for a in self.asteroids:
            model = a.get_model()
            world_pts = [a.pos.add(p) for p in model]
            self.draw_3d_object(world_pts, (180, 180, 200), self.cam)

        # Draw drones
        for d in self.drones:
            model = d.get_model()
            world_pts = [d.pos.add(p) for p in model]
            self.draw_3d_object(world_pts, (255, 60, 60), self.cam)

        # Draw player ship
        ship_pts = self.player.get_model_points()
        world_ship = [self.player.pos.add(p) for p in ship_pts]
        self.draw_3d_object(world_ship, (80, 255, 255), self.cam, filled=True)

        # Projectiles
        for p in self.projectiles:
            proj = self.cam.project(p.pos)
            if proj:
                pygame.draw.circle(self.screen, (255, 255, 100), (proj[0], proj[1]), 4)

        # Particles
        self.particles.draw(self.screen, self.cam)

        # HUD
        speed_text = self.font.render(f"SPEED {int(self.player.vel.length()*12)}", True, (80, 255, 255))
        self.screen.blit(speed_text, (40, 40))
        score_text = self.font.render(f"SCORE {self.score}", True, (255, 255, 100))
        self.screen.blit(score_text, (40, 80))
        dist_text = self.font.render(f"DIST {int(self.distance)}", True, (200, 200, 255))
        self.screen.blit(dist_text, (40, 120))

        # Boost bar
        boost_w = int(self.player.boost * 200)
        pygame.draw.rect(self.screen, (255, 100, 255), (40, 170, boost_w, 12))
        pygame.draw.rect(self.screen, (255, 255, 255), (40, 170, 200, 12), 2)

        if self.game_over:
            overlay = pygame.Surface((1280, 720))
            overlay.set_alpha(180)
            overlay.fill((20, 0, 0))
            self.screen.blit(overlay, (0, 0))
            go_text = self.big_font.render("CRITICAL FAILURE", True, (255, 80, 80))
            self.screen.blit(go_text, (640 - go_text.get_width()//2, 220))
            final_text = self.font.render(f"FINAL SCORE: {self.score}", True, (255, 255, 100))
            self.screen.blit(final_text, (640 - final_text.get_width()//2, 340))
            restart_text = self.font.render("PRESS R TO RESTART", True, (200, 200, 200))
            self.screen.blit(restart_text, (640 - restart_text.get_width()//2, 410))

        if self.paused:
            pause_text = self.big_font.render("PAUSED", True, (255, 255, 255))
            self.screen.blit(pause_text, (640 - pause_text.get_width()//2, 300))

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                    if event.key == pygame.K_r and self.game_over:
                        self.__init__()  # Full restart
                    if event.key == pygame.K_f and not self.game_over:
                        self.fire()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.game_over:
                    self.fire()

            self.update()
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    game = Game()
    game.run()
