# 内置 AI 决策记录

> 日期：2026-06-01 | 状态：已确认

## 决定

**暂不内置 AI 推理。** 当前架构保持 Ollama 可选模式，无 Ollama 时走 `scripted_fallback` 纯规则引擎。

## 理由

1. 现阶段素材仅 4 个动作（stand / walk_left / walk_right / sleep_cycle降级为stand），AI 的决策空间有限，规则系统已能覆盖
2. `decide_action` 是独立函数，接口清晰，将来换内置推理只改这一个函数
3. 瓶颈在素材不在决策——精灵图还是 Kitty 占位符，先解决素材

## 何时重评

素材丰富到 10+ 个动作后，规则系统维护成本超过 AI 集成成本时，重新评估。方案已预研：llama-cpp-python + Qwen2.5-0.5B-Instruct GGUF Q4_K_M（~350MB）。

## 当前行为

- Ollama 可用 → AI 决策
- Ollama 不可用 → `scripted_fallback`（4 条规则：夜晚/饥饿/活跃边缘/默认）
- 切换无缝，不 crash
