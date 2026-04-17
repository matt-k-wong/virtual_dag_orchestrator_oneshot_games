# game.py
import sys
import subprocess
import random
import math
import time

# --- Bootstrap Dependencies ---
def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            __import__(package)
        except Exception:
            print(f"Failed to install {package}. Please install manually.")
            sys.exit(1)

install_and_import("pygame")
import pygame

# --- Configuration ---
class Config:
    WIDTH = 1280
    HEIGHT = 720
    FPS = 60
    TITLE = "NEON PROTOCOL: OVERDRIVE"
    
    # Colors (Neon Palette)
    COLOR_BG = (10, 10, 20)
    COLOR_GRID = (30, 30, 50)
    COLOR_PLAYER = (0, 255, 255)      # Cyan
    COLOR_ENEMY = (255, 0, 128)       # Magenta
    COLOR_BULLET = (255, 255, 0)      # Yellow
    COLOR_PARTICLE = (255, 255, 255)  # White
    COLOR_TEXT = (255, 255, 255)
    COLOR_HUD = (0, 255, 100)         # Green
    
    # Gameplay
    PLAYER_SPEED = 300.0
    PLAYER_HEALTH = 5
    BULLET_SPEED = 600.0
    FIRE_COOLDOWN = 0.15
    ENEMY_BASE_SPEED = 150.0
    SPAWN_RATE_INITIAL = 1.0  # Seconds
    SPAWN_RATE_MIN = 0.2
    
    # Limits
    MAX_PARTICLES = 300
    MAX_ENEMIES = 60

# --- Utilities ---
def get_distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def normalize(vec):
    mag = math.hypot(vec[0], vec[1])
    if mag == 0: return (0, 0)
    return (vec[0] / mag, vec[1] / mag)

# --- Classes ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(50, 200)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.3, 0.6)
        self.max_life = self.life
        self.size = random.randint(2, 4)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.vx *= 0.95 # Drag
        self.vy *= 0.95

    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        if alpha < 0: alpha = 0
        # Simple fade via color approximation (pygame surf alpha is better but complex for one-shot)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(s, (self.x - self.size, self.y - self.size), special_flags=pygame.BLEND_ADD)

class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * Config.BULLET_SPEED
        self.vy = math.sin(angle) * Config.BULLET_SPEED
        self.radius = 4
        self.active = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Out of bounds
        if not (0 < self.x < Config.WIDTH and 0 < self.y < Config.HEIGHT):
            self.active = False

    def draw(self, surface):
        pygame.draw.circle(surface, Config.COLOR_BULLET, (int(self.x), int(self.y)), self.radius)
        # Glow
        pygame.draw.circle(surface, (200, 200, 0), (int(self.x), int(self.y)), self.radius + 2, 1)

class Enemy:
    def __init__(self, x, y, difficulty_mult):
        self.x = x
        self.y = y
        self.radius = 12
        self.speed = Config.ENEMY_BASE_SPEED * (1 + difficulty_mult * 0.1)
        self.active = True
        self.health = 1 + int(difficulty_mult / 2)

    def update(self, dt, player_x, player_y):
        # Chase
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

    def draw(self, surface):
        rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        pygame.draw.rect(surface, Config.COLOR_ENEMY, rect)
        pygame.draw.rect(surface, (255, 100, 100), rect, 2)

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = Config.PLAYER_SPEED
        self.health = Config.PLAYER_HEALTH
        self.last_shot = 0
        self.trail = [] # List of (x, y, time)

    def update(self, dt, keys, mouse_pos, mouse_pressed):
        # Movement
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
        
        # Normalize
        if dx != 0 or dy != 0:
            mag = math.hypot(dx, dy)
            dx /= mag
            dy /= mag
            
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        
        # Bounds
        self.x = max(self.radius, min(Config.WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(Config.HEIGHT - self.radius, self.y))
        
        # Trail
        self.trail.append((self.x, self.y, time.time()))
        if len(self.trail) > 20:
            self.trail.pop(0)
            
        # Shooting
        bullets = []
        now = time.time()
        if mouse_pressed[0] and now - self.last_shot > Config.FIRE_COOLDOWN:
            angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
            bullets.append(Bullet(self.x, self.y, angle))
            self.last_shot = now
            
        return bullets

    def draw(self, surface):
        # Trail
        for i, (tx, ty, t) in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)))
            size = int(self.radius * (i / len(self.trail)))
            if size > 0:
                s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*Config.COLOR_PLAYER, alpha//2), (size, size), size)
                surface.blit(s, (tx - size, ty - size), special_flags=pygame.BLEND_ADD)
        
        # Body
        pygame.draw.circle(surface, Config.COLOR_PLAYER, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius, 2)

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))
        pygame.display.set_caption(Config.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)
        self.big_font = pygame.font.SysFont("consolas", 48, bold=True)
        
        self.state = "MENU" # MENU, PLAYING, GAMEOVER
        self.reset_game()
        
    def reset_game(self):
        self.player = Player(Config.WIDTH // 2, Config.HEIGHT // 2)
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.score = 0
        self.start_time = time.time()
        self.last_spawn = 0
        self.shake = 0
        self.difficulty = 0
        
    def spawn_enemy(self, now):
        # Spawn rate scales with difficulty
        current_spawn_rate = max(Config.SPAWN_RATE_MIN, Config.SPAWN_RATE_INITIAL - (self.difficulty * 0.05))
        
        if now - self.last_spawn > current_spawn_rate:
            # Spawn at edge
            side = random.randint(0, 3)
            if side == 0: x, y = random.randint(0, Config.WIDTH), -20
            elif side == 1: x, y = Config.WIDTH + 20, random.randint(0, Config.HEIGHT)
            elif side == 2: x, y = random.randint(0, Config.WIDTH), Config.HEIGHT + 20
            else: x, y = -20, random.randint(0, Config.HEIGHT)
            
            # Ensure not too close to player
            if get_distance((x,y), (self.player.x, self.player.y)) > 200:
                self.enemies.append(Enemy(x, y, self.difficulty))
                self.last_spawn = now

    def add_particles(self, x, y, count, color):
        for _ in range(count):
            if len(self.particles) < Config.MAX_PARTICLES:
                self.particles.append(Particle(x, y, color))

    def add_shake(self, amount):
        self.shake = amount

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(Config.FPS) / 1000.0
            now = time.time()
            
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r:
                        if self.state == "GAMEOVER":
                            self.state = "MENU"
                        elif self.state == "MENU":
                            self.reset_game()
                            self.state = "PLAYING"
            
            if self.state == "MENU":
                self.draw_menu()
                pygame.display.flip()
                continue
                
            if self.state == "PLAYING":
                # Logic
                keys = pygame.key.get_pressed()
                mouse_pos = pygame.mouse.get_pos()
                mouse_pressed = pygame.mouse.get_pressed()
                
                # Difficulty scaling
                elapsed = now - self.start_time
                self.difficulty = int(elapsed / 10) # Increase every 10s
                
                # Player
                new_bullets = self.player.update(dt, keys, mouse_pos, mouse_pressed)
                self.bullets.extend(new_bullets)
                
                # Bullets
                for b in self.bullets:
                    b.update(dt)
                self.bullets = [b for b in self.bullets if b.active]
                
                # Enemies
                self.spawn_enemy(now)
                for e in self.enemies:
                    e.update(dt, self.player.x, self.player.y)
                    
                    # Collision Player
                    if get_distance((e.x, e.y), (self.player.x, self.player.y)) < e.radius + self.player.radius:
                        self.player.health -= 1
                        e.active = False
                        self.add_shake(10)
                        self.add_particles(self.player.x, self.player.y, 10, Config.COLOR_PLAYER)
                        if self.player.health <= 0:
                            self.state = "GAMEOVER"
                    
                    # Collision Bullets
                    for b in self.bullets:
                        if b.active and e.active and get_distance((e.x, e.y), (b.x, b.y)) < e.radius + b.radius:
                            e.active = False
                            b.active = False
                            self.score += 10
                            self.add_particles(e.x, e.y, 5, Config.COLOR_ENEMY)
                            self.add_shake(2)
                
                self.enemies = [e for e in self.enemies if e.active]
                if len(self.enemies) > Config.MAX_ENEMIES:
                    self.enemies = self.enemies[-Config.MAX_ENEMIES:]

                # Particles
                for p in self.particles:
                    p.update(dt)
                self.particles = [p for p in self.particles if p.life > 0]
                
                # Shake decay
                if self.shake > 0:
                    self.shake -= dt * 30
                    if self.shake < 0: self.shake = 0

                self.draw_game()
                
            elif self.state == "GAMEOVER":
                self.draw_game_over()
                
            pygame.display.flip()

    def draw_grid(self):
        for x in range(0, Config.WIDTH, 50):
            pygame.draw.line(self.screen, Config.COLOR_GRID, (x, 0), (x, Config.HEIGHT))
        for y in range(0, Config.HEIGHT, 50):
            pygame.draw.line(self.screen, Config.COLOR_GRID, (0, y), (Config.WIDTH, y))

    def draw_game(self):
        self.screen.fill(Config.COLOR_BG)
        self.draw_grid()
        
        # Apply Shake
        offset = (0, 0)
        if self.shake > 0:
            offset = (random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake)))
        
        # Draw Entities with offset
        for b in self.bullets:
            b.draw(self.screen)
        for e in self.enemies:
            e.draw(self.screen)
        self.player.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)
            
        # HUD
        self.draw_hud()
        
        # Shake effect (draw rect over everything)
        if self.shake > 0:
            s = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
            s.fill((0,0,0, int(20 * self.shake)))
            self.screen.blit(s, (0,0), special_flags=pygame.BLEND_ADD)

    def draw_hud(self):
        # Health
        health_str = "HEALTH: " + "❤" * self.player.health
        hs = self.font.render(health_str, True, Config.COLOR_HUD)
        self.screen.blit(hs, (20, 20))
        
        # Score
        score_str = f"SCORE: {self.score}"
        ss = self.font.render(score_str, True, Config.COLOR_TEXT)
        self.screen.blit(ss, (20, 50))
        
        # Time
        elapsed = time.time() - self.start_time
        ts = self.font.render(f"TIME: {elapsed:.1f}", True, Config.COLOR_TEXT)
        self.screen.blit(ts, (20, 80))
        
        # Instructions
        inst = self.font.render("WASD Move | CLICK Shoot | ESC Quit", True, (100, 100, 100))
        self.screen.blit(inst, (Config.WIDTH - 250, Config.HEIGHT - 30))

    def draw_menu(self):
        self.screen.fill(Config.COLOR_BG)
        self.draw_grid()
        title = self.big_font.render("NEON PROTOCOL", True, Config.COLOR_PLAYER)
        sub = self.font.render("Press R to Start", True, Config.COLOR_TEXT)
        self.screen.blit(title, (Config.WIDTH//2 - title.get_width()//2, Config.HEIGHT//2 - 50))
        self.screen.blit(sub, (Config.WIDTH//2 - sub.get_width()//2, Config.HEIGHT//2 + 10))

    def draw_game_over(self):
        self.draw_game() # Draw underlying game
        overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0,0))
        
        title = self.big_font.render("GAME OVER", True, Config.COLOR_ENEMY)
        score_txt = self.font.render(f"Final Score: {self.score}", True, Config.COLOR_TEXT)
        restart_txt = self.font.render("Press R to Restart", True, Config.COLOR_TEXT)
        
        self.screen.blit(title, (Config.WIDTH//2 - title.get_width()//2, Config.HEIGHT//2 - 50))
        self.screen.blit(score_txt, (Config.WIDTH//2 - score_txt.get_width()//2, Config.HEIGHT//2 + 10))
        self.screen.blit(restart_txt, (Config.WIDTH//2 - restart_txt.get_width()//2, Config.HEIGHT//2 + 50))

if __name__ == "__main__":
    try:
        g = Game()
        g.run()
    except Exception as e:
        print(f"Critical Error: {e}")
        pygame.quit()
        sys.exit(1)

