#!/usr/bin/env python3
"""
NEON DRONE SURVIVOR
A top-down twin-stick survivor shooter.
Controls: WASD to move, Mouse to aim, Click/Space to shoot
Press R to restart when dead, P to pause
"""

import sys
import math
import random
import time

# ============================================================================
# BOOTSTRAP: Auto-install pygame-ce or pygame
# ============================================================================
try:
    import pygame
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce", "-q"])
    import pygame

# ============================================================================
# CONSTANTS
# ============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors (Neon Cyberpunk Palette)
COLOR_BG = (13, 2, 33)  # Deep purple-black
COLOR_GRID = (26, 10, 62)  # Dark purple grid
COLOR_PLAYER = (0, 255, 255)  # Cyan
COLOR_PLAYER_BULLET = (0, 255, 255)  # Cyan
COLOR_ENEMY_BULLET = (255, 0, 64)  # Red
COLOR_SCRAMBLER = (255, 0, 128)  # Hot pink
COLOR_SPITTER = (255, 102, 0)  # Orange
COLOR_BRUTE = (255, 0, 0)  # Red
COLOR_TEXT = (255, 255, 255)  # White
COLOR_SCORE = (0, 255, 0)  # Green

# Powerup Colors
COLOR_RAPID = (255, 255, 0)  # Yellow
COLOR_SHIELD = (0, 255, 255)  # Cyan
COLOR_SPEED = (0, 255, 0)  # Green
COLOR_SPREAD = (255, 0, 255)  # Magenta

# Physics
PLAYER_SPEED = 300
PLAYER_FIRE_RATE = 0.2  # seconds between shots
PLAYER_BULLET_SPEED = 600
ENEMY_BULLET_SPEED = 300
PLAYER_HITBOX = 20
PLAYER_MAX_HEALTH = 5
INVINCIBILITY_TIME = 1.0

# Wave scaling
ENEMY_SPEED_SCALE_PER_WAVE = 0.05
MAX_ENEMY_SPEED_SCALE = 0.5
MAX_ENEMIES = 30
INITIAL_ENEMY_COUNT = 5
ENEMIES_PER_WAVE = 3

# Powerup settings
POWERUP_LIFETIME = 10.0
POWERUP_DROP_CHANCE = 0.15
RAPID_DURATION = 8.0
SPEED_DURATION = 6.0
SPREAD_DURATION = 10.0

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def distance(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

def normalize(vec):
    mag = math.sqrt(vec[0]**2 + vec[1]**2)
    if mag == 0:
        return (0, 0)
    return (vec[0] / mag, vec[1] / mag)

def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

# ============================================================================
# PARTICLE SYSTEM
# ============================================================================
class Particle:
    def __init__(self, x, y, vx, vy, color, size, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0
        self.shrink_rate = size / lifetime if lifetime > 0 else size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.98
        self.vy *= 0.98
        self.age += dt
        return self.age < self.lifetime

    def draw(self, surface):
        alpha = 255 * (1 - self.age / self.lifetime)
        current_size = max(1, self.size * (1 - self.age / self.lifetime))
        
        # Create surface for alpha blending
        if alpha < 255:
            temp_surf = pygame.Surface((int(current_size * 2 + 2), int(current_size * 2 + 2)), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, (*self.color, int(alpha)), 
                             (int(current_size + 1), int(current_size + 1)), int(current_size))
            surface.blit(temp_surf, (self.x - current_size - 1, self.y - current_size - 1))
        else:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(current_size))

class ParticleSystem:
    def __init__(self, max_particles=200):
        self.max_particles = max_particles
        self.particles = []

    def emit(self, x, y, count, color, speed=100, size=5, lifetime=0.5):
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            angle = random.uniform(0, 2 * math.pi)
            spd = speed * random.uniform(0.5, 1.5)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            self.particles.append(Particle(x, y, vx, vy, color, size * random.uniform(0.5, 1.0), lifetime))

    def emit_explosion(self, x, y, color, count=20):
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(100, 300)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            size = random.uniform(3, 10)
            lifetime = random.uniform(0.3, 0.8)
            self.particles.append(Particle(x, y, vx, vy, color, size, lifetime))

    def emit_trail(self, x, y, color):
        if len(self.particles) < self.max_particles:
            angle = random.uniform(0, 2 * math.pi)
            vx = math.cos(angle) * 20
            vy = math.sin(angle) * 20
            self.particles.append(Particle(x, y, vx, vy, color, 3, 0.3))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear

