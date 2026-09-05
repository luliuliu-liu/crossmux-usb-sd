#include "DinoRunActivity.h"

#include <Arduino.h>
#include <I18n.h>
#include <Logging.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>

#include "../../../components/UITheme.h"
#include "../../../fontIds.h"
#include "../GameUi.h"

namespace {
constexpr int kStatusFont = UI_12_FONT_ID;
}

void DinoRunActivity::onEnter() {
  Activity::onEnter();
  renderer.setOrientation(GfxRenderer::Orientation::LandscapeClockwise);
  resetGame();
  requestUpdate();
}

void DinoRunActivity::onExit() { Activity::onExit(); }

void DinoRunActivity::resetGame() {
  running_ = true;
  gameOver_ = false;
  lastStepMs_ = millis();
  elapsedMs_ = 0;
  speed_ = BASE_SPEED;
  dinoY_ = 0.0f;
  dinoVy_ = 0.0f;
  jumping_ = false;
  jumpHeld_ = false;
  obstacles_.clear();
}

void DinoRunActivity::startJump() {
  if (!running_ || gameOver_) return;
  // Allow a jump from the ground; air jumps are only a slight impulse so a
  // held button keeps you airborne a touch longer without making it trivial.
  if (dinoY_ == 0.0f) {
    dinoVy_ = JUMP_VELOCITY;
    jumping_ = true;
  } else if (jumpHeld_ && dinoVy_ > -2.0f) {
    dinoVy_ = JUMP_VELOCITY * 0.7f;
  }
}

void DinoRunActivity::updateStep() {
  if (!running_ || gameOver_) return;
  const uint32_t now = millis();
  if (now - lastStepMs_ < STEP_MS) return;
  lastStepMs_ = now;
  elapsedMs_ += STEP_MS;

  // Dino vertical physics.
  if (jumping_ || dinoY_ != 0.0f) {
    dinoVy_ += GRAVITY;
    dinoY_ += dinoVy_;
    if (dinoY_ >= 0.0f) {
      dinoY_ = 0.0f;
      dinoVy_ = 0.0f;
      jumping_ = false;
    }
  }
  jumpHeld_ = false;

  // Speed ramps with score (cap at 2.4× base so it stays playable on e-ink).
  speed_ = BASE_SPEED + static_cast<float>(score()) * 0.08f;
  if (speed_ > BASE_SPEED * 2.4f) speed_ = BASE_SPEED * 2.4f;

  // Move obstacles and drop ones past the left edge.
  for (auto& o : obstacles_) o.x -= o.speed;
  obstacles_.erase(std::remove_if(obstacles_.begin(), obstacles_.end(),
                                  [](const Obstacle& o) { return o.x + OBSTACLE_W < 0; }),
                   obstacles_.end());

  // Spawn new obstacles with a minimum gap from the last one.
  float rightmost = SPAWN_MARGIN;
  for (const auto& o : obstacles_) {
    if (o.x > rightmost) rightmost = o.x;
  }
  const uint32_t randVal = esp_random();
  if (rightmost < 800 + SPAWN_MARGIN && (randVal % 100) < 12 &&
      (obstacles_.empty() || rightmost < 800 - MIN_GAP)) {
    obstacles_.push_back(Obstacle{800.0f + SPAWN_MARGIN, speed_});
  }

  // Collision: axis-aligned box overlap with the dino (a small hitbox inset
  // keeps the game fair, matching the visual footprint).
  const int dinoLeft = DINO_X + 4;
  const int dinoRight = DINO_X + DINO_W - 4;
  const int dinoTop = GROUND_Y - DINO_H + static_cast<int>(dinoY_);
  const int dinoBottom = GROUND_Y;
  for (const auto& o : obstacles_) {
    if (o.x + OBSTACLE_W > dinoLeft && o.x < dinoRight && GROUND_Y - OBSTACLE_H < dinoBottom &&
        GROUND_Y > dinoTop) {
      gameOver_ = true;
      requestUpdate();
      return;
    }
  }
  requestUpdate();
}

void DinoRunActivity::handleInput() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    activityManager.goToApps();
  } else if (mappedInput.wasReleased(MappedInputManager::Button::Up) ||
             mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (gameOver_) {
      resetGame();
    } else {
      startJump();
      jumpHeld_ = true;
    }
    requestUpdate();
  }
}

void DinoRunActivity::loop() {
  if (gameOver_) {
    handleInput();
    return;
  }
  updateStep();
  handleInput();
}

void DinoRunActivity::drawTitleBar() {
  const int w = renderer.getScreenWidth();
  const int h = renderer.getScreenHeight();

  char scoreBuf[48];
  snprintf(scoreBuf, sizeof(scoreBuf), "%s %d", tr(STR_DINO_SCORE), score());
  renderer.drawText(kStatusFont, 20, 10, tr(STR_DINO_TITLE));
  const int tw = renderer.getTextWidth(kStatusFont, scoreBuf);
  renderer.drawText(kStatusFont, w - 20 - tw, 10, scoreBuf);
  renderer.drawLine(0, 36, w - 1, 36, true);
  (void)h;
}

void DinoRunActivity::drawScene() {
  const int w = renderer.getScreenWidth();

  // Ground strip.
  renderer.fillRect(0, GROUND_Y, w, GROUND_H, true);
  // Ground texture dashes (spaced by speed for a pseudo-scroll feel).
  const int dash = 24;
  const int offset = static_cast<int>(elapsedMs_ / 20) % dash;
  for (int x = -offset; x < w; x += dash) {
    if (x + 8 < 0 || x > w) continue;
    renderer.fillRect(x, GROUND_Y + 6, 8, 3, false);
  }

  drawDino();
  for (const auto& o : obstacles_) drawObstacle(o);
}

void DinoRunActivity::drawDino() {
  const int x = DINO_X;
  const int top = GROUND_Y - DINO_H + static_cast<int>(dinoY_);

  // Body.
  renderer.fillRect(x, top + 10, DINO_W, DINO_H - 10, true);
  // Head.
  renderer.fillRect(x + DINO_W - 8, top, 8, 12, true);
  // Eye (hollow).
  renderer.fillRect(x + DINO_W - 6, top + 3, 3, 3, false);
  // Legs (two blocks; the right one lifts while airborne for a running look).
  renderer.fillRect(x + 4, GROUND_Y - 8, 8, 8, true);
  const int legLift = jumping_ ? static_cast<int>(-dinoVy_) : 0;
  renderer.fillRect(x + DINO_W - 14, GROUND_Y - 8 + (legLift > 6 ? 3 : 0), 8, 8, true);
  // Tail.
  renderer.fillRect(x - 6, top + 18, 6, 8, true);
}

void DinoRunActivity::drawObstacle(const Obstacle& o) {
  const int x = static_cast<int>(o.x);
  const int top = GROUND_Y - OBSTACLE_H;
  // Cactus body + arms.
  renderer.fillRect(x, top, OBSTACLE_W, OBSTACLE_H, true);
  renderer.fillRect(x - 4, top + 6, 6, 10, true);
  renderer.fillRect(x + OBSTACLE_W - 2, top + 6, 6, 10, true);
  renderer.fillRect(x - 2, top + 4, 4, 4, true);
  renderer.fillRect(x + OBSTACLE_W - 2, top + 4, 4, 4, true);
}

void DinoRunActivity::drawGameOver() {
  const int w = renderer.getScreenWidth();
  const int h = renderer.getScreenHeight();

  renderer.fillRect(0, h / 2 - 52, w, 104, false);
  renderer.drawCenteredText(UI_12_FONT_ID, h / 2 - 30, tr(STR_DINO_GAME_OVER), true, EpdFontFamily::BOLD);

  char scoreBuf[64];
  snprintf(scoreBuf, sizeof(scoreBuf), "%s: %d", tr(STR_DINO_SCORE), score());
  renderer.drawCenteredText(UI_12_FONT_ID, h / 2 - 5, scoreBuf);

  const auto labels = mappedInput.mapLabels(tr(STR_BACK), tr(STR_RETRY), "", "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}

void DinoRunActivity::render(RenderLock&&) {
  renderer.clearScreen();
  drawTitleBar();

  if (gameOver_) {
    drawScene();
    drawGameOver();
  } else {
    drawScene();
  }

  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}