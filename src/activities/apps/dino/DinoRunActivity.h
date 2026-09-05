#pragma once

#include <cstdint>
#include <vector>

#include "../../Activity.h"

// Chrome-Dino-style endless runner for the e-ink screen.
//
// LandscapeClockwise orientation (800×480 logical). The dinosaur sits on the
// ground on the left; obstacles move in from the right. Up/Confirm makes the
// dino jump (gravity + terminal velocity). Collision ends the run; score is
// time survived, and speed ramps up slowly. Back exits to the Apps menu.
//
// Stateless toy: no SD persistence, mirroring the CellularGameActivity pattern.
// The framebuffer is cleared and redrawn every step, so the game relies on
// FAST_REFRESH and a modest step interval rather than partial updates.
class DinoRunActivity final : public Activity {
 public:
  DinoRunActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("DinoRun", renderer, mappedInput) {}
  ~DinoRunActivity() override = default;

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  // Game constants (logical 800×480 landscape).
  static constexpr int GROUND_Y = 420;         // top of ground strip
  static constexpr int GROUND_H = 30;
  static constexpr int DINO_X = 90;
  static constexpr int DINO_W = 30;
  static constexpr int DINO_H = 40;
  static constexpr int DINO_GROUND_TOP = GROUND_Y - DINO_H;  // dino feet on ground
  static constexpr int OBSTACLE_W = 18;
  static constexpr int OBSTACLE_H = 34;
  static constexpr int SPAWN_MARGIN = 120;     // new obstacle spawns right of screen
  static constexpr int MIN_GAP = 220;          // min spacing between obstacles (px)

  static constexpr float GRAVITY = 0.5f;       // px per step^2
  static constexpr float JUMP_VELOCITY = -9.0f;
  static constexpr int MAX_JUMP_H = 70;
  static constexpr uint16_t STEP_MS = 60;      // one game step
  static constexpr float BASE_SPEED = 3.4f;    // obstacle speed (px/step)

  struct Obstacle {
    float x;      // left edge
    float speed;  // px per step
  };

  bool running_ = false;
  bool gameOver_ = false;
  uint32_t lastStepMs_ = 0;
  uint32_t elapsedMs_ = 0;   // run time for score
  float speed_ = BASE_SPEED;

  // Dino vertical state. yTop measures the dino's top edge relative to the
  // ground: 0 on the ground, negative while airborne.
  float dinoY_ = 0.0f;
  float dinoVy_ = 0.0f;
  bool jumping_ = false;
  bool jumpHeld_ = false;

  std::vector<Obstacle> obstacles_;

  void resetGame();
  void startJump();
  void updateStep();
  void handleInput();
  void drawScene();
  void drawDino();
  void drawObstacle(const Obstacle& o);
  void drawTitleBar();
  void drawGameOver();
  int score() const { return static_cast<int>(elapsedMs_ / 1000); }
};