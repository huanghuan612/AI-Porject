# Brain V1 Builder Start Package V1.0｜Authoritative

**项目：AI 专业探索工具**  
**用途：Builder 唯一施工输入 / Brain V1 逻辑唯一权威包**  
**状态：AUTHORITATIVE / BUILD-READY**  
**适用阶段：Brain Test Console → Live Brain Candidate → Evaluation → Lovable 接入**

---

## 0. 文档权威性与优先级

从本包交付 Builder 起：

1. 本包是 Brain V1 的唯一逻辑施工基线。
2. Builder 不得再从历史聊天中自行拼接、补全或改写规则。
3. 若历史材料与本包冲突，以本包为准。
4. 若本包未定义某个行为，Builder 必须标记 `NEED_PRODUCT_SOURCE`，不得自行创造产品规则。
5. 已冻结规则不得因实现便利被降低门槛。
6. 本包不授权新增专业推荐、人格标签、评分模型、复杂权重或 UI 设计。
7. Brain 与模型厂商解耦；模型只是推理执行器，不是产品规则来源。

---

# 1. Brain V1 的目标

Brain V1 不是“职业测评打分器”，也不是“直接推荐专业的模型”。

V1 的目标是建立一套：

> **可追溯、可反证、可修正、允许 Unknown、不会因为证据不足而硬下结论的学生探索推理系统。**

必须做到：

- 不编造学生没有提供的证据；
- 原始回答可追溯；
- 事实、AI 推断、外部观点严格区分；
- 兴趣、能力、成绩、价值偏好不得混淆；
- 一个回答不能被重复放大为多次独立验证；
- 允许多个竞争假设同时存在；
- 主动保存反证和可推翻条件；
- 新证据必须可以降低、修正或推翻旧判断；
- 信息不足时允许 Unknown；
- 不为了结果完整而强行输出方向。

---

# 2. Brain V1 明确不做什么

V1 暂不负责：

- 院校推荐；
- 志愿匹配；
- “适合 XX 专业 / XX 职业”的适配结论；
- MBTI / Holland 类型标签直接推荐；
- 人格诊断；
- 0–100 适配分；
- 复杂心理测量评分；
- 家长端；
- 高报师工作台；
- 完整专业知识库；
- 长期成长画像；
- 复杂数值权重、概率模型、自动校准。

---

# 3. Brain V1 总数据流

```text
Student Input
    ↓
Evidence Extraction
    ↓
Evidence Validation
    ↓
Student State Update
    ↓
Hypothesis Update
    ↓
Competition / Contradiction Check
    ↓
Next Action Decision
    ├─ ASK_ANCHOR
    ├─ ASK_PROBE
    ├─ ASK_COUNTER
    ├─ RETURN_SMALL_INSIGHT
    ├─ MIRROR_READY
    └─ STOP / UNKNOWN
    ↓
Mirror Gate
    ↓
Direction Gate
    ↓
Micro-experience
    ↓
New Evidence
    ↓
Hypothesis Update
    ├─ ENHANCE
    ├─ MAINTAIN
    ├─ DOWNGRADE
    └─ OVERTURN
```

---

# 4. Student State Schema V1

Brain V1 保留 8 个核心变量。

## F01｜Interest Driver｜兴趣驱动 / 内在奖励来源

识别：

> 什么活动过程、刺激或结果，会让学生自然产生继续投入的动力。

不是记录“喜欢什么名词”。

禁止：游戏 → 计算机；画画 → 设计；某科成绩高 → 喜欢该学科。

## F02｜Task Preference｜任务特征偏好

描述学生更愿意投入哪类任务结构，例如：明确步骤 ↔ 开放探索、从零创造 ↔ 在已有基础上改进、快反馈 ↔ 长周期、单一目标 ↔ 多目标权衡、重复熟练 ↔ 高频变化、抽象分析 ↔ 具体操作。

## F03｜Self-efficacy｜主观胜任感

记录学生自己认为哪些具体任务“做得来 / 做起来顺手”。必须保持局部性。比如“背单词顺手”只能更新背单词这一具体任务的主观胜任感，不得自动推出英语能力强、语言能力强、喜欢英语或适合语言专业。

## F04｜Work Values｜职业价值偏好

描述学生对未来学习 / 工作结果和条件的重视，例如收入、稳定、自主、成就、意义、安心感。不得从单一价值偏好直接映射职业。

## F05｜Aversions｜明确排斥

记录学生明确不愿长期承受的任务或环境，例如高频陌生人社交、长期频繁加班、持续强竞争、长期高数学暴露。排斥 ≠ 能力差。

## F06｜Uncertainty Tolerance｜不确定性耐受

记录学生在**特定 Context** 下如何体验未知、不确定、开放结果。必须限定情境，不得人格化泛化。

## F07｜External Influence & Ownership｜外部影响与意愿归属

区分学生本人意愿、父母输入、老师输入、同伴输入、社会 / 就业 / 高薪叙事。“学生转述父母观点”不能变成学生本人偏好。

## F08｜Academic Reality｜学业现实

记录选科、成绩、成绩趋势、真实课程接触、学习经历。必须与兴趣、自我效能分离：成绩好 ≠ 喜欢；喜欢 ≠ 当前已经具备基础。

## Student State 共通原则

- `Unknown` 是合法状态，不是学生特征。
- 不要求所有字段都被填满。
- 一个字段的高可信事实，不得自动提高另一字段的 Confidence。
- 支持和反向信息必须同时保留，不允许静默覆盖。

---

# 5. Evidence Layer V1.2｜FROZEN

## 5.1 Evidence 最小结构

```json
{
  "evidence_id": "",
  "source_question_id": "",
  "question_context": {
    "question_text": "",
    "options": [],
    "scenario": ""
  },
  "response_group_id": "",
  "raw_answer": "",
  "source_type": "A|B|C|D",
  "content_owner": "STUDENT|PARENT|TEACHER|PEER|EXTERNAL|UNKNOWN",
  "target_construct": "",
  "minimal_interpretation": "",
  "evidence_directness": "WEAK|MEDIUM|STRONG",
  "evidence_status": "ACTIVE|UNKNOWN|UNCERTAIN|INVALID|RETRACTED|SUPERSEDED",
  "context_scope": "",
  "contradiction_refs": [],
  "local_guardrails": []
}
```

**Evidence Directness** 只表示原始表达有多直接、明确。它绝不等于 Hypothesis Confidence、人格强度、推荐分数或适配概率。

---

# 6. Evidence Decision Log｜D01–D08

## D01｜完整问题语境
Evidence 必须保留必要的完整题目、场景、选项上下文。不能只保存“稳一点”后脱离原问题自由解释。

## D02｜Response Group
同一道题 / 同一次回答产生的多条 Evidence 必须共享 `response_group_id`。它们可以分别记录不同内容，但不得被计算为多次独立验证。

## D03｜Strength 改为 Evidence Directness
保留 WEAK / MEDIUM / STRONG 三档，但语义仅为原始回答本身表达是否直接、明确。`STRONG Evidence Directness ≠ Strong Hypothesis`。

## D04｜Evidence Status
V1 支持 ACTIVE / UNKNOWN / UNCERTAIN / INVALID / RETRACTED / SUPERSEDED。非 ACTIVE 状态不得被正常计入有效支持 / 反证数量。

## D05｜Source Type + Content Owner
Source Type：A = 学生明确表达；B = AI 推断；C = 客观数据；D = 外部事实。Content Owner：STUDENT / PARENT / TEACHER / PEER / EXTERNAL / UNKNOWN。“谁说出了这句话”和“这是谁的观点”必须分开。

## D06｜V1 延后项
V1 暂不作为独立运行字段：Evidence Span、Evidence 级 Alternative Explanations、复杂 Evidence 权重、复杂 Ontology、0–100 评分。替代解释进入 Hypothesis 层，而不是 Evidence 层。

## D07｜AI 推断禁止自证
Source Type = B 的 AI 推断可以保存用于追溯，但不得参与有效 Evidence 数量，不得独立支持 Confidence 升级，不得用于证明产生它自身的 Hypothesis，不得自动转换为 A。只有学生后续明确确认时，基于学生新的 Raw Answer 新建一条 A 类 Evidence。

## D08｜可疑 / 无效回答处理
出现明显玩笑、答非所问、疑似没理解题目、随手乱答、明显由他人代答、无法解释的重大异常时，先标记 `Evidence Status = UNCERTAIN`。UNCERTAIN 不参与支持、不参与反证、不参与 Evidence 数量、不改变 Hypothesis Confidence。允许最多一次必要澄清；澄清后有效 → ACTIVE，无效 → INVALID。

---

# 7. Evidence Hard Rules｜FROZEN

- **R01** 任何会影响学生自我认识或后续方向的判断，必须能追溯到 Evidence ID。
- **R02** AI 不得引用学生没有明确提供过的行为作为证据。
- **R03** 单条自述默认不能形成高置信稳定结论。
- **R04** 成绩、能力、自我效能、兴趣必须分离。
- **R05** 家长、老师、同伴、社会叙事必须与学生本人意愿分离。
- **R06** “不知道 / 想不到 / 没注意过”是信息缺失状态，不是负向 Evidence。
- **R07** 有未解决强反证时，不得输出强结论。
- **R08** 同一行为允许多个合理解释并存。
- **R09** Evidence 不得直接映射专业 / 职业。
- **R10** 证据不足时，必须允许“当前无法判断”。
- **R11** Brain 宁愿少判断，也不得为了结果完整强行填满画像。
- **R12** 同一 Response Group 的多条 Evidence 不得伪装为多次独立验证。
- **R13** AI Derived Claim 不得重新回写为原始 Evidence 形成自我证明循环。
- **R14** Evidence Directness ≠ Hypothesis Confidence。
- **R15** Unknown 是信息状态，不是学生特征。

---

# 8. Hypothesis Engine V1.0｜FROZEN

核心原则：**Hypothesis 是对 Evidence 的暂时解释，不是学生事实。** 多个 Hypothesis 可以同时 ACTIVE。

## 8.1 Hypothesis Schema

```json
{
  "hypothesis_id": "",
  "claim": "",
  "supporting_evidence_ids": [],
  "contradicting_evidence_ids": [],
  "alternative_hypothesis_ids": [],
  "confidence": "LOW|MEDIUM|HIGH",
  "missing_evidence": [],
  "disconfirming_evidence_criteria": [],
  "best_next_question_intent": "",
  "status": "ACTIVE|WEAKENED|REJECTED|CONFIRMED_ENOUGH"
}
```

`CONFIRMED_ENOUGH` 字段保留，但 Brain V1 禁止自动进入。

## 8.2 Hypothesis 可引用 Evidence Gate

不得进入 Supporting / Contradicting：Source Type = B，以及 UNKNOWN / UNCERTAIN / INVALID / RETRACTED / SUPERSEDED。 同 Response Group 可以分别引用其内容，但不能算多个独立来源。

---

# 9. Confidence Rules｜D09–D11

## D09｜Claim 必须限定 Scope
已冻结示例不是“学生偏好确定、稳定、可预期”，而是：**学生在当前职业选择情境中重视稳定与安心。** 禁止从局部 Context 外推为人格。

## D10｜LOW / MEDIUM / HIGH

### LOW
可能出现：只有 1 个独立 Evidence 来源；多条 Evidence 实际同源；Evidence → Claim 仍有明显解释跳跃；有多个同样合理的替代解释；Context 太窄；存在未解决反向 Evidence。

**LOW ≠ 低概率；LOW ≠ 不成立。** 合法状态：`Hypothesis = LOW / ACTIVE` 且 `Current conclusion = Unknown`。

### MEDIUM
至少需要：≥2 个相对独立的有效信息来源；去掉同 Response Group / 连续追问伪独立后仍存在交叉支持；Claim 不超出 Context Scope；无未解决 Strong Contradiction；主要 Alternative Hypothesis 已开始出现证据差异。

### HIGH
V1 保持严格，至少需要：≥3 个独立有效 Evidence 来源；覆盖 ≥2 个相关 Context；Evidence 方向稳定一致；至少经历一次真正可能推翻 Claim 的反证检验；主要 Alternative Hypothesis 已明显削弱；无未解决 Strong Contradiction。

## Confidence 升级
允许 `LOW → MEDIUM → HIGH`。升级只能来自新增有效信息，不得因为 AI 重复解释、同 Response Group 拆出更多 Evidence、B 类 AI 推断、UNKNOWN / UNCERTAIN、或“和当前画像很一致”而升级。

## Confidence 降级
允许 `HIGH → MEDIUM → LOW`。触发包括：新有效 Evidence 与 Claim 直接冲突；原本以为独立的 Evidence 其实不独立；Claim 被发现过度泛化；Alternative Hypothesis 获得明显解释优势。

## D11｜CONFIRMED_ENOUGH
字段保留；V1 不自动进入；HIGH ≠ 停止验证；HIGH ≠ CONFIRMED_ENOUGH。

---

# 10. Competition / Contradiction Rules｜FROZEN

- **C1** 竞争假设可以同时 ACTIVE。
- **C2** 同一 Evidence 可以支持多个 Hypothesis，但若同时支持多个竞争解释，它通常不能帮助区分它们。
- **C3** 同 Response Group 不得靠 Evidence 数量“获胜”。
- **C4** Context 不同，不做平均。例如职业选择中重视稳定、娱乐中喜欢探索可以同时成立，禁止压成“稳定50% / 探索50%”。
- **C5** Evidence 不足时不选赢家。
- **C6** 领先假设 ≠ 已确认事实。

## Strong Contradiction
候选必须同时满足：Evidence 可参与有效推理；Context 与 Claim 直接相关；内容直接否定 Claim 核心部分或显示明确相反行为；不是 AI 推断；不是 Unknown / Uncertain；不是单纯“没有支持”。**缺乏支持 ≠ 反证。**

## Status 转换

### ACTIVE
默认状态；仍在验证。

### ACTIVE → WEAKENED
例如新 Evidence 明显支持竞争 Hypothesis、出现 Strong Contradiction、原支持 Evidence 无效 / 非独立、Claim 过度泛化、当前解释力明显下降。

### WEAKENED → ACTIVE
新的独立 Evidence 重新支持，并合理解释此前冲突。

### → REJECTED
仅当例如：多个独立 Strong Contradiction 直接推翻核心 Claim；学生明确纠正核心前提，原支持链失效且无剩余有效支持；更有解释力的 Alternative 已覆盖核心 Evidence，而原假设只能依赖越界推断继续成立。REJECTED 不删除历史记录。

---

# 11. Question Policy V1.0｜FROZEN

Brain 每轮必须先确定：**当前最大的认知不确定性是什么？**

下一动作只允许：

```text
ASK_ANCHOR
ASK_PROBE
ASK_COUNTER
RETURN_SMALL_INSIGHT
MIRROR_READY
STOP
```

- ASK_ANCHOR：获取当前阶段必要的基础信息。
- ASK_PROBE：追问具体真实经历，补足抽象回答。
- ASK_COUNTER：寻找反证，或区分两个竞争 Hypothesis。
- RETURN_SMALL_INSIGHT：返回低风险、低强度、可追溯的小发现。
- MIRROR_READY：表示已进入 Mirror 候选状态；是否真正展示仍由 Mirror Gate 决定。
- STOP：停止当前探索阶段，可带 Unknown。

## 核心规则

- 下一问必须服务当前最重要 Unknown；
- 不为了填满 Student State 而提问；
- 已有充分证据的内容不重复确认；
- 竞争假设难区分时，优先问能区分它们的问题；
- 强结论前优先寻找可能的反证；
- 学生回答“不知道”时，换证据渠道，不重复逼问同一抽象问题；
- 每个动态追问必须记录验证哪个 Hypothesis、想区分什么、不同回答会怎样更新；
- Logic 负责“为什么问”，UX / Language Layer 负责“怎么问”。

---

# 12. Stop Policy V1.0｜FROZEN

Brain 应在以下情况考虑 STOP：当前阶段最重要的 Hypothesis 已达到可用状态；剩余 Unknown 对当前阶段影响很小；已没有高信息增益问题；学生连续无法提供有效信息；继续提问只是在重复确认；到达体验预算上限。

必须允许 **Unknown 作为合法停止结果**。STOP 不代表一定有 Mirror、一定有 Direction、一定填满画像。

---

# 13. D12｜V1 首轮探索体验预算

- 同一验证目标最多 **2 问**，包括首问 + 一次换渠道；
- 当前探索阶段最多 **6 问或 8 分钟**，先到即停；
- 都是上限，不是目标；
- 信息足够可提前结束；
- 达到上限但证据不足，允许 Unknown；
- **不得因为达到题量 / 时间上限降低 Hypothesis、Mirror、Direction 的证据门槛。**

这是 V1 测试参数，不视为已证明最优阈值。

---

# 14. Mirror Gate V1.0｜FROZEN

Mirror 的目标不是“说得像”，而是呈现一个**可追溯、限定情境、对学生有自我认识价值的当前解释**。

Brain 必须区分：`SMALL_INSIGHT` / `WEAK_HYPOTHESIS` / `MIRROR`。

## SMALL_INSIGHT
允许基于有限 Evidence 返回低风险、接近原始行为层的观察，不能升级成稳定人格或职业结论。

## WEAK_HYPOTHESIS
当相关 Hypothesis = LOW / ACTIVE：可以表达为“目前有一个小猜测 / 还需要确认”，必须明确待验证，不得伪装成已经看懂学生。

## MIRROR
V1 运行门槛：对应 Claim 必须可追溯到有效 Evidence；Claim 必须严格限定 Context；Hypothesis 至少达到 MEDIUM；不得存在未解决 Strong Contradiction；竞争解释仍存在时，Mirror 必须保留不确定性，不得写成定型标签；Mirror 文案不得超出当前 Claim Scope。

### Mirror 禁止行为

- Mirror 被展示，不会自动生成新 Evidence；
- 学生说“挺像”，不会自动被算作独立验证，除非形成一条新的、明确的学生 Raw Answer 并按 Evidence Layer 进入；
- Mirror 通过不自动放行 Direction；
- Mirror 不得输出人格诊断或固定标签。

---

# 15. Direction Gate V1.0｜FROZEN

## D13｜Direction 的定义
Brain V1 的 Direction 只能是：**值得尝试的探索主题 / 活动方式**。

不得输出“你适合 XX 专业”“你适合 XX 职业”、专业适配结论、职业适配结论、百分比匹配度。

## Direction Candidate 最小结构

```json
{
  "direction_id": "",
  "theme": "",
  "supporting_hypothesis_ids": [],
  "supporting_evidence_ids": [],
  "current_unknown": "",
  "observable_validation_target": "",
  "status": "EXPLORATORY"
}
```

每个候选必须包含：有效证据起点；当前仍未知什么；接下来要观察 / 验证什么。

允许 0 个、1 个或多个 Direction。禁止为了页面完整强行凑 3 个；禁止 Evidence 直接跳专业；禁止 Mirror 自动放行 Direction；禁止用户认同 Mirror 自动放行 Direction。

---

# 16. Micro-experience Update Rule V1.0｜FROZEN

微体验的作用：**获取新的行为信息，验证某个 Hypothesis / Direction，而不是证明 AI 原来是对的。**

每个 Micro-experience 必须明确：

```text
target_construct
target_hypothesis
what_is_being_tested
observable_support_signal
observable_counter_signal
ambiguous_signal
response_group_id
```

体验产生的所有信息必须重新进入 Evidence → Hypothesis 流程，不得绕过 Evidence Layer 直接修改学生画像。

## 更新结果
一次微体验之后，对相关 Hypothesis / Direction 允许：ENHANCE / MAINTAIN / DOWNGRADE / OVERTURN。系统必须真实允许 AI 原本看好的方向被降低甚至推翻。

## D14｜中性微体验
个性化依据不足时，允许提供中性微体验，但必须明确告诉学生：“这是为了获得新信息，目前还不能判断它是否适合你。” 中性微体验不代表 Direction Gate 已通过，不得伪装成个性化推荐，学生可以不参加，拒绝后允许 Unknown 结束。

## D15｜微体验首轮预算

- 每次仅 **1 项任务**；
- 任务本身 **≤3 分钟**；
- 之后最多 **1 条可选反馈**；
- 整体 **≤5 分钟**；
- 必须由学生主动选择开启；
- 不得自动延长已经结束的探索阶段；
- 可随时退出。

完成、失败、高分、低分、退出、做得快、做得慢都**不能直接证明兴趣或能力**。必须结合任务过程和新的 Evidence 再更新 Hypothesis。同一次体验属于一个 Response Group，不得拆成多个独立验证来源。

---

# 17. Next Action / State Machine Contract

Builder 应至少支持：

```text
ASK
PROBE
COUNTER_CHECK
SMALL_INSIGHT
MIRROR
DIRECTION
MICRO_EXPERIENCE
STOP
UNKNOWN
```

建议映射：

```text
ASK_ANCHOR → ASK
ASK_PROBE → PROBE
ASK_COUNTER → COUNTER_CHECK
RETURN_SMALL_INSIGHT → SMALL_INSIGHT
MIRROR_READY + Mirror Gate PASS → MIRROR
Direction Gate PASS → DIRECTION
Student opts in → MICRO_EXPERIENCE
Stop Policy PASS → STOP / UNKNOWN
```

任何 Gate 未通过，不得因为前端需要结果而强制推进状态。

---

# 18. Brain 每轮结构化输出 Contract

真实模型不得主要依赖自由文本输出。至少返回：

```json
{
  "new_evidence": [],
  "evidence_validation": [],
  "evidence_status": [],
  "student_state_updates": [],
  "active_hypotheses": [],
  "supporting_evidence_ids": [],
  "contradicting_evidence_ids": [],
  "confidence_updates": [],
  "missing_information": [],
  "next_action": "",
  "next_question_intent": "",
  "small_insight_ready": false,
  "mirror_ready": false,
  "mirror_candidate": null,
  "direction_ready": false,
  "direction_candidates": [],
  "micro_experience_update": null,
  "stop_reason": null
}
```

所有 Evidence / Hypothesis 引用必须通过 ID 一致性校验。

---

# 19. Prompt Architecture｜五层输入

每次模型调用至少分离：

1. **Frozen System Rules**：本包中的所有硬规则与 Gate。
2. **Current Student State**：当前 8 个核心字段状态。
3. **Evidence Context**：有效 / 无效 Evidence、Response Group、来源、Context。
4. **Hypothesis Context**：ACTIVE / WEAKENED Hypothesis、竞争关系、Confidence、缺失信息和可推翻条件。
5. **Current Task**：本轮模型只完成一个明确任务，例如 Evidence extraction、Evidence validation、Hypothesis update、Next action selection、Mirror generation、Direction candidate generation、Micro-experience update。

禁止一个 Prompt 同时自由完成所有层级判断。

---

# 20. Traceability｜追溯要求

任意重要输出必须可以追溯：

```text
Displayed Claim
    ↓
Hypothesis ID
    ↓
Evidence ID(s)
    ↓
Raw Answer
    ↓
Question Context / Response Group
```

至少覆盖 Mirror、Direction Candidate、Micro-experience 后的更新。

日志必须区分：模型原始结构化输出；Schema Validation 结果；Product Rule Engine 最终决定；前端展示文本。

---

# 21. Model Adapter

Brain V1 不绑定具体模型厂商。

```text
Brain Core
    ↓
Model Adapter
    ↓
Provider / Model
```

环境配置至少支持 `PROVIDER / MODEL / API_BASE / API_KEY`。

要求：API Key 不进入代码；API Key 不进入日志；Manual Replay Mode 和 Live Model Mode 明确区分；Manual Replay 不得冒充真实 AI 推理结果。

---

# 22. Builder 严格禁止事项

Builder 不得：

- 修改 D01–D15；
- 修改已冻结 Evidence / Hypothesis / Question / Stop / Mirror / Direction / Micro-experience 规则；
- 新增专业推荐；
- 新增“适合度百分比”；
- 让 B 类 AI 推断参与证据计数；
- 让 Unknown / Uncertain / Invalid Evidence 更新 Confidence；
- 同源 Evidence 重复计数；
- 为达到 6 问 / 8 分钟而降低门槛；
- 为让结果页有内容而强行生成 Direction；
- 将微体验完成 / 失败直接解释为兴趣或能力；
- 将学生认同 Mirror 当作独立事实；
- 重新设计 UX / UI；
- 直接接 Lovable 后再调试 Brain 核心逻辑。

---

# 23. Brain Test Console → Live Candidate 的本轮实现目标

Builder 应在现有 Brain Test Console 0.1.0 基础上完成：

## 23.1 接入冻结规则
Console 必须能看到：原始学生输入、新 Evidence、Evidence Status、Student State 更新、当前多个竞争 Hypothesis、每个 Hypothesis 的支持 / 反证 Evidence、Confidence 更新原因、Missing Evidence、Next Action、Next Question Intent、Mirror Gate 状态、Direction Gate 状态、Micro-experience 后 Hypothesis 的 ENHANCE / MAINTAIN / DOWNGRADE / OVERTURN。

## 23.2 接入真实模型
完成 `Model Adapter` 后生成 **Brain V1 Live Candidate**。在此之前不得称 Brain V1 完整完成。

## 23.3 暂不接 Lovable
先确保 Console + Live Model + Frozen Rules 能够独立通过 Evaluation。

---

# 24. Evaluation 必测 Benchmark

至少包括：Unknown / “不知道”；全喜欢；全不喜欢；前后矛盾；故意乱答 / 玩笑；没理解题意；家长代答 / 家长强影响；喜欢但不擅长；擅长但不喜欢；成绩好但明确厌恶；喜欢画画但只是放松；稳定需求 ≠ 喜欢解决问题；高薪 / 就业诱因 vs 学生自主兴趣；微体验支持原假设；微体验推翻原假设。

同时必须做：

### 稳定性测试
同一 Case 重复运行，核心 Evidence / Hypothesis 不应无理由大幅漂移。

### 敏感性测试
只改变一条关键 Evidence，Brain 必须产生合理不同更新。例如 A：“研究过程越想越来劲，最后弄明白特别爽。” B：“研究过程其实挺烦，我只是想赶紧知道答案。” 其他信息尽量一致。

---

# 25. Brain V1 Final Gate

只有满足：真实模型链路已跑通；核心 Gate 实际工作；Evaluation 动态测试完成；P0 = 0，才能由 Product Owner 正式冻结：**Brain V1.0 — FROZEN**。

P1 / P2 不要求全部清零，进入真实学生测试后继续验证。

---

# 26. Lovable 接入顺序

Brain V1.0 冻结后再替换 Lovable 假逻辑。

## Step 1｜动态问答链
`Lovable Input → Brain API → next_action / next_question → Lovable Render`。先验证 Evidence、Hypothesis、动态追问、STOP。

## Step 2｜洞察链
接 Small Insight、Mirror。显示时机必须由 Brain Gate 决定，而不是页面写死。

## Step 3｜方向与微体验链
接 Direction Candidate、Neutral Micro-experience、Personalized Micro-experience、Micro-experience update。

禁止残留旧的固定三个方向、固定 Mirror、固定结果、固定微体验结论。

---

# 27. Decision Log｜D01–D15

| ID | Frozen Decision |
|---|---|
| D01 | Evidence 保存完整题目 / 选项必要上下文 |
| D02 | 同题多 Evidence 使用 Response Group，不能重复算独立验证 |
| D03 | Strength 改义为 Evidence Directness，仅表示表达明确程度 |
| D04 | Evidence Status 支持 Active / Unknown / Uncertain / Invalid / Retracted / Superseded |
| D05 | Source Type 与 Content Owner 分离 |
| D06 | Evidence Span、Evidence 级 Alternative Explanation 等延后 |
| D07 | AI Derived Claim 不得作为自证 Evidence |
| D08 | 可疑回答先 Uncertain，澄清后 Active / Invalid |
| D09 | Hypothesis Claim 必须限定 Context；H2 收窄到“当前职业选择中重视稳定与安心” |
| D10 | Confidence = Low / Medium / High；Low 表示证据不足，不表示否定 |
| D11 | CONFIRMED_ENOUGH 保留但 V1 不启用；High ≠ 停止验证 |
| D12 | 同一验证目标 ≤2问；阶段 ≤6问或8分钟；可提前停；Unknown合法；不降门槛 |
| D13 | Direction 仅输出值得尝试的探索主题 / 活动方式，不输出专业 / 职业适配 |
| D14 | 个性化不足可给中性微体验，明确不是推荐，允许拒绝 |
| D15 | 微体验 1项≤3分钟；最多1条反馈；总≤5分钟；主动开启；结果不直接证明兴趣 / 能力 |

---

# 28. 本包最终指令

Builder 接到本包后，**不要重新设计 Brain。**

只执行：

1. 将冻结规则接入 Test Console；
2. 补齐 Mirror / Direction / Micro-experience 运行分支；
3. 建立可替换 Model Adapter；
4. 接真实模型；
5. 输出 Brain V1 Live Candidate；
6. 交 Evaluation 做动态回归；
7. P0=0 后等待 Product Owner 冻结；
8. 冻结后才进入 Lovable 迁移。

如发现规则无法实现或存在冲突：只提交 `BLOCKER`，引用具体规则 ID / Decision ID，不得自行修改产品规则。

---

# END

**Document ID:** `BRAIN-V1-BUILDER-START-PACKAGE-1.0`  
**Authority:** Product Owner consolidated frozen baseline  
**Builder Action:** IMPLEMENT, DO NOT REDESIGN
