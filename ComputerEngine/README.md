# HS Autonomous Computer Engine (HACE)

The **HS Autonomous Computer Engine (HACE)** powers real-world desktop and browser automation for the Electorn AI Companion.

## Architecture

```
ComputerEngine/
├── core/
│   ├── ComputerEngine.ts    # Master entry point & orchestration
│   ├── ActionPlanner.ts     # Natural language -> structured TaskPlan
│   ├── ActionExecutor.ts    # Physical controller dispatch & safety gating
│   ├── ActionValidator.ts   # Post-action verification & outcome evidence
│   ├── TaskManager.ts       # Execution loop (Plan -> Act -> Observe -> Verify)
│   └── TaskMemory.ts        # Persistent learned interaction patterns
├── controllers/
│   ├── MouseController.ts     # Bézier curve smoothing, clicking, scrolling
│   ├── KeyboardController.ts  # Speed-controlled typing, Unicode, shortcuts
│   ├── ClipboardController.ts # Context backup, restoration, Unicode clipboard
│   ├── ScreenController.ts    # Screen capture, scaling, region cropping
│   └── WindowController.ts    # Windows app lifecycle, focus, minimize/maximize
├── perception/
│   ├── ScreenAnalyzer.ts      # Multi-modal structured ComputerState perception
│   ├── UIElementDetector.ts   # UI automation tree & landmarks detection
│   ├── OCRProcessor.ts        # Text token & bounding box extraction
│   └── VisualGrounding.ts     # Natural language -> exact [x, y] coordinates
├── browser/
│   ├── BrowserAgent.ts        # Multi-step web research & document downloads
│   ├── BrowserController.ts   # Playwright-compatible browser actions
│   └── BrowserNavigator.ts    # Navigation stack, reload, tab management
├── safety/
│   ├── PermissionManager.ts   # Risk-level analysis & forbidden command rules
│   ├── ActionApproval.ts      # Interactive confirmation for high-risk steps
│   ├── EmergencyStop.ts       # Global instantaneous halt (<Ctrl+Alt+Esc>, "Stop!")
│   └── ActionValidator.ts     # Pre-execution boundary & parameter sanitizer
└── types/
    ├── ActionTypes.ts         # Atomic action schemas & results
    ├── TaskTypes.ts           # Plan, step status, and workflow definitions
    └── ComputerState.ts       # Real-time structured computer representation
```

## Security & Electron Preload Best Practices
- Implements strict `contextIsolation`.
- Exposes a restricted API surface rather than raw Node.js primitives to the renderer.
- Intercepts all destructive operations with `PermissionManager` and requires explicit approval for consequential actions.
- Global `EmergencyStop` immediately terminates mouse and keyboard simulation.
