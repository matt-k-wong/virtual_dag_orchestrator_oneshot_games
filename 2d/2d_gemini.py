# game.py
import sys
import math
import random
import time

try:
    import pygame
except ImportError:
    import subprocess
    print("Installing pygame-ce...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
    import pygame

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Palette
BG_COLOR = (11, 11, 26)
PLAYER_COLOR = (0, 255, 255)
BULLET_COLOR = (255, 255, 255)
UI_COLOR = (200, 200, 200)

ENEMY_SPECS = {
    "Scrapper": {"color": (255, 0, 255), "speed": 150, "hp": 30, "radius": 12, "score": 10},
    "Brute":    {"color": (255, 165, 0), "speed": 75,  "hp": 150, "radius": 22, "score": 50},
    "Interceptor":{"color": (255, 255, 0), "speed": 220, "hp": 10, "radius": 8, "score": 25}
}

class Particle:
    __slots__ = ['pos', 'vel', 'life', 'max_life', 'color', 'size']
    def __init__(self, x, y, color, speed_mult=1.0):
        self.pos = pygame.math.Vector2(x, y)
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(50, 300) * speed_mult
        self.vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * speed
        self.max_life = random.uniform(0.2, 0.6)
        self.life = self.max_life
        self.color = color
        self.size = random.uniform(2, 5)

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= 0.9  # friction
        self.life -= dt

    def draw(self, surface, offset):
        if self.life > 0:
            alpha = max(0, int((self.life / self.max_life) * 255))
            # Fast fading rect
            rect = pygame.Rect(int(self.pos.x - offset.x), int(self.pos.y - offset.y), int(self.size), int(self.size))
            pygame.draw.rect(surface, self.color, rect)

class Bullet:
    __slots__ = ['pos', 'vel', 'life', 'damage']
    def __init__(self, x, y, target_x, target_y):
        self.pos = pygame.math.Vector2(x, y)
        dir_vec = pygame.math.Vector2(target_x - x, target_y - y)
        if dir_vec.length() > 0:
            dir_vec.normalize_ip()
        else:
            dir_vec = pygame.math.Vector2(1, 0)
        self.vel = dir_vec * 1000
        self.life = 1.5
        self.damage = 15

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt

    def draw(self, surface, offset):
        start = self.pos - self.vel * 0.02
        pygame.draw.line(surface, BULLET_COLOR, start - offset, self.pos - offset, 3)

class Enemy:
    __slots__ = ['pos', 'type', 'color', 'speed', 'hp', 'max_hp', 'radius', 'score', 'flash_timer']
    def __init__(self, x, y, e_type):
        self.pos = pygame.math.Vector2(x, y)
        self.type = e_type
        spec = ENEMY_SPECS[e_type]
        self.color = spec["color"]
        self.speed = spec["speed"]
        self.hp = spec["hp"]
        self.max_hp = spec["hp"]
        self.radius = spec["radius"]
        self.score = spec["score"]
        self.flash_timer = 0.0

    def update(self, dt, player_pos, other_enemies):
        # AI: Move to player
        dir_vec = player_pos - self.pos
        if dir_vec.length() > 0:
            dir_vec.normalize_ip()
        
        # Soft separation
        sep = pygame.math.Vector2(0, 0)
        for other in other_enemies:
            if other is not self:
                dist_vec = self.pos - other.pos
                dist = dist_vec.length()
                if 0 < dist < self.radius * 2.5:
                    sep += dist_vec.normalize() / dist
        
        if sep.length() > 0:
            sep.normalize_ip()
            dir_vec = (dir_vec + sep * 0.5).normalize()

        self.pos += dir_vec * self.speed * dt
        if self.flash_timer > 0:
            self.flash_timer -= dt

    def draw(self, surface, offset):
        draw_color = (255, 255, 255) if self.flash_timer > 0 else self.color
        pygame.draw.circle(surface, draw_color, (int(self.pos.x - offset.x), int(self.pos.y - offset.y)), self.radius)
        pygame.draw.circle(surface, (0,0,0), (int(self.pos.x - offset.x), int(self.pos.y - offset.y)), self.radius - 2)

class Player:
    def __init__(self):
        self.pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
        self.vel = pygame.math.Vector2(0, 0)
        self.speed = 350
        self.radius = 14
        self.hp = 100
        self.shoot_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.is_dashing = False
        self.dash_time = 0.0
        
    def update(self, dt, keys):
        input_vec = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w]: input_vec.y -= 1
        if keys[pygame.K_s]: input_vec.y += 1
        if keys[pygame.K_a]: input_vec.x -= 1
        if keys[pygame.K_d]: input_vec.x += 1

        if input_vec.length() > 0:
            input_vec.normalize_ip()

        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0 and input_vec.length() > 0:
            self.is_dashing = True
            self.dash_time = 0.2
            self.dash_cooldown = 1.5
            self.vel = input_vec * 1200

        if self.is_dashing:
            self.dash_time -= dt
            if self.dash_time <= 0:
                self.is_dashing = False
        else:
            # Friction and normal movement
            self.vel = self.vel.lerp(input_vec * self.speed, 10 * dt)

        self.pos += self.vel * dt

        # Screen bounds
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))

        if self.shoot_cooldown > 0: self.shoot_cooldown -= dt
        if self.dash_cooldown > 0: self.dash_cooldown -= dt

    def draw(self, surface, offset):
        # Dash trail effect
        if self.is_dashing:
            pygame.draw.circle(surface, (0, 150, 150), (int(self.pos.x - self.vel.x*0.05 - offset.x), int(self.pos.y - self.vel.y*0.05 - offset.y)), self.radius)
        
        pygame.draw.circle(surface, PLAYER_COLOR, (int(self.pos.x - offset.x), int(self.pos.y - offset.y)), self.radius)
        # Core
        pygame.draw.circle(surface, (255, 255, 255), (int(self.pos.x - offset.x), int(self.pos.y - offset.y)), self.radius - 4)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Neon Grid: Rogue Override")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("impact", 72)
        self.font_small = pygame.font.SysFont("consolas", 24)
        
        self.state = "MENU" # MENU, PLAY, OVER
        self.score = 0
        self.high_score = 0
        
        self.reset()

    def reset(self):
        self.player = Player()
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.score = 0
        self.spawn_timer = 0.0
        self.spawn_rate = 1.5
        self.difficulty_timer = 0.0
        self.screen_shake = 0.0
        self.time_survived = 0.0

    def spawn_enemy(self):
        side = random.randint(0, 3)
        padding = 50
        if side == 0: x, y = random.randint(-padding, WIDTH+padding), -padding
        elif side == 1: x, y = WIDTH+padding, random.randint(-padding, HEIGHT+padding)
        elif side == 2: x, y = random.randint(-padding, WIDTH+padding), HEIGHT+padding
        else: x, y = -padding, random.randint(-padding, HEIGHT+padding)

        r = random.random()
        if r < 0.15: e_type = "Brute"
        elif r < 0.35: e_type = "Interceptor"
        else: e_type = "Scrapper"

        self.enemies.append(Enemy(x, y, e_type))

    def add_particles(self, x, y, color, count, speed_mult=1.0):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, speed_mult))
            if len(self.particles) > 300:
                self.particles.pop(0)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05) # Prevent spiral of death
            
            mx, my = pygame.mouse.get_pos()
            mouse_buttons = pygame.mouse.get_pressed()
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if self.state != "PLAY" and event.key == pygame.K_RETURN:
                        self.reset()
                        self.state = "PLAY"

            if self.state == "PLAY":
                self.update_play(dt, keys, mouse_buttons, mx, my)
            
            self.draw()

        pygame.quit()
        sys.exit()

    def update_play(self, dt, keys, mouse_buttons, mx, my):
        self.time_survived += dt
        self.difficulty_timer += dt
        
        if self.difficulty_timer > 5.0:
            self.spawn_rate = max(0.2, self.spawn_rate * 0.95)
            self.difficulty_timer = 0

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            self.spawn_timer = self.spawn_rate

        if self.screen_shake > 0:
            self.screen_shake -= dt * 10
            self.screen_shake = max(0, self.screen_shake)

        self.player.update(dt, keys)

        # Shooting
        if mouse_buttons[0] and self.player.shoot_cooldown <= 0:
            offset_mx = mx + (random.randint(-2, 2) if self.screen_shake else 0)
            offset_my = my + (random.randint(-2, 2) if self.screen_shake else 0)
            self.bullets.append(Bullet(self.player.pos.x, self.player.pos.y, offset_mx, offset_my))
            self.player.shoot_cooldown = 0.1
            self.screen_shake = max(self.screen_shake, 0.1)
            # Recoil particle
            self.add_particles(self.player.pos.x, self.player.pos.y, (0, 200, 255), 1, 0.3)

        # Update bullets
        for b in self.bullets[:]:
            b.update(dt)
            if b.life <= 0 or not (0 <= b.pos.x <= WIDTH and 0 <= b.pos.y <= HEIGHT):
                self.bullets.remove(b)

        # Update enemies & Collisions
        for e in self.enemies[:]:
            e.update(dt, self.player.pos, self.enemies)
            
            # Bullet collision
            for b in self.bullets[:]:
                if b.pos.distance_to(e.pos) < e.radius + 5:
                    e.hp -= b.damage
                    e.flash_timer = 0.05
                    self.add_particles(b.pos.x, b.pos.y, e.color, 3, 0.5)
                    self.bullets.remove(b)
                    if e.hp <= 0:
                        break

            if e.hp <= 0:
                self.score += e.score
                self.add_particles(e.pos.x, e.pos.y, e.color, 15 if e.type != "Brute" else 40, 1.5)
                if e.type == "Brute": self.screen_shake = max(self.screen_shake, 0.5)
                else: self.screen_shake = max(self.screen_shake, 0.2)
                self.enemies.remove(e)
                continue

            # Player collision
            if e.pos.distance_to(self.player.pos) < e.radius + self.player.radius:
                if not self.player.is_dashing:
                    self.player.hp -= 10
                    self.add_particles(self.player.pos.x, self.player.pos.y, (255, 0, 0), 20, 2.0)
                    self.screen_shake = 0.6
                    # Knockback
                    kb_dir = (self.player.pos - e.pos)
                    if kb_dir.length() > 0:
                        self.player.vel = kb_dir.normalize() * 800
                    e.hp = 0 # Destroy enemy on kamikaze
                    self.enemies.remove(e)
                    
                    if self.player.hp <= 0:
                        self.state = "OVER"
                        self.high_score = max(self.high_score, self.score)

        # Update particles
        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self):
        self.screen.fill(BG_COLOR)
        
        offset = pygame.math.Vector2(0, 0)
        if self.screen_shake > 0:
            shake_amt = int(self.screen_shake * 15)
            offset.x = random.randint(-shake_amt, shake_amt)
            offset.y = random.randint(-shake_amt, shake_amt)

        # Draw entities
        if self.state == "PLAY" or self.state == "OVER":
            for p in self.particles: p.draw(self.screen, offset)
            for b in self.bullets: b.draw(self.screen, offset)
            for e in self.enemies: e.draw(self.screen, offset)
            if self.player.hp > 0:
                self.player.draw(self.screen, offset)

        # Draw UI (Unaffected by camera offset)
        if self.state == "MENU":
            title = self.font_large.render("NEON GRID", True, PLAYER_COLOR)
            sub = self.font_small.render("Press ENTER to Initialize Override", True, UI_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 60))
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 20))
        
        elif self.state == "PLAY":
            score_txt = self.font_small.render(f"SCORE: {self.score}", True, UI_COLOR)
            hp_txt = self.font_small.render(f"INTEGRITY: {self.player.hp}%", True, (0, 255, 0) if self.player.hp > 30 else (255, 0, 0))
            self.screen.blit(score_txt, (20, 20))
            self.screen.blit(hp_txt, (20, 50))
            
            # Dash indicator
            if self.player.dash_cooldown <= 0:
                pygame.draw.rect(self.screen, (0, 255, 255), (20, 80, 100, 10))
            else:
                ratio = 1.0 - (self.player.dash_cooldown / 1.5)
                pygame.draw.rect(self.screen, (50, 50, 50), (20, 80, 100, 10))
                pygame.draw.rect(self.screen, (0, 150, 150), (20, 80, int(100*ratio), 10))

        elif self.state == "OVER":
            over_txt = self.font_large.render("SYSTEM FAILURE", True, (255, 0, 0))
            score_txt = self.font_small.render(f"FINAL SCORE: {self.score} | HIGH SCORE: {self.high_score}", True, UI_COLOR)
            sub = self.font_small.render("Press ENTER to Reboot", True, UI_COLOR)
            self.screen.blit(over_txt, (WIDTH//2 - over_txt.get_width()//2, HEIGHT//2 - 80))
            self.screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, HEIGHT//2))
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 40))

        pygame.display.flip()

if __name__ == "__main__":
    Game().run()
