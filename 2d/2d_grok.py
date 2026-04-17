# game.py
import sys
import subprocess
import random
import math
from pygame.math import Vector2

# Minimal auto-install bootstrap for pygame
try:
    import pygame
except ImportError:
    print("pygame not found. Installing pygame-ce...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
    import pygame

pygame.init()

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON ROGUE DRONE")
CLOCK = pygame.time.Clock()

# Neon cyberpunk palette
BG_COLOR = (10, 0, 31)
GRID_COLOR = (0, 255, 220)
PLAYER_COLOR = (0, 255, 255)
ENEMY_COLORS = {"grunt": (255, 60, 60), "shooter": (255, 140, 0), "kamikaze": (255, 0, 200)}
PROJECTILE_COLOR = (180, 255, 255)
FONT = pygame.font.SysFont("consolas", 24)
BIG_FONT = pygame.font.SysFont("consolas", 72)

class Particle:
    def __init__(self, pos, vel, life, color, size=4):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self):
        self.pos += self.vel
        self.vel *= 0.96
        self.life -= 1

    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color, alpha) if len(self.color) == 3 else self.color
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.size, self.size), int(self.size * (self.life / self.max_life)))
        surface.blit(s, (self.pos.x - self.size, self.pos.y - self.size))

class Projectile:
    def __init__(self, pos, direction):
        self.pos = Vector2(pos)
        self.vel = direction * 18
        self.life = 40
        self.trail = []

    def update(self):
        self.trail.append(Vector2(self.pos))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.pos += self.vel
        self.life -= 1

    def draw(self, surface):
        # trail
        for i, p in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)))
            pygame.draw.circle(surface, (*PROJECTILE_COLOR, alpha), (int(p.x), int(p.y)), 3)
        # head
        pygame.draw.circle(surface, PROJECTILE_COLOR, (int(self.pos.x), int(self.pos.y)), 5)

class Enemy:
    def __init__(self, pos, etype):
        self.pos = Vector2(pos)
        self.etype = etype
        self.vel = Vector2(0, 0)
        self.health = {"grunt": 25, "shooter": 45, "kamikaze": 18}[etype]
        self.speed = {"grunt": 3.2, "shooter": 2.1, "kamikaze": 5.8}[etype]
        self.size = 18
        self.shoot_timer = 0 if etype == "shooter" else -1
        self.flash = 0

    def update(self, player_pos):
        direction = player_pos - self.pos
        if direction.length() > 0:
            direction = direction.normalize()
        self.vel = direction * self.speed
        self.pos += self.vel

        if self.etype == "shooter":
            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                # shooter fires back (simple)
                self.shoot_timer = 45

        if self.flash > 0:
            self.flash -= 1

    def draw(self, surface):
        c = ENEMY_COLORS[self.etype]
        if self.flash > 0:
            c = (255, 255, 255)
        # base
        pygame.draw.circle(surface, c, (int(self.pos.x), int(self.pos.y)), self.size)
        # inner detail
        pygame.draw.circle(surface, (20, 20, 40), (int(self.pos.x), int(self.pos.y)), self.size - 6)
        # corrupted lines
        pygame.draw.line(surface, (255, 255, 100), (int(self.pos.x - 10), int(self.pos.y - 8)),
                         (int(self.pos.x + 10), int(self.pos.y + 8)), 3)

class Player:
    def __init__(self):
        self.pos = Vector2(WIDTH / 2, HEIGHT / 2)
        self.vel = Vector2(0, 0)
        self.speed = 6.5
        self.health = 100
        self.max_health = 100
        self.fire_cooldown = 0
        self.thruster_particles = []
        self.angle = 0

    def update(self, keys, mouse_pos):
        self.vel = Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.vel.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.vel.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vel.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vel.x += 1

        if self.vel.length() > 0:
            self.vel = self.vel.normalize() * self.speed

        self.pos += self.vel
        # keep in bounds
        self.pos.x = max(40, min(WIDTH - 40, self.pos.x))
        self.pos.y = max(40, min(HEIGHT - 40, self.pos.y))

        # aim
        if mouse_pos != self.pos:
            self.angle = math.atan2(mouse_pos.y - self.pos.y, mouse_pos.x - self.pos.x)

        # thruster particles
        if self.vel.length() > 0:
            for _ in range(3):
                offset = Vector2(-math.cos(self.angle), -math.sin(self.angle)) * 18
                ppos = self.pos + offset + Vector2(random.uniform(-8, 8), random.uniform(-8, 8))
                pvel = -Vector2(math.cos(self.angle), math.sin(self.angle)) * random.uniform(4, 8)
                self.thruster_particles.append(Particle(ppos, pvel, 18, (0, 255, 255), 3))

        # update thrusters
        for p in self.thruster_particles[:]:
            p.update()
            if p.life <= 0:
                self.thruster_particles.remove(p)

    def shoot(self, mouse_pressed):
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
            return None
        if mouse_pressed:
            self.fire_cooldown = 5
            direction = Vector2(math.cos(self.angle), math.sin(self.angle))
            muzzle = self.pos + direction * 24
            # muzzle flash particle
            for _ in range(8):
                pvel = direction * random.uniform(8, 14) + Vector2(random.uniform(-3, 3), random.uniform(-3, 3))
                return Projectile(muzzle, direction), Particle(muzzle, pvel, 8, (255, 240, 100), 6)
        return None

    def draw(self, surface):
        # thrusters already drawn globally
        # drone body
        points = [
            self.pos + Vector2(math.cos(self.angle), math.sin(self.angle)) * 22,
            self.pos + Vector2(math.cos(self.angle + 2.3), math.sin(self.angle + 2.3)) * 16,
            self.pos + Vector2(math.cos(self.angle - 2.3), math.sin(self.angle - 2.3)) * 16,
        ]
        pygame.draw.polygon(surface, PLAYER_COLOR, points)
        # inner glow
        pygame.draw.polygon(surface, (255, 255, 255), points, 3)
        # rotor lines
        pygame.draw.line(surface, (180, 255, 255), self.pos, self.pos + Vector2(math.cos(self.angle + 1.57), math.sin(self.angle + 1.57)) * 14, 4)

class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.player = Player()
        self.projectiles = []
        self.enemies = []
        self.particles = []
        self.score = 0
        self.time_survived = 0
        self.wave = 1
        self.spawn_timer = 0
        self.screen_shake = 0
        self.state = "playing"  # playing, paused, game_over
        self.last_spawn_time = 0

    def spawn_enemy(self):
        side = random.choice(["left", "right", "top", "bottom"])
        if side == "left":
            pos = Vector2(-30, random.randint(50, HEIGHT - 50))
        elif side == "right":
            pos = Vector2(WIDTH + 30, random.randint(50, HEIGHT - 50))
        elif side == "top":
            pos = Vector2(random.randint(50, WIDTH - 50), -30)
        else:
            pos = Vector2(random.randint(50, WIDTH - 50), HEIGHT + 30)

        etype = random.choices(["grunt", "shooter", "kamikaze"], weights=[50, 30, 20], k=1)[0]
        if self.wave > 4 and random.random() < 0.3:
            etype = "kamikaze"
        self.enemies.append(Enemy(pos, etype))

    def update(self):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        mouse_pos = Vector2(pygame.mouse.get_pos())
        mouse_pressed = pygame.mouse.get_pressed()[0]

        self.player.update(keys, mouse_pos)

        # shooting
        shot = self.player.shoot(mouse_pressed)
        if shot:
            proj, flash = shot
            self.projectiles.append(proj)
            self.particles.append(flash)

        # update projectiles
        for p in self.projectiles[:]:
            p.update()
            if p.life <= 0:
                self.projectiles.remove(p)

        # update enemies
        for e in self.enemies[:]:
            e.update(self.player.pos)
            # enemy-player collision
            if (e.pos - self.player.pos).length() < e.size + 22:
                self.player.health -= 15 if e.etype == "kamikaze" else 8
                self.screen_shake = 12
                if e.etype == "kamikaze":
                    self.explode(e.pos, (255, 80, 200), 45)
                self.enemies.remove(e)
                if self.player.health <= 0:
                    self.state = "game_over"
                    self.explode(self.player.pos, (0, 255, 255), 70)
                    return

        # projectile-enemy collisions
        for p in self.projectiles[:]:
            for e in self.enemies[:]:
                if (p.pos - e.pos).length() < e.size + 6:
                    e.health -= 18
                    e.flash = 4
                    self.particles.append(Particle(p.pos, Vector2(0, 0), 12, (255, 240, 100), 5))
                    if p in self.projectiles:
                        self.projectiles.remove(p)
                    if e.health <= 0:
                        self.score += 100 if e.etype == "grunt" else 160 if e.etype == "shooter" else 220
                        self.explode(e.pos, ENEMY_COLORS[e.etype], 32)
                        self.screen_shake = max(self.screen_shake, 8)
                        self.enemies.remove(e)
                    break

        # spawning
        self.spawn_timer += 1
        spawn_interval = max(18, 55 - self.wave * 3)
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0
            for _ in range(1 + self.wave // 3):
                self.spawn_enemy()
            self.last_spawn_time = pygame.time.get_ticks()

        # time & wave progression
        self.time_survived += 1 / FPS
        if int(self.time_survived) % 10 == 0 and int(self.time_survived) > self.wave * 10:
            self.wave += 1

        # particles
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        # player thrusters already updated

    def explode(self, pos, base_color, count):
        for _ in range(count):
            vel = Vector2(random.uniform(-8, 8), random.uniform(-8, 8))
            life = random.randint(18, 34)
            size = random.randint(3, 7)
            self.particles.append(Particle(pos, vel, life, base_color, size))

    def draw_background(self):
        SCREEN.fill(BG_COLOR)
        # pulsing neon grid
        pulse = math.sin(pygame.time.get_ticks() / 180) * 30 + 80
        for x in range(0, WIDTH + 80, 80):
            alpha = int(pulse)
            color = (*GRID_COLOR, alpha)
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(s, color, (x, 0), (x, HEIGHT), 2)
            SCREEN.blit(s, (0, 0))
        for y in range(0, HEIGHT + 80, 80):
            alpha = int(pulse)
            color = (*GRID_COLOR, alpha)
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(s, color, (0, y), (WIDTH, y), 2)
            SCREEN.blit(s, (0, 0))

    def draw(self):
        self.draw_background()

        # shake offset
        shake_offset = Vector2(0, 0)
        if self.screen_shake > 0:
            shake_offset = Vector2(random.uniform(-self.screen_shake, self.screen_shake),
                                   random.uniform(-self.screen_shake, self.screen_shake))
            self.screen_shake *= 0.8
            if self.screen_shake < 0.5:
                self.screen_shake = 0

        # draw player thrusters
        for p in self.player.thruster_particles:
            p.draw(SCREEN)

        # draw projectiles
        for p in self.projectiles:
            p.draw(SCREEN)

        # draw enemies
        for e in self.enemies:
            e.draw(SCREEN)

        # draw player
        self.player.draw(SCREEN)

        # draw particles
        for p in self.particles:
            p.draw(SCREEN)

        # HUD
        # health
        bar_w = 300
        bar_h = 24
        fill = max(0, self.player.health / self.player.max_health)
        pygame.draw.rect(SCREEN, (40, 40, 40), (40, 40, bar_w, bar_h))
        pygame.draw.rect(SCREEN, (0, 255, 180), (40, 40, bar_w * fill, bar_h))
        pygame.draw.rect(SCREEN, PLAYER_COLOR, (40, 40, bar_w, bar_h), 3)

        # score
        score_text = FONT.render(f"SCORE {int(self.score)}", True, (255, 240, 100))
        SCREEN.blit(score_text, (WIDTH - score_text.get_width() - 40, 40))

        # time & wave
        time_text = FONT.render(f"TIME {int(self.time_survived)}s  WAVE {self.wave}", True, GRID_COLOR)
        SCREEN.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, 40))

        if self.state == "game_over":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            SCREEN.blit(overlay, (0, 0))
            go_text = BIG_FONT.render("DRONE OFFLINE", True, (255, 60, 60))
            SCREEN.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 100))
            final_score = FONT.render(f"FINAL SCORE {int(self.score)}", True, (255, 240, 100))
            SCREEN.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, HEIGHT // 2 + 20))
            restart_text = FONT.render("PRESS R TO REBOOT", True, (180, 255, 255))
            SCREEN.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 80))

        if self.state == "paused":
            pause_text = BIG_FONT.render("PAUSED", True, (180, 255, 255))
            SCREEN.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 40))

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "paused"
                        elif self.state == "paused":
                            self.state = "playing"
                    if event.key == pygame.K_r and self.state == "game_over":
                        self.reset()

            if self.state == "playing":
                self.update()

            self.draw()
            pygame.display.flip()
            CLOCK.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
