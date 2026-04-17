# game.py
import sys
import math
import random
import time

# --- Bootstrap & Imports ---
try:
    import pygame
    from pygame import gfxdraw
except ImportError:
    print("Pygame not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    import pygame
    from pygame import gfxdraw

# --- Constants ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
FOV = 400
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2

# Colors (Neon Palette)
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_CYAN = (0, 255, 255)
C_MAGENTA = (255, 0, 255)
C_LIME = (50, 255, 50)
C_RED = (255, 50, 50)
C_GRID = (20, 20, 50)

# --- Math & Projection ---
class Vector3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)
    
    def add(self, v): return Vector3(self.x + v.x, self.y + v.y, self.z + v.z)
    def sub(self, v): return Vector3(self.x - v.x, self.y - v.y, self.z - v.z)
    def mul(self, s): return Vector3(self.x * s, self.y * s, self.z * s)
    def dist(self, v): return math.sqrt((self.x-v.x)**2 + (self.y-v.y)**2 + (self.z-v.z)**2)

def project(v, cam_z=0):
    """Projects 3D point to 2D screen space."""
    z = v.z - cam_z
    if z <= 0: return None, 0 # Behind camera
    scale = FOV / z
    x = int(v.x * scale + CENTER_X)
    y = int(v.y * scale + CENTER_Y)
    return (x, y), scale

# --- Entities ---
class GameObject:
    def __init__(self, x, y, z, color):
        self.pos = Vector3(x, y, z)
        self.color = color
        self.active = True
        self.radius = 20 # Collision radius approximation

    def update(self, dt):
        pass

    def draw(self, surface, cam_z=0):
        pass

    def get_screen_pos(self, cam_z=0):
        return project(self.pos, cam_z)

class Player(GameObject):
    def __init__(self):
        super().__init__(0, 0, 100, C_CYAN)
        self.speed = 300
        self.vel = Vector3(0, 0, 0)
        self.radius = 30

    def update(self, dt, keys):
        # Movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.vel.x -= 2000 * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vel.x += 2000 * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.vel.y -= 2000 * dt
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.vel.y += 2000 * dt
        
        # Friction
        self.vel.x *= 0.9
        self.vel.y *= 0.9
        
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        
        # Bounds
        limit = 400
        self.pos.x = max(-limit, min(limit, self.pos.x))
        self.pos.y = max(-limit, min(limit, self.pos.y))

    def draw(self, surface, cam_z=0):
        p, scale = self.get_screen_pos(cam_z)
        if p is None: return
        s = 20 * scale
        # Draw Ship (Triangle)
        pts = [
            (p[0], p[1] - s),
            (p[0] - s, p[1] + s),
            (p[0] + s, p[1] + s)
        ]
        pygame.draw.polygon(surface, self.color, pts, 2)
        # Engine glow
        pygame.draw.circle(surface, C_LIME, (int(p[0]), int(p[1]+s)), int(5*scale))

class Enemy(GameObject):
    def __init__(self, x, y, z):
        super().__init__(x, y, z, C_RED)
        self.speed = 200
        self.rot = 0
        self.radius = 40

    def update(self, dt):
        self.pos.z -= self.speed
        self.rot += 2
        if self.pos.z < -100:
            self.active = False

    def draw(self, surface, cam_z=0):
        p, scale = self.get_screen_pos(cam_z)
        if p is None: return
        s = 30 * scale
        # Draw Cube Wireframe
        half = s
        # Front face
        f_pts = [
            (p[0]-half, p[1]-half), (p[0]+half, p[1]-half),
            (p[0]+half, p[1]+half), (p[0]-half, p[1]+half)
        ]
        # Back face (offset for 3D effect)
        offset = 10 * scale
        b_pts = [
            (p[0]-half+offset, p[1]-half+offset), (p[0]+half+offset, p[1]-half+offset),
            (p[0]+half+offset, p[1]+half+offset), (p[0]-half+offset, p[1]+half+offset)
        ]
        
        for i in range(4):
            pygame.draw.line(surface, self.color, f_pts[i], f_pts[(i+1)%4], 2)
            pygame.draw.line(surface, self.color, b_pts[i], b_pts[(i+1)%4], 2)
            pygame.draw.line(surface, self.color, f_pts[i], b_pts[i], 2)

class Bullet(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 100, C_LIME)
        self.speed = 800
        self.radius = 10

    def update(self, dt):
        self.pos.z -= self.speed * dt
        if self.pos.z < -200:
            self.active = False

    def draw(self, surface, cam_z=0):
        p, scale = self.get_screen_pos(cam_z)
        if p:
            pygame.draw.circle(surface, self.color, p, int(5 * scale))

class Particle(GameObject):
    def __init__(self, x, y, z):
        super().__init__(x, y, z, C_WHITE)
        self.vel = Vector3(random.uniform(-100, 100), random.uniform(-100, 100), random.uniform(-100, 100))
        self.life = 1.0

    def update(self, dt):
        self.pos = self.pos.add(self.vel * dt)
        self.life -= dt * 2
        if self.life <= 0: self.active = False

    def draw(self, surface, cam_z=0):
        p, scale = self.get_screen_pos(cam_z)
        if p and self.life > 0:
            alpha = int(255 * self.life)
            color = (min(255, self.color[0]+50), min(255, self.color[1]+50), min(255, self.color[2]+50))
            pygame.draw.circle(surface, color, p, int(3 * scale * self.life))

# --- Game Engine ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NEON HORIZON")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 64, bold=True)
        
        self.reset()

    def reset(self):
        self.player = Player()
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.score = 0
        self.state = "PLAYING" # PLAYING, GAMEOVER
        self.shake = 0
        self.spawn_timer = 0
        self.grid_offset = 0

    def spawn_enemy(self):
        x = random.uniform(-300, 300)
        y = random.uniform(-200, 200)
        z = 2000
        self.enemies.append(Enemy(x, y, z))

    def add_explosion(self, pos):
        for _ in range(10):
            self.particles.append(Particle(pos.x, pos.y, pos.z))

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if self.state == "PLAYING":
            self.player.update(1/60, keys)
            
            # Shooting
            if keys[pygame.K_SPACE]:
                if not hasattr(self, 'last_shot') or time.time() - self.last_shot > 0.15:
                    self.bullets.append(Bullet(self.player.pos.x, self.player.pos.y))
                    self.last_shot = time.time()
        elif self.state == "GAMEOVER":
            if keys[pygame.K_r]:
                self.reset()

    def update(self):
        if self.state != "PLAYING":
            self.handle_input()
            return

        dt = 1/60
        self.handle_input()
        self.grid_offset = (self.grid_offset + 20) % 100

        # Spawning
        self.spawn_timer += dt
        spawn_rate = max(0.2, 1.0 - (self.score / 5000))
        if self.spawn_timer > spawn_rate:
            self.spawn_enemy()
            self.spawn_timer = 0

        # Updates
        self.player.update(dt, pygame.key.get_pressed())
        
        for obj in self.enemies + self.bullets + self.particles:
            obj.update(dt)
        
        # Cleanup
        self.enemies = [e for e in self.enemies if e.active]
        self.bullets = [b for b in self.bullets if e.active]
        self.particles = [p for p in self.particles if p.active]

        # Collisions
        # Bullet vs Enemy
        for b in self.bullets:
            for e in self.enemies:
                if b.pos.dist(e.pos) < (b.radius + e.radius):
                    b.active = False
                    e.active = False
                    self.score += 10
                    self.add_explosion(e.pos)
                    self.shake = 5
        
        # Player vs Enemy
        for e in self.enemies:
            if self.player.pos.dist(e.pos) < (self.player.radius + e.radius):
                self.state = "GAMEOVER"
                self.shake = 20

        # Score
        self.score += 1
        if self.shake > 0: self.shake -= 1

    def draw_grid(self):
        # Simple moving floor grid
        for i in range(-10, 10):
            for j in range(0, 20):
                z = j * 100 + self.grid_offset - 1000
                if z < 10: continue
                # Horizontal lines
                p1, _ = project(Vector3(i * 100, 200, z), 0)
                p2, _ = project(Vector3(i * 100, 200, z + 100), 0)
                if p1 and p2:
                    pygame.draw.line(self.screen, C_GRID, p1, p2, 1)
                
                # Vertical lines (simplified)
                if j == 0:
                    p3, _ = project(Vector3(i * 100, 200, 2000), 0)
                    p4, _ = project(Vector3((i+1) * 100, 200, 2000), 0)
                    if p3 and p4:
                         pygame.draw.line(self.screen, C_GRID, p3, p4, 1)

    def render(self):
        self.screen.fill(C_BLACK)
        
        # Screen Shake
        offset_x = random.randint(-self.shake, self.shake)
        offset_y = random.randint(-self.shake, self.shake)
        self.screen.blit(self.screen, (0,0)) # Clear logic handled by fill, but shake needs transform
        # Actually, let's just offset drawing
        old_proj = project # Hacky way to inject offset globally? No, too complex for one-shot.
        # Simple shake: draw everything on a surface then blit with offset
        game_surf = pygame.Surface((WIDTH, HEIGHT))
        game_surf.fill(C_BLACK)
        
        self.draw_grid()

        # Sort by Z (Painter's algorithm)
        all_objs = self.enemies + self.bullets + self.particles + [self.player]
        all_objs.sort(key=lambda k: k.pos.z, reverse=True)

        for obj in all_objs:
            obj.draw(game_surf, 0)
        
        # Particles don't need Z sort strictly but look better if drawn last
        for p in self.particles:
            p.draw(game_surf, 0)

        # Apply Shake
        final_surf = pygame.Surface((WIDTH + self.shake*2, HEIGHT + self.shake*2))
        final_surf.blit(game_surf, (0,0))
        self.screen.blit(final_surf, (offset_x - self.shake, offset_y - self.shake))

        # HUD
        score_text = self.font.render(f"SCORE: {self.score}", True, C_WHITE)
        self.screen.blit(score_text, (20, 20))

        if self.state == "GAMEOVER":
            over_text = self.big_font.render("GAME OVER", True, C_RED)
            restart_text = self.font.render("Press 'R' to Restart", True, C_WHITE)
            rect = over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 20))
            rect2 = restart_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 40))
            self.screen.blit(over_text, rect)
            self.screen.blit(restart_text, rect2)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        Game().run()
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()

