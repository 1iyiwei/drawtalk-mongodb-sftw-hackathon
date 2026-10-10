# Ideation

[Google Gemini](https://share.google/aimode/8N2fk7XDsH9qHm7WX)

The Build the Future: MongoDB x Cerebral Valley Hackathon is taking place this weekend as part of SF Tech Week. This event provides an incredible canvas for your unique technical intersection of computer graphics, human-computer interaction (HCI), and machine learning—especially given your recent focus on large language models (LLMs), agentic structures, and application development. [1, 2]
The event details and strategic angles to consider for your project configuration are detailed below.
[Rich media excluded from paste]
## Event Logistics & Details

| Attribute | Details |
|---|---|
| Event Name | Build the Future: MongoDB x Cerebral Valley Hackathon |
| Date & Time | Sunday, October 11, 2026 from 9:00 AM to 8:00 PM PDT |
| Location | SHACK15 (Suite 201, Ferry Building, San Francisco, CA 94111) |
| Theme / Focus | Harness Engineering & Model Wrangling[](https://cerebralvalley.ai/e/mongodb-sftw-hackathon): Building persistent, adaptive, and self-evolving AI agent memory infrastructure. |
| Core Tooling | MongoDB Atlas, Vector Search, and Agentic Memory tools. |
| Prizes | $15,000 in cash prizes awarded across three final teams. |
| Format & Capacity | Fully in-person. Max team size is 4. Application/approval required. Food and drinks are included. |

## Weather & Preparation
The weather in the SF Bay Area remains ideal for an indoor-outdoor venue like the Ferry Building, showing typical mild, clear-to-partly-cloudy October conditions. Because SHACK15 sits right over the water, it is best to bring layers for the morning and evening breeze along the Embarcadero. [3, 4]
------------------------------
## Strategic Project Formulations for Li-Yi Wei
Given the theme focuses on persistent context engineering and persistent memory, you can bypass heavy model training and use your PyTorch/Python framework strengths alongside LLM application orchestration to stand out. [1, 5, 6]
## 1. Controllable Graphic Design & Storyboarding Memory

*
* The Concept: An AI-driven storyboarding agent that adapts to an illustrator's multi-turn spatial feedback.
* How it works: The user moves objects or sketches variations (leveraging human-in-the-loop interaction patterns). The application captures the delta of these visual states, converting canvas positions and text-guided dynamic updates into contextual memory vectors.
* MongoDB Role: MongoDB Atlas handles the multi-turn session trajectory. The agent uses persistent context to remember preferred user styling rules across distinct scenes without blowing past its raw token windows.
*

## 2. Self-Evolving Multi-Modal Canvas Engine

*
* The Concept: An application framework where an LLM acts as an layout engine that continuously self-corrects its multi-modal rendering code based on user usage.
* How it works: As a developer interactively edits a vector graphic or animation sequence using natural language blocks, a backend agent observes successful and discarded rendering versions.
* MongoDB Role: It logs granular rollout histories (inputs, code drafts, user feedback loops). Successful structural designs are embedded into MongoDB Vector Search as high-advantage memory patterns, enabling the agent to learn the user's specific structural syntax over long-term iterations.
*

## 3. Trajectory & Asset Version Control Tracker

*
* The Concept: A nonlinear revision and memory management hub tailored for complex asset pipelines (e.g., 3D meshes or layered canvas systems).
* How it works: The agent dynamically stores state descriptions, node dependencies, and structural execution graphs. When users bounce between creative branches, the agent parses intent and references past parallel asset trees.
* MongoDB Role: MongoDB’s flexible document model natively maps complex multi-branch revision graphs, while Vector Search correlates past prompt sequences with corresponding visual asset milestones.
*

Would you like me to dive deeper into building out a system architecture diagram for one of these directions, or do you want to outline a pitch template optimized for the judges panel?

[1] [https://www.tech-week.com](https://www.tech-week.com/calendar/sf/events/the-harness-engineering-and-model-wrangling-hackathon-88af9295-2ccc-4bf8-bbc5-1eb223817051)
[2] [https://partiful.com](https://partiful.com/e/SLKAGzRbpQ3d3TGM8pAU)
[3] [https://wu-next-prod.wunderground.com](https://wu-next-prod.wunderground.com/history/monthly/us/ca/emerald-hills/KCAEMERA23/date/2026-10)
[4] [https://veteransonesource.app](https://veteransonesource.app/sanramonca/)
[5] [https://cerebralvalley.ai](https://cerebralvalley.ai/e/mongoDB-hackathon)
[6] [https://cerebralvalley.ai](https://cerebralvalley.ai/e/mongodb-sftw-hackathon)


------------------------------
The project must build in **at least one** of the following problem statements:

### **Statement 1: Recursive Harnessing**

Build a self-improving agent harness that automatically evolves its own architecture: updating rules, context policies, guardrails, tool access, and more. How can agents dynamically adapt their entire environment to fit a specific user, task, or use case?

### **Statement 2: Long Horizon Engineering**

The highest-value agentic work spans hours, days, or weeks. Build a harness that sustains coherent memory across billions of tokens in one session, relentlessly optimizes toward long-term goals, and learns from hard metric signals to complete traditionally difficult tasks.

------------------------------
To align perfectly with the judges' specific criteria, your project should marry your deep background in human-in-the-loop interaction, spatial/visual authoring, and multi-agent orchestration with the core architectural demands of these problem statements.
Below are two tailored architectural concepts mapped to your exact technical strengths (Python/PyTorch, LLM application routing, and interactive creative tool design), leveraging MongoDB Atlas as the foundational infrastructure.

------------------------------
## Concept A: The Self-Evolving Creative Canvas (Statement 1)
Problem Statement 1: Recursive Harnessing
Build a self-improving agent harness that automatically evolves its own architecture to adapt its environment to a specific user, task, or use case.
## 🛠️ Technical Formulation
You can build a web-based, direct-manipulation layout or sketching canvas where a multi-agent system serves as the interface engine. Instead of hardcoding how the AI reacts to the user's text prompts, rough drawings, and layout adjustments, the agentic harness dynamically modifies its own execution rules, tool priority, and guardrails based on the user's implicit behavior.

[ User Interaction ] ──(Canvas Inputs)──> [ Interface Monitor Agent ]
                                                 │
                                           (Flags Friction / Success)
                                                 ▼
[ Canvas Engine Tooling ] <──(Updates)── [ Harness Optimizer Agent ]
         ▲                                       │
         └──────────(Vector Search Sync)─────────┴──> [ MongoDB Atlas ]
                                                      (Rules/State Collection)

## 📊 Implementation Blueprint

| Component | Function & Architecture |
|---|---|
| The Harness Adaptation Loop | The harness contains a system rule profile (e.g., balance between automated generation vs. strict manual control). If the system detects the user frequently hitting "undo" or manually shifting objects after a generative action, an optimization agent parses this friction and rewritten its own local system prompts and tool constraints. |
| MongoDB Atlas Infrastructure | Store the system's execution configurations and rule states as flexible JSON documents. Use MongoDB Atlas Vector Search to store semantic embeddings of past user interventions, letting the harness query prior sessions to fetch the optimal prompt architecture for similar creative tasks. |
| Why it Stands Out | It directly tackles "Recursive Harnessing" by letting an interface learn an individual designer's spatial grammar, changing its core operation policies dynamically without requiring an engineer to rewrite the code. |

------------------------------
## Concept B: Non-Linear Creative Pipeline Memory (Statement 2)
Problem Statement 2: Long Horizon Engineering
Build a harness that sustains coherent memory across long timelines, optimizes toward long-term goals, and learns from hard metric signals.
## 🛠️ Technical Formulation
Creative asset pipelines (like multi-scene storyboarding or generating coordinated visual worlds) involve long horizons with frequent branching, dead ends, and revisions. This project introduces a harness that manages an interactive world's generation over days or weeks, maintaining strict structural, visual, and behavioral consistency across thousands of asynchronous adjustments.

                  ┌──> Branch A: Photorealistic Style (Discarded)
[ Original Scene ]┼──> Branch B: Stylized Sketch (Active)
                  └──> Branch C: Dynamic Animation (Explored)
                         ▲
                         └─(Harness analyzes hard signals to preserve consistency)

## 📊 Implementation Blueprint

| Component | Function & Architecture |
|---|---|
| The Long Horizon Tracker | The harness tracks a hierarchical graph of the project state. It monitors multi-modal inputs (text prompts + directional motion paths) across extended periods, ensuring characters or environments generated in "Scene 10" still perfectly align with the constraints established in "Scene 1." |
| Hard Metric Signals | Implement hard feedback hooks: asset validation passes (e.g., layout resolution checks, layout overlap collisions, or user export/save actions). The harness treats "frequent exports" as positive reinforcement and "abandoned branches" as penalties, automatically refining its search/generation trajectory toward high-value states. |
| MongoDB Atlas Infrastructure | Utilize MongoDB's document model to natively store and query the highly non-linear, branching tree structures of the creative pipeline. Map episodic memory (past user attempts) and procedural memory (how a multi-step design goal was successfully achieved) directly to a unified Atlas backend. |
| Why it Stands Out | It provides an elegant solution to long-horizon context drift. Instead of drowning the LLM context window with thousands of historical steps, the harness strategically fetches historical milestones using episodic memory routing. |

------------------------------
## Proactive Next Steps
To give you a massive running start before the clock begins ticking on Sunday, we can map out a specific technical roadmap.
If you want, let me know:

* Which Problem Statement (1 or 2) resonates more with your target hackathon goals?
* Do you plan to build this as a pure command-line/API agent harness, or would you like to couple it with a lightweight interactive UI/canvas web app (e.g., using Streamlit, Gradio, or FastAPI)?

I can help you draft a technical stack definition or a submission pitch outline tailored to catch the attention of the judging panel.


------------------------------
We can combine both concept A and B together in one project: adaptive sketch-based authoring for a variety of media types, including images, vector graphics, and animations.

Start with a blank canvas, the user can use strokes to indicate various types of functionalities. For example, they can:

* Start with a drawing, and span out branches to generate variations
* Connect two or more drawings to produce creative hybrids
* Loop through multiple images that serve keyframes to create a video
* Many other possibilities defined by the individual users

The users can use natural languages to describe what they are doing, and the system will adapt and learn their strokes/gestures/annotations.

Such dynamic, adaptive, and individualized authoring interfaces are what I have been thinking about building, but given that the theme  of this hackathon is database and agent harness instead of generative image and video, I am not sure if it would be too heavy on the graphics side (without support from the provided hackathon infrastructure).

------------------------------
Your concern is completely valid, but this is actually your biggest competitive advantage. By shifting focus away from raw media generation and onto how the harness handles spatial logic, gesture parsing, and user-intent memory, you align perfectly with the theme without getting bogged down by rendering pipelines.
In a hackathon setting, you do not need to build complex graphics engines or train video generation models from scratch. You can use fast, off-the-shelf APIs (like Flux or Stable Diffusion for images, and basic Lottie/GIF compilation or existing lightweight models for video) as black-box "tools". The real engine of your project is the database-backed agent harness that translates sketch gestures into programmatic agent state changes.
Here is how you frame, architect, and execute this project so that it remains a database and agent harness masterpiece.

## Framing the Pitch: The "Spatial Command Language"
You are building an environment where sketches are code, and the agent harness is the compiler.

* Instead of the user typing out prompt strings over and over, their gestures create a living execution graph in MongoDB Atlas.
* The system is a direct-manipulation interface for long-horizon agent trajectories. The database does not just store the final pixel output; it stores the interaction semantics (gestures, connections, and language definitions) that govern the agents.

------------------------------
## Architectural Implementation Blueprint
To keep the project lightweight and highly aligned with the hackathon infrastructure, use this architecture:

 [ User Web Canvas ] ──(Strokes + Voice/Text)──> [ Context Parsing Engine ]
                                                          │
                                            (Resolves Intent vs History)
                                                          ▼
  [ Off-the-Shelf APIs ] <──(Triggers)── [ MongoDB Atlas Agent Engine ]
  (Flux, SVG Engine, etc.)                  (Saves Rules, Graphs, & Tokens)

| Component | How It Works Natively (Theme Alignment) | Lightweight Hackathon Shortcut |
|---|---|---|
| Statement 1: Recursive Harnessing (Gesture Learning) | When a user draws a new shape (e.g., a lightning bolt) and speaks: "This gesture means flash-interpolate between these two images," the agent harness dynamically updates its own environment policy. It writes a new tool schema definition and system rule on the fly. | The Shortcut: Don't build a complex computer vision model. Capture the stroke as an array of 2D coordinates [[x1,y1], [x2,y2]] or a bounding box. Pass the bounding box, the coordinate path, and the user's audio/text transcription to a fast LLM. The LLM updates a JSON prompt rule map in MongoDB Atlas. |
| Statement 2: Long Horizon Engineering (Branching Graphs) | Multi-modal design requires maintaining visual context over hours of revision. The database stores a non-linear state graph. If a user loops keyframes or branches a hybrid image, the harness reads the historical graph nodes out of MongoDB Atlas to inject exact structural context back into the generation prompts. | The Shortcut: Use a unified document schema to store canvas operations as nodes. When generating a hybrid or a video loop, the harness uses MongoDB Vector Search to pull semantic data from the parent nodes. It packages them into a clean prompt context window for your media generation API. |

------------------------------
## Lean MongoDB Document Schema (The Core Deliverable)
This schema proves to the judges that your database infrastructure is driving the entire multi-modal spatial workspace:

{
  "session_id": "session_li_yi_wei_2026",
  "user_defined_gestures": [
    {
      "gesture_name": "hybrid_bridge_line",
      "semantic_meaning": "Blend features of connected image nodes proportionally to line length",
      "harness_policy_patch": "Override image generation weights to use multi-source image conditioning"
    }
  ],
  "canvas_graph": {
    "nodes": [
      {
        "node_id": "canvas_node_01",
        "type": "image",
        "asset_url": "https://storage.api",
        "generation_prompt": "A minimalist architectural structure, vector art style"
      },
      {
        "node_id": "canvas_node_02",
        "type": "image",
        "asset_url": "https://storage.api",
        "generation_prompt": "A modern building merging into nature, vector art style"
      }
    ],
    "edges": [
      {
        "edge_id": "edge_loop_01",
        "type": "loop_gesture",
        "from_nodes": ["canvas_node_01", "canvas_node_02"],
        "resolved_action": "Compile keyframe sequence using frame interpolation API"
      }
    ]
  }
}

------------------------------
## Step-by-Step Implementation Strategy for Sunday

   1. The UI Canvas (Minimalist Frontend): Use a lightweight HTML5 canvas component wrapped in a FastAPI backend. The canvas only needs to track two inputs: a bounding box/stroke array and a simple text box (mimicking voice/natural language input).
   2. The Agent Orchestration (The Brain): Use Python to intercept the stroke and text data. Send them to an LLM instance acting as the "Harness Manager." The manager determines if the user is defining a rule (Statement 1) or executing a long-horizon action (Statement 2).
   3. The Database (The Hook): Write every single user gesture, updated rule profile, and node connection state directly into MongoDB Atlas. Use the database state to build the context windows for your media generation endpoints.

This setup prevents you from fighting complex rendering loops on Sunday. Instead, it lets you present a beautifully interactive, adaptive interface driven entirely by a self-improving database agent harness.
If you are interested, we can:

* Draft the precise system prompt structure for the Harness Manager that allows it to learn gestures on the fly.
* Build a comprehensive submission checklist to keep development hyper-focused on the database theme throughout the hackathon.

How would you like to refine this technical plan?

------------------------------
One possibility is to limit the graphics to be purely vector-graphics/code-based animation - basically, an agentic + MongoDB version of project DrawTalking/Narrative-Motion-Block where users use sketch and natural languages to animate their drawings. In the original DrawTalking project, all animations come from pre-baked library, and for this hackathon we can use an agent/LLM to create animations. (Related, I heard that project ChalkTalk, sister project from NYU, recently adopted AI generation.) The narrative motion block project uses LLM but not in a deep agent or harness way.

An agentic, MongoDB-backed adaptation of DrawTalking and Narrative-Motion-Block is the perfect scope for this hackathon. Focusing strictly on vector graphics (SVG) and code-based animations (HTML5 Canvas/JavaScript, CSS, or SVG attributes) completely solves your graphics pipeline worries.
Instead of fighting heavy video rendering or slow machine learning pipelines on Sunday, your agents will generate raw code and spatial instructions as text strings. This shifts 100% of the technical spotlight onto your agent harness architecture, long-horizon sequence tracking, and MongoDB storage optimization, which is exactly what the judges want to see.

------------------------------
## Structural Metamorphosis: Evolution of Your Past Work

| Project | original Paradigm | New Hackathon Agentic Paradigm |
|---|---|---|
| DrawTalking | Pre-baked animation library templates. | Generative Motion Compilers: The agent generates custom canvas/SVG animation logic on the fly based on natural language commands. |
| Narrative-Motion-Block | Shallow LLM scripting without long-term tracking. | Deep Branching Harness & Memory Graph: Every sketch interaction, rule adjustment, and timeline state is actively tracked, dynamically evaluated, and saved in MongoDB Atlas. |

------------------------------
## Project Architecture: DrawTalking-Agentic
Your core architecture acts as a compiler that translates natural language and custom gestures into executable vector motion code.

 [ Vector Canvas (HTML5) ] <───(Executes Code/SVG)─── [ Animation Runtime ]
        │                                                     ▲
(Strokes + Language)                                          │
        ▼                                                     │
 [ Intent Parser Agent ] ──(Queries Rules/Context)──> [ MongoDB Atlas Graph ]
        │                                            - Gesture Definitions
        ▼                                            - Timeline Milestones
 [ Code Synthesis Agent ] ───────────────────────────> - SVG State Trees

------------------------------
## Implementation Mapping to the Problem Statements## 1. Statement 1 (Recursive Harnessing): The Gesture Learning Engine

* How it works: When a user draws an arrow connecting a sketch of a bird to a sketch of a cage and says: "This gesture means the object flies toward and enters the target over 3 seconds," the agent harness updates its own capabilities.
* The Blueprint: The parser agent captures the line trajectory and user instructions. It then creates or edits an execution tool script (e.g., a JavaScript animation loop module) and stores this new behavior layout directly inside your MongoDB database. The environment effectively expands its own animation API library on the fly without a hardcoded re-deploy.

## 2. Statement 2 (Long Horizon Engineering): The Non-Linear Animation Graph

* How it works: Creating complex animation blocks requires managing non-linear states, object relationships, and nested timelines across hours of fine-tuning.
* The Blueprint: MongoDB Atlas hosts a single, living document graph that tracks the state of every vector asset on the screen, alongside a historical timeline tree. If a user says, "Remember how the cloud moved two scenes ago? Make the bird copy that exact wind velocity path," your long-horizon harness uses MongoDB Vector Search to scan the historical SVG attributes and animation scripts to extract and inject the correct motion attributes back into the current animation layer.

------------------------------
## Lean MongoDB Document Layout (The Core Deliverable)
This document structure demonstrates to the panel that your database is driving the spatial layout and motion engine:

{
  "project_id": "drawtalking_agentic_demo",
  "learned_gestures": [
    {
      "trigger_pattern": "connecting_arrow",
      "action_intent": "spatial_translation_interpolation",
      "runtime_js_template": "function animate(obj, target) { gsap.to(obj, {x: target.x, y: target.y, duration: 3}); }"
    }
  ],
  "timeline_graph": {
    "current_frame": 120,
    "elements": [
      {
        "element_id": "bird_svg",
        "raw_svg": "<path d='M10 20...' fill='blue'/>",
        "ancestry_node": "initial_sketch_01",
        "active_animations": [
          {
            "animation_id": "anim_fly_02",
            "generated_js_code": "gsap.to('#bird_svg', {rotation: 360, repeat: -1, ease: 'linear'});",
            "reward_metric_score": 1.0,
            "status": "approved_by_user"
          }
        ]
      }
    ]
  }
}

------------------------------
## Technical Shortcuts for Fast Hackathon Execution

* The Frontend Layer: Create a very simple web canvas using Python Streamlit (incorporating a custom drawable canvas element) or a quick FastAPI backend with a simple HTML5 sketch board.
* The Motion Engine: Use a proven JavaScript library like GSAP (GreenSock) or raw CSS Keyframes. Have your backend agent output pure GSAP animation code blocks (e.g., gsap.to("#circle", {x: 300, duration: 2})). The frontend simply executes this incoming text string using eval().
* Handling Hard Metric Feedback: When the user runs the animation script, tracking buttons like [Keep Motion] (+1 reward) or [Rewrite Code] (-1 penalty) send clean optimization flags to your database to help the harness improve its future code generation passes.

------------------------------
## Setting Up for a Sunday Win
This framework plays directly to your deep expertise in human-computer interface design while staying lightweight enough to build quickly over a single weekend.
If you are ready, I can help you draft:

* The exact System Prompt Rules for the Agent Engine so it knows how to read layout coordinates, parse sketch lines, and export valid JavaScript animation properties.
* A clean 3-Stage Pitch Outline designed to clearly communicate your technical architecture to judges from AWS, MongoDB, and Raindrop.

Where would you like to direct our focus next?


------------------------------
I wonder if it is possible to use only the services provided by MongoDB for the hackathon without any other AI services like outside LLMs or generative models for purity, or that would be too restrictive.

------------------------------
Attempting a "pure" MongoDB implementation is an excellent way to capture the judges' attention, but you must understand exactly where the line is drawn: MongoDB provides the state, memory, and orchestration layers, but it explicitly relies on external LLMs to do the actual "thinking" and text generation.
Building a pure stack is not restrictive—it is exactly how [MongoDB Atlas Agent Engine](https://www.mongodb.com/products/platform/atlas-agent-engine) is designed to function. [1]

------------------------------
## Understanding the MongoDB AI Stack
MongoDB built its brand-new [Atlas Agent Engine](https://www.mongodb.com/docs/agentengine/) to be completely open and model-neutral. It replaces the need for custom state management, separate vector databases, and custom guardrail plumbing, but it does not contain a native LLM. [1, 2, 3]
To build your agentic version of DrawTalking, you will combine MongoDB's native features with a standard cloud LLM or an open-source model running locally on your laptop. [2, 4]
Here is how you can configure a mathematically pure, zero-extra-vendor setup using only MongoDB's platform components alongside an LLM endpoint:

| Operational Dimension | How to Keep it Purely inside MongoDB | The External Component |
|---|---|---|
| Orchestration & State | Use the Atlas Agent Engine API[](https://www.mongodb.com/docs/agentengine/) to handle your Python agentic execution, session management, and runtime logic natively. | None |
| Agentic Memory Loops | Use MongoDB's built-in platform memory to automatically distill interactions into semantic, episodic, taxonomic, and procedural memories right inside your collections. | None |
| Vector Embedding & Reranking | Use MongoDB Voyage AI integration (which is natively baked into the platform) to embed your user's stroke paths and natural language metadata. | None |
| Governance & Guardrails | Use the Agent Engine Policy Engine to enforce structural system constraints and cost rules directly at the database layer. | None |
| The "Thinking" Engine | None | Connect an external model (such as Claude via Bedrock or GPT-4o) using open standards like the [Model Context Protocol (MCP)](https://www.mongodb.com/products/platform/atlas-agent-engine[](https://www.mongodb.com/products/platform/atlas-agent-engine) "The MongoDB Agent Platform |

------------------------------
## The Ultimate Purity Play: Local AI + MongoDB Atlas
If you want to achieve true technical isolation—meaning you do not rely on third-party cloud AI vendors (like OpenAI or Anthropic accounts)—you can use an Open-Source Local Model Strategy. [4]

   1. Database & Agent Layer: Deploy a free MongoDB Atlas Community Edition cluster locally or in the cloud.
   2. Local LLM Engine: Download an open-source model (such as Llama 3 or Qwen) onto your laptop using a tool like Ollama or Llama.cpp.
   3. The Pipeline: Your Python backend feeds canvas sketches and text inputs into Atlas Agent Engine to organize context and memory metadata. The engine then passes a minimized prompt payload to your local running LLM endpoint to generate the raw JavaScript/GSAP motion code blocks. [1, 2, 3, 4]

This architectural setup is a phenomenal narrative for your final presentation. It proves that your system can run securely and entirely on a developer's local machine, leveraging MongoDB as a unified context operating system. [2]
------------------------------
## Proactive Next Steps
Since the Atlas Agent Engine natively supports framework tools you likely already use, we can draft a starting point. [5]
If you'd like, let me know:

*
* Whether you prefer to connect your agent layer to an external API (like OpenAI/Anthropic) or configure it to point to a locally hosted model (via Ollama).
* Which agent orchestration package you are most comfortable with (LangGraph for Python is natively supported by the new platform). [1, 3, 4, 5]
*

I can help write a clean Python script draft using LangGraph and MongoDB Atlas Agent Engine to establish your core stroke-to-code compilation loop!

[1] [https://www.mongodb.com](https://www.mongodb.com/products/platform/atlas-agent-engine)
[2] [https://www.mongodb.com](https://www.mongodb.com/company/newsroom/press-releases/mongodb-launches-atlas-agent-engine-to-put-ai-agents-in-production-without-a-new-stack)
[3] [https://www.mongodb.com](https://www.mongodb.com/docs/agentengine/)
[4] [https://www.youtube.com](https://www.youtube.com/watch?v=ZdTNbziWxqE)
[5] [https://www.thelec.net](https://www.thelec.net/news/articleView.html?idxno=14365)
