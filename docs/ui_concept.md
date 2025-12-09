# UI Concept: Communication Runtime Console

## Purpose and Audience
- Power dashboard for embedded and industrial engineers to orchestrate firmware workflows, protocol channels, and live execution traces with low cognitive load.
- Supports both YAML workflow authoring and visual state machine editing for XMODEM, Modbus, UART/TCP pipelines, and firmware flashing tasks.

## Visual Language
- Dark navy base with subtle grid; glassmorphism panels with soft rounded corners and light blur.
- Accents: neon cyan for primary actions and highlights; soft violet for secondary focus; desaturated green (success), amber (warning), red (error).
- High contrast, minimal clutter, crisp edges with gentle depth and glow on active/selected items.
- Typography: modern sans (SF Pro or Inter) for UI, monospace for raw data/log payloads; bold headings, medium labels, regular body.

## Layout Blueprint (Responsive)
- Left sidebar nav (collapsible): Dashboard, Workflow Studio, YAML Editor, Channels Manager, Protocol Drivers, Execution Logs, Settings, Device List.
- Center main canvas: state machine visual editor with zoom/pan; shows nodes, connectors, execution trace.
- Right properties panel: inspector for selected node/channel; YAML snippet preview with apply/reset; validation messages inline.
- Bottom logs/monitoring bar: resizable, tabbed (Console, UART, TCP, Actions); sticky filters and raw hex view.
- Panels are resizable; collapse controls on sidebar and properties panel for focus mode.

## Canvas Interaction (Workflow Studio)
- Node types: Wait for UART RX, XMODEM Receive, Modbus Read/Write, Check CRC, Flash Write, Jump to App, Delay, Condition Branch, Error Handler, Timeout Handler.
- Drag-and-drop from Node Library; snap-to-grid; connectors with arrowheads; hover highlights; pulsing glow on active node.
- Execution trace: animated edge highlighting along current path; breadcrumb of last events; quick filter by state/channel.
- Zoom controls with +/- buttons and scroll; minimap toggle in corner.

## Left Panel: Node Library
- Categorized groups: Wait Nodes, IO Nodes, Protocol Nodes, Control Flow, Error Handling, Utilities.
- Search box with fuzzy match; each item shows short tooltip (e.g., "XMODEM Receive: stream firmware blocks over selected channel").
- Node cards show small icon, name, brief description, protocol tags.

## Right Panel: Properties Inspector
- Sections: Summary (name, type, status), Channel binding (dropdown, baudrate/host/port), Timing (timeout, delay), Protocol options (CRC, retries, block size), Conditions (expressions), Error handling (fallbacks), YAML snippet preview.
- Inputs show inline validation and hints; apply/reset buttons; dirty state badge.
- Preview renders YAML fragment of the node and highlights invalid fields.

## Bottom Logs & Monitoring
- Tabs: Console, UART, TCP, Actions.
- Color-coded levels (info, success, warn, error); timestamp column; channel/state filters; expandable rows; raw hex toggle in monospace.
- Live scrolling with pause and search; toast for critical actions (connect/disconnect, errors, workflow complete).

## Channels Manager
- Cards for UART and TCP channels: show name, type, baud or IP:port, status badge (connected, idle, error), tags.
- Actions: Open/Close, Test Connection, Auto-detect ports; quick link to bind channel to current workflow.

## Protocol Drivers
- Grid of driver cards: XMODEM, Modbus, Custom; badges for capabilities (read/write, CRC, block size limits); Configure and Docs buttons.

## Dashboard Highlights
- Active devices cards with connection status and last contact.
- Recent workflows list with last run status and duration.
- Quick start button: "Create New Workflow".
- Small charts: success rate sparkline, runtime health indicator.

## YAML Editor
- Monospace dark pane with syntax highlighting, lint/validation; split view with live preview of parsed nodes; apply to canvas button.
- Inline error badges mapping to canvas nodes when possible.

## Motion & Feedback
- Smooth hover elevation on cards/buttons; neon cyan glow on active node; animated connection lines pulsing on execution path.
- Loading spinners for connects/tests; modal dialogs for critical actions (flash, abort, stop).
- Toast notifications for success/error; subtle panel slide for open/close transitions.

## Color Tokens (suggested)
- `bg`: #0b1220, `panel`: #121a2c, `panel-muted`: #1a2235
- `accent`: #2af2ff, `accent-strong`: #08c7d9
- `secondary`: #8a5cf6
- `text`: #e7f1ff, `muted`: #8fa2c1
- `success`: #4cc38a, `warning`: #f5a524, `error`: #f14d50

## Accessibility and Clarity
- High-contrast text and focus outlines; keyboard shortcuts for zoom, add node, play/pause execution, toggle logs.
- Clear status labels over playful wording; concise tooltips; avoid dense text in panels.
