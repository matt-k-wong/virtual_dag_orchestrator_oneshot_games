# game.py
import sys, subprocess, math, random

# ----- Bootstrap -----
def ensure_pygame():
    try:
        import pygamece
        return pygamece
    except Exception:
        try:
            import pygame
            return pygame
        except Exception:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
            import pygamece
            return pygamece

pg = ensure_pygame()

class Vec3:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    def __sub__(self, other): return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, s): return Vec3(self.x * s, self.y * s, self.z * s)
    def __rmul__(self, s): return Vec3(self.x * s, self.y * s, self.z * s)
    def __repr__(self): return f"Vec3({self.x}, {self.y}, {self.z})"
    def update(self, x, y, z=0):
        self.x, self.y, self.z = x, y, z
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

Vector2 = Vec3

# ----- CONFIG -----
CONFIG = {
    "WIN_W": 960,
    "WIN_H": 540,
    "FPS": 60,
    "SKY_TOP": (13, 56, 136),
    "SKY_BOTTOM": (173, 216, 230),
    "GROUND_COLOR": (60, 60, 60),
    "GRID_COLOR": (80, 80, 80),
    "JET_COLOR": (255, 140, 0),
    "RING_COLOR_START": (0, 200, 0),
    "RING_COLOR_END": (255, 215, 0),
    "PARTICLE_COLOR": (255, 255, 255),
    "BASE_SPEED": 5.0,
    "SPEED_INCREASE": 0.02,
    "BASE_SPAWN_INTERVAL": 2.0,
    "MIN_SPAWN_INTERVAL": 0.5,
    "SPAWN_INTERVAL_DECREASE": 0.001,
    "BASE_RING_SIZE": 3.0,
    "RING_SIZE_DECREASE": 0.0005,
    "MIN_RING_SIZE": 1.0,
    "RING_PASS_TOLERANCE": 0.5,
    "PARTICLE_COUNT_PASS": 12,
    "PARTICLE_COUNT_CRASH": 30,
    "SCREEN_SHAKE_INTENSITY": 6,
    "SCREEN_SHAKE_DECAY": 0.92,
    "FIELD_OF_VIEW": 45.0,
    "NEAR_CLIP": 0.1,
}

# ----- Helper: 3D -> 2D projection -----
def project(point, camera_z):
    x, y, z = point
    if z <= camera_z + CONFIG["NEAR_CLIP"]:
        return None
    scale = CONFIG["WIN_H"] / (2 * math.tan(math.radians(CONFIG["FIELD_OF_VIEW"] / 2)))
    proj_x = CONFIG["WIN_W"] / 2 + scale * (x - 0) / (z - camera_z)
    proj_y = CONFIG["WIN_H"] / 2 - scale * (y - 0) / (z - camera_z)
    return int(proj_x), int(proj_y)

# ----- Particle -----
class Particle:
    __slots__ = ("pos", "vel", "life", "max_life")
    def __init__(self, pos, vel, life):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.life = life
        self.max_life = life
    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
    def draw(self, surf, offset):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        col = (*CONFIG["PARTICLE_COLOR"], alpha)
        s = pg.Surface((2, 2), pg.SRCALPHA)
        pg.draw.circle(s, col, (1, 1), 2)
        surf.blit(s, (int(self.pos.x + offset.x), int(self.pos.y + offset.y)))

# ----- Screen Shake -----
class ScreenShake:
    def __init__(self):
        self.offset = Vector2(0, 0)
        self.intensity = 0.0
    def trigger(self, amount):
        self.intensity = amount
    def update(self, dt):
        if self.intensity > 0:
            self.offset.update(random.uniform(-1, 1), random.uniform(-1, 1))
            self.offset *= self.intensity
            self.intensity *= CONFIG["SCREEN_SHAKE_DECAY"]
            if self.intensity < 0.1:
                self.intensity = 0.0
                self.offset.update(0, 0)
        else:
            self.offset.update(0, 0)

# ----- Player -----
class Player:
    def __init__(self):
        self.pos = Vector2(0, 0, 0)  # world space
        self.pitch = 0.0   # up/down radians
        self.roll = 0.0    # tilt left/right radians
        self.speed = CONFIG["BASE_SPEED"]
    def update(self, dt, keys):
        # throttle
        if keys[pg.K_SPACE] or keys[pg.K_UP]:
            self.speed += CONFIG["SPEED_INCREASE"] * dt * 10
        if keys[pg.K_LSHIFT] or keys[pg.K_DOWN]:
            self.speed -= CONFIG["SPEED_INCREASE"] * dt * 10
        self.speed = max(1.0, self.speed)
        # pitch
        if keys[pg.K_w] or keys[pg.K_UP]:
            self.pitch -= 0.003 * dt * 60
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            self.pitch += 0.003 * dt * 60
        self.pitch = max(-0.5, min(0.5, self.pitch))
        # roll
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            self.roll += 0.004 * dt * 60
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            self.roll -= 0.004 * dt * 60
        self.roll = max(-0.4, min(0.4, self.roll))
        # forward movement (world moves backward)
        forward = Vector2(
            math.sin(self.yaw()) * math.cos(self.pitch),
            math.sin(self.pitch),
            -math.cos(self.yaw()) * math.cos(self.pitch)
        )
        self.pos -= forward * self.speed * dt
    def yaw(self):
        return self.roll  # using roll as yaw for simplicity (no separate yaw control)
    def get_forward_vector(self):
        return Vector2(
            math.sin(self.yaw()) * math.cos(self.pitch),
            math.sin(self.pitch),
            -math.cos(self.yaw()) * math.cos(self.pitch)
        )
    def get_position(self):
        return self.pos

# ----- Ring & Spawner -----
class Ring:
    def __init__(self, z, size, passed=False):
        self.pos = Vector2(0, 0, z)  # centered on X=Y=0
        self.size = size
        self.passed = passed
    def update(self, dt, speed):
        self.pos.z -= speed * dt
    def draw(self, surf, camera_z, offset):
        proj = project(self.pos, camera_z)
        if proj is None:
            return
        # scale size by perspective
        scale = (CONFIG["WIN_H"] / 2) / (proj[1] - (CONFIG["WIN_H"] / 2)) if proj[1] != CONFIG["WIN_H"] / 2 else 1
        size_2d = max(1, int(self.size * scale * 0.5))
        color = tuple(
            int(CONFIG["RING_COLOR_START"][i] + (CONFIG["RING_COLOR_END"][i] - CONFIG["RING_COLOR_START"][i]) *
                ((CONFIG["BASE_RING_SIZE"] - self.size) / (CONFIG["BASE_RING_SIZE"] - CONFIG["MIN_RING_SIZE"]))
            ) for i in range(3)
        )
        pg.draw.circle(surf, color, proj, size_2d, 2)
        # inner circle for visual depth
        pg.draw.circle(surf, (0,0,0), proj, max(1, size_2d//2), 1)

class RingSpawner:
    def __init__(self):
        self.rings = []
        self.timer = 0.0
        self.spawn_interval = CONFIG["BASE_SPAWN_INTERVAL"]
        self.next_size = CONFIG["BASE_RING_SIZE"]
    def update(self, dt, speed, difficulty):
        self.timer -= dt
        if self.timer <= 0:
            self.spawn_interval = max(
                CONFIG["MIN_SPAWN_INTERVAL"],
                self.spawn_interval - CONFIG["SPAWN_INTERVAL_DECREASE"] * dt
            )
            self.timer = self.spawn_interval
            # ensure spacing
            if not self.rings or (self.rings[-1].pos.z - self.next_size*2) > 30:
                self.rings.append(Ring(self.rings[-1].pos.z + 40 if self.rings else 80, self.next_size))
                self.next_size = max(
                    CONFIG["MIN_RING_SIZE"],
                    self.next_size - CONFIG["RING_SIZE_DECREASE"] * dt
                )
        # update rings
        for r in self.rings:
            r.update(dt, speed)
        # remove far rings
        self.rings = [r for r in self.rings if r.pos.z > -20]
    def draw(self, surf, camera_z, offset):
        for r in self.rings:
            r.draw(surf, camera_z, offset)
    def check_pass_miss(self, player_pos):
        # find closest ring ahead of player
        ahead = [r for r in self.rings if r.pos.z > player_pos.z and not r.passed]
        if not ahead:
            return False, None
        ring = min(ahead, key=lambda r: r.pos.z)
        # check if player passed through ring plane
        if player_pos.z > ring.pos.z:
            # calculate offset in X/Y at ring plane
            # approximate by using player pos (since X/Y ~0)
            offset_x = player_pos.x
            offset_y = player_pos.y
            if abs(offset_x) < ring.size/2 + CONFIG["RING_PASS_TOLERANCE"] and \
               abs(offset_y) < ring.size/2 + CONFIG["RING_PASS_TOLERANCE"]:
                ring.passed = True
                return True, ring
            else:
                return False, ring
        return False, None

# ----- Difficulty -----
class DifficultyManager:
    def __init__(self):
        self.speed = CONFIG["BASE_SPEED"]
        self.spawn_interval = CONFIG["BASE_SPAWN_INTERVAL"]
        self.ring_size = CONFIG["BASE_RING_SIZE"]
    def update(self, dt):
        self.speed += CONFIG["SPEED_INCREASE"] * dt
        self.spawn_interval = max(
            CONFIG["MIN_SPAWN_INTERVAL"],
            self.spawn_interval - CONFIG["SPAWN_INTERVAL_DECREASE"] * dt
        )
        self.ring_size = max(
            CONFIG["MIN_RING_SIZE"],
            self.ring_size - CONFIG["RING_SIZE_DECREASE"] * dt
        )
    def get(self):
        return self.speed, self.spawn_interval, self.ring_size

# ----- HUD -----
def draw_hud(surf, font, player, score, speed, altitude):
    # speed
    txt = font.render(f"Speed: {speed:.1f}", True, (255,255,255))
    surf.blit(txt, (10, 10))
    # altitude
    txt = font.render(f"Altitude: {altitude:.1f}", True, (255,255,255))
    surf.blit(txt, (10, 35))
    # score
    txt = font.render(f"Score: {score}", True, (255,215,0))
    surf.blit(txt, (10, 60))
    # simple altimeter bar
    bar_w, bar_h = 20, 100
    bar_x, bar_y = CONFIG["WIN_W"] - 30, 20
    pg.draw.rect(surf, (50,50,50), (bar_x, bar_y, bar_w, bar_h), 2)
    fill = int((altitude + 50) / 100 * bar_h)  # assume altitude range -50 to 50
    fill = max(0, min(bar_h, fill))
    pg.draw.rect(surf, (0,200,0), (bar_x, bar_y + bar_h - fill, bar_w, fill))

# ----- Main Game -----
def main():
    pg.init()
    screen = pg.display.set_mode((CONFIG["WIN_W"], CONFIG["WIN_H"]))
    pg.display.set_caption("Skyward Rings")
    clock = pg.time.Clock()
    font = pg.font.SysFont(None, 24)
    # game objects
    player = Player()
    spawner = RingSpawner()
    difficulty = DifficultyManager()
    particles = []
    shake = ScreenShake()
    # state
    score = 0
    game_over = False
    passed_rings = set()
    camera_z = -10.0  # camera slightly behind player
    # ----- Main Loop -----
    while True:
        dt = clock.tick(CONFIG["FPS"]) / 1000.0
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                return
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    pg.quit()
                    return
                if e.key == pg.K_r and game_over:
                    # restart
                    player = Player()
                    spawner = RingSpawner()
                    difficulty = DifficultyManager()
                    particles = []
                    shake = ScreenShake()
                    score = 0
                    game_over = False
                    passed_rings.clear()
        if not game_over:
            keys = pg.key.get_pressed()
            player.update(dt, keys)
            speed, spawn_int, ring_size = difficulty.get()
            difficulty.update(dt)
            spawner.update(dt, speed, difficulty)
            # check pass/miss
            passed, ring = spawner.check_pass_miss(player.get_position())
            if passed:
                score += 10
                passed_rings.add(id(ring))
                # particle burst
                for _ in range(CONFIG["PARTICLE_COUNT_PASS"]):
                    ang = random.uniform(0, 2*math.pi)
                    sp = random.uniform(2, 5)
                    vel = Vector2(math.cos(ang)*sp, math.sin(ang)*sp)
                    particles.append(Particle((0,0), vel, random.uniform(0.3,0.6)))
                shake.trigger(CONFIG["SCREEN_SHAKE_INTENSITY"] * 0.5)
            elif ring is not None and not ring.passed:
                # miss -> crash
                game_over = True
                shake.trigger(CONFIG["SCREEN_SHAKE_INTENSITY"])
                for _ in range(CONFIG["PARTICLE_COUNT_CRASH"]):
                    ang = random.uniform(0, 2*math.pi)
                    sp = random.uniform(1, 4)
                    vel = Vector2(math.cos(ang)*sp, math.sin(ang)*sp)
                    particles.append(Particle((0,0), vel, random.uniform(0.2,0.5)))
            # ground collision
            if player.get_position().y < -0.5:  # ground at y=0, player slightly below
                game_over = True
                shake.trigger(CONFIG["SCREEN_SHAKE_INTENSITY"] * 1.5)
                for _ in range(CONFIG["PARTICLE_COUNT_CRASH"]):
                    ang = random.uniform(0, 2*math.pi)
                    sp = random.uniform(1, 4)
                    vel = Vector2(math.cos(ang)*sp, math.sin(ang)*sp)
                    particles.append(Particle((0,0), vel, random.uniform(0.2,0.5)))
            # update particles
            for p in particles:
                p.update(dt)
            particles = [p for p in particles if p.life > 0]
            shake.update(dt)
        # ----- Render -----
        # sky gradient
        for y in range(CONFIG["WIN_H"]):
            t = y / CONFIG["WIN_H"]
            r = int(CONFIG["SKY_TOP"][0] + (CONFIG["SKY_BOTTOM"][0] - CONFIG["SKY_TOP"][0]) * t)
            g = int(CONFIG["SKY_TOP"][1] + (CONFIG["SKY_BOTTOM"][1] - CONFIG["SKY_TOP"][1]) * t)
            b = int(CONFIG["SKY_TOP"][2] + (CONFIG["SKY_BOTTOM"][2] - CONFIG["SKY_TOP"][2]) * t)
            pg.draw.line(screen, (r,g,b), (0, y), (CONFIG["WIN_W"], y))
        # ground plane (simple scrolling)
        ground_z = 0
        ground_y = -player.get_position().y  # invert
        # draw grid
        grid_size = 20
        for gx in range(-5, 6):
            xw = gx * grid_size
            proj1 = project((xw, ground_y, ground_z), camera_z)
            proj2 = project((xw, ground_y + 100, ground_z), camera_z)
            if proj1 and proj2:
                pg.draw.line(screen, CONFIG["GRID_COLOR"], proj1, proj2, 1)
        for gz in range(-5, 6):
            zw = gz * grid_size
            proj1 = project((0, ground_y, zw), camera_z)
            proj2 = project((100, ground_y, zw), camera_z)
            if proj1 and proj2:
                pg.draw.line(screen, CONFIG["GRID_COLOR"], proj1, proj2, 1)
        # draw rings
        spawner.draw(screen, camera_z, Vector2(0,0))
        # draw player (simple triangle)
        nose = project((0,0,10), camera_z)  # nose forward
        left = project((-2,0,-5), camera_z)
        right = project((2,0,-5), camera_z)
        if nose and left and right:
            pg.draw.polygon(screen, CONFIG["JET_COLOR"], [nose, left, right])
        # draw particles
        offset = shake.offset
        for p in particles:
            p.draw(screen, offset)
        # HUD
        altitude = -player.get_position().y
        draw_hud(screen, font, player, score, speed, altitude)
        # apply shake
        if shake.offset.length() > 0:
            pass  # offset already applied in drawing
        if game_over:
            over_font = pg.font.SysFont(None, 48)
            txt = over_font.render("GAME OVER", True, (255,60,60))
            screen.blit(txt, (CONFIG["WIN_W"]//2 - txt.get_width()//2, CONFIG["WIN_H"]//2 - 20))
            txt2 = font.render(f"Final Score: {score}", True, (255,255,255))
            screen.blit(txt2, (CONFIG["WIN_W"]//2 - txt2.get_width()//2, CONFIG["WIN_H"]//2 + 20))
            txt3 = font.render("Press R to Restart or ESC to Quit", True, (200,200,200))
            screen.blit(txt3, (CONFIG["WIN_W"]//2 - txt3.get_width()//2, CONFIG["WIN_H"]//2 + 50))
        pg.display.flip()

if __name__ == "__main__":
    main()

