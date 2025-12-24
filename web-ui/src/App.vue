<script setup>
import { computed, onMounted, ref } from 'vue'

const bridge = ref(null)
const status = ref('disconnected')
const ports = ref([])
const selectedPort = ref('')
const baud = ref(115200)
const tcpHost = ref('127.0.0.1')
const tcpPort = ref(502)
const channelMode = ref('serial')
const displayMode = ref('hex')
const sendText = ref('')
const sendHex = ref('')
const commLogs = ref([])
const scriptLogs = ref([])
const scriptState = ref('idle')
const scriptProgress = ref(0)
const yamlText = ref('# paste DSL YAML here')
const currentView = ref('control')
const draggingWindow = ref(false)
const dragArmed = ref(false)
const dragStarted = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const snapPreview = ref('')
const enableSnapPreview = ref(false)
const logLevel = ref('ALL')
const logKeyword = ref('')

function addCommLog(kind, payload) {
  const line = `[${kind}] ${payload.text || ''} ${payload.hex ? `(0x${payload.hex})` : ''}`
  commLogs.value.unshift(line.trim())
  if (commLogs.value.length > 200) commLogs.value.pop()
}

function addScriptLog(line) {
  scriptLogs.value.unshift(line)
  if (scriptLogs.value.length > 200) scriptLogs.value.pop()
}

function getLevel(line) {
  if (line.includes('[ERROR]')) return 'ERROR'
  if (line.includes('[WARN]')) return 'WARN'
  if (line.includes('[INFO]')) return 'INFO'
  return 'INFO'
}

function filterLogs(lines) {
  const keyword = logKeyword.value.trim().toLowerCase()
  return lines.filter((line) => {
    if (logLevel.value !== 'ALL' && getLevel(line) !== logLevel.value) {
      return false
    }
    if (keyword && !line.toLowerCase().includes(keyword)) {
      return false
    }
    return true
  })
}

const consoleLogs = computed(() => filterLogs(commLogs.value))
const uartLogs = computed(() => filterLogs(commLogs.value))
const tcpLogs = computed(() => filterLogs([]))
const scriptViewLogs = computed(() => filterLogs(scriptLogs.value))

function addCommBatch(batch) {
  if (!Array.isArray(batch)) return
  for (const item of batch) {
    if (!item) continue
    const kind = item.kind || 'RX'
    if (kind === 'FRAME') {
      addCommLog('FRAME', { text: JSON.stringify(item.payload) })
    } else {
      addCommLog(kind, item.payload || {})
    }
  }
}

function withResult(value, handler) {
  if (value && typeof value.then === 'function') {
    value.then(handler)
  } else {
    handler(value)
  }
}

function refreshPorts() {
  if (!bridge.value) return
  withResult(bridge.value.list_ports(), (items) => {
    ports.value = items || []
    if (!selectedPort.value && ports.value.length) {
      selectedPort.value = ports.value[0]
    }
  })
}

function connectSerial() {
  if (!bridge.value) return
  bridge.value.connect_serial(selectedPort.value, Number(baud.value))
}

function connectTcp() {
  if (!bridge.value) return
  bridge.value.connect_tcp(tcpHost.value, Number(tcpPort.value))
}

function disconnect() {
  if (!bridge.value) return
  bridge.value.disconnect()
}

function sendAscii() {
  if (!bridge.value || !sendText.value) return
  bridge.value.send_text(sendText.value)
}

function sendHexData() {
  if (!bridge.value || !sendHex.value) return
  bridge.value.send_hex(sendHex.value)
}

function runScript() {
  if (!bridge.value || !yamlText.value) return
  bridge.value.run_script(yamlText.value)
}

function stopScript() {
  if (!bridge.value) return
  bridge.value.stop_script()
}

function loadYaml() {
  addScriptLog('[INFO] Load YAML not wired yet')
}

function saveYaml() {
  addScriptLog('[INFO] Save YAML not wired yet')
}

function applyLogFilter() {
  // Filter is applied via computed values.
}

function resetLogFilter() {
  logLevel.value = 'ALL'
  logKeyword.value = ''
}

function attachBridge(obj) {
  bridge.value = obj
  obj.comm_batch.connect((batch) => addCommBatch(batch))
  obj.comm_status.connect((payload) => {
    const text = typeof payload === 'string' ? payload : JSON.stringify(payload)
    status.value = text
  })
  obj.script_log.connect((line) => addScriptLog(line))
  obj.script_state.connect((state) => {
    scriptState.value = state
  })
  obj.script_progress.connect((value) => {
    scriptProgress.value = value
  })
  refreshPorts()
}

onMounted(() => {
  const timer = setInterval(() => {
    if (window.bridge) {
      attachBridge(window.bridge)
      clearInterval(timer)
    }
  }, 200)
})

function armWindowMove(event) {
  if (!event) return
  dragArmed.value = true
  dragStarted.value = false
  dragStart.value = { x: event.screenX, y: event.screenY }
}

function maybeStartWindowMove(event) {
  if (!dragArmed.value || dragStarted.value || !event) return
  const dx = Math.abs(event.screenX - dragStart.value.x)
  const dy = Math.abs(event.screenY - dragStart.value.y)
  if (dx < 10 && dy < 10) return
  if (bridge.value) {
    if (bridge.value.window_start_move_at) {
      bridge.value.window_start_move_at(Math.round(event.screenX), Math.round(event.screenY))
    } else {
      bridge.value.window_start_move()
    }
  }
  dragStarted.value = true
  draggingWindow.value = true
  snapPreview.value = ''
  attachDragListeners()
}

function minimizeWindow() {
  if (bridge.value) {
    bridge.value.window_minimize()
  }
}

function toggleMaximize() {
  if (bridge.value) {
    bridge.value.window_toggle_maximize()
  }
}

function closeWindow() {
  if (bridge.value) {
    bridge.value.window_close()
  }
}

function applyWindowSnap(event) {
  if (bridge.value && event && dragStarted.value) {
    bridge.value.window_apply_snap(Math.round(event.screenX), Math.round(event.screenY))
  }
  clearDragState()
}

function showSystemMenu(event) {
  if (bridge.value && event) {
    bridge.value.window_show_system_menu(Math.round(event.screenX), Math.round(event.screenY))
  }
}

function startResize(edge, event) {
  if (!bridge.value || !edge || !event) return
  document.body.classList.add('resizing')
  bridge.value.window_start_resize(edge)
}

function updateSnapPreview(event) {
  if (!draggingWindow.value || !event) return
  if (event.buttons !== 1) {
    snapPreview.value = ''
    return
  }
  if (!enableSnapPreview.value) {
    snapPreview.value = ''
    return
  }
  const margin = 24
  const x = event.clientX
  const y = event.clientY
  const width = window.innerWidth
  const height = window.innerHeight
  if (y <= margin) {
    snapPreview.value = 'max'
  } else if (x <= margin) {
    snapPreview.value = 'left'
  } else if (x >= width - margin) {
    snapPreview.value = 'right'
  } else {
    snapPreview.value = ''
  }
}

function handleDragEnd(event) {
  if (!draggingWindow.value) return
  applyWindowSnap(event)
}

function attachDragListeners() {
  window.addEventListener('mousemove', updateSnapPreview)
  window.addEventListener('mouseup', handleDragEnd)
  window.addEventListener('blur', handleDragCancel)
  document.addEventListener('visibilitychange', handleDragCancel)
}

function detachDragListeners() {
  window.removeEventListener('mousemove', updateSnapPreview)
  window.removeEventListener('mouseup', handleDragEnd)
  window.removeEventListener('blur', handleDragCancel)
  document.removeEventListener('visibilitychange', handleDragCancel)
}

function handleDragCancel() {
  clearDragState()
}

function clearDragState() {
  draggingWindow.value = false
  dragArmed.value = false
  dragStarted.value = false
  snapPreview.value = ''
  document.body.classList.remove('resizing')
  detachDragListeners()
}
</script>

<template>
  <div class="app">
    <div class="resize-handle top" @mousedown.stop="startResize('top', $event)"></div>
    <div class="resize-handle bottom" @mousedown.stop="startResize('bottom', $event)"></div>
    <div class="resize-handle left" @mousedown.stop="startResize('left', $event)"></div>
    <div class="resize-handle right" @mousedown.stop="startResize('right', $event)"></div>
    <div class="resize-handle top-left" @mousedown.stop="startResize('top-left', $event)"></div>
    <div class="resize-handle top-right" @mousedown.stop="startResize('top-right', $event)"></div>
    <div class="resize-handle bottom-left" @mousedown.stop="startResize('bottom-left', $event)"></div>
    <div class="resize-handle bottom-right" @mousedown.stop="startResize('bottom-right', $event)"></div>
    <header
      class="app-titlebar"
      @dblclick="toggleMaximize"
      @mousedown.left="armWindowMove"
      @mousemove="maybeStartWindowMove"
      @mouseup.left="applyWindowSnap"
      @contextmenu.prevent="showSystemMenu"
    >
      <button
        class="app-icon"
        type="button"
        @mousedown.stop
        @dblclick.stop
        @click.stop="showSystemMenu"
      >
        <span class="app-icon-dot"></span>
      </button>
      <div class="app-title">ProtoFlow</div>
      <div class="title-actions">
        <button
          class="title-btn"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="minimizeWindow"
        >
          <el-icon><Minus /></el-icon>
        </button>
        <button
          class="title-btn"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="toggleMaximize"
        >
          <el-icon><FullScreen /></el-icon>
        </button>
        <button
          class="title-btn close"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="closeWindow"
        >
          <el-icon><Close /></el-icon>
        </button>
      </div>
    </header>
    <div class="body">
      <aside class="nav">
        <div class="nav-title">Navigation</div>
        <div class="nav-panel">
          <button class="nav-button" :class="{ active: currentView === 'control' }" @click="currentView = 'control'">
            Manual
          </button>
          <button class="nav-button" :class="{ active: currentView === 'scripts' }" @click="currentView = 'scripts'">
            Scripts
          </button>
          <button class="nav-button" :class="{ active: currentView === 'channels' }" @click="currentView = 'channels'">
            Channels
          </button>
          <button class="nav-button" :class="{ active: currentView === 'protocols' }" @click="currentView = 'protocols'">
            Protocols
          </button>
          <button class="nav-button" :class="{ active: currentView === 'settings' }" @click="currentView = 'settings'">
            Settings
          </button>
        </div>
      </aside>

      <section class="content">
        <div v-if="currentView === 'control'" class="stack">
          <div class="split-horizontal">
            <div class="panel">
              <div class="section-title">IO Monitor</div>
              <div class="log">
                <el-fixed-size-list
                  :data="commLogs"
                  :total="commLogs.length"
                  :height="220"
                  :item-size="18"
                >
                  <template #default="{ data, index, style }">
                    <div class="log-line" :style="style">{{ data[index] }}</div>
                  </template>
                </el-fixed-size-list>
              </div>
            </div>
            <div class="panel">
              <div class="section-title">Control Panel</div>
              <div class="field">
                <label>Channel Mode</label>
                <el-select v-model="channelMode" placeholder="Mode">
                  <el-option label="Serial" value="serial" />
                  <el-option label="TCP" value="tcp" />
                </el-select>
              </div>
              <div class="field">
                <label>Serial Port</label>
                <el-select v-model="selectedPort" placeholder="Select port" filterable>
                  <el-option v-for="item in ports" :key="item" :label="item" :value="item" />
                </el-select>
                <el-button type="primary" plain size="small" @click="refreshPorts">Refresh</el-button>
              </div>
              <div class="field">
                <label>Baud</label>
                <el-input-number v-model="baud" :min="300" :max="2000000" controls-position="right" />
              </div>
              <div class="row">
                <el-button type="primary" @click="connectSerial">Connect Serial</el-button>
                <el-button plain @click="disconnect">Disconnect</el-button>
              </div>
              <div class="divider"></div>
              <div class="field">
                <label>TCP Host</label>
                <el-input v-model="tcpHost" placeholder="127.0.0.1" />
              </div>
              <div class="field">
                <label>TCP Port</label>
                <el-input-number v-model="tcpPort" :min="1" :max="65535" controls-position="right" />
              </div>
              <div class="row">
                <el-button type="primary" @click="connectTcp">Connect TCP</el-button>
              </div>
              <div class="divider"></div>
              <div class="field">
                <label>Display Format</label>
                <el-select v-model="displayMode" placeholder="HEX">
                  <el-option label="HEX" value="hex" />
                  <el-option label="Text" value="text" />
                </el-select>
              </div>
              <div class="field">
                <label>Send HEX / Text</label>
                <el-input v-model="sendHex" placeholder="55 AA 01" />
                <el-input v-model="sendText" placeholder="UTF-8 text" />
                <div class="row">
                  <el-button type="primary" @click="sendHexData">Send HEX</el-button>
                  <el-button type="primary" @click="sendAscii">Send Text</el-button>
                </div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="section-title">Console</div>
            <div class="log-filter">
              <el-select v-model="logLevel" placeholder="Level" size="small">
                <el-option label="ALL" value="ALL" />
                <el-option label="INFO" value="INFO" />
                <el-option label="WARN" value="WARN" />
                <el-option label="ERROR" value="ERROR" />
              </el-select>
              <el-input v-model="logKeyword" size="small" placeholder="Search logs" />
              <el-button size="small" @click="applyLogFilter">Filter</el-button>
              <el-button size="small" plain @click="resetLogFilter">Reset</el-button>
            </div>
            <el-tabs type="border-card" class="log-tabs">
              <el-tab-pane label="Console">
                <div class="log">
                  <el-fixed-size-list
                    :data="consoleLogs"
                    :total="consoleLogs.length"
                    :height="240"
                    :item-size="18"
                  >
                    <template #default="{ data, index, style }">
                      <div class="log-line" :style="style">{{ data[index] }}</div>
                    </template>
                  </el-fixed-size-list>
                </div>
              </el-tab-pane>
              <el-tab-pane label="UART">
                <div class="log">
                  <el-fixed-size-list
                    :data="uartLogs"
                    :total="uartLogs.length"
                    :height="240"
                    :item-size="18"
                  >
                    <template #default="{ data, index, style }">
                      <div class="log-line" :style="style">{{ data[index] }}</div>
                    </template>
                  </el-fixed-size-list>
                </div>
              </el-tab-pane>
              <el-tab-pane label="TCP">
                <div class="log">
                  <el-fixed-size-list
                    :data="tcpLogs"
                    :total="tcpLogs.length"
                    :height="240"
                    :item-size="18"
                  >
                    <template #default="{ data, index, style }">
                      <div class="log-line" :style="style">{{ data[index] }}</div>
                    </template>
                  </el-fixed-size-list>
                </div>
              </el-tab-pane>
              <el-tab-pane label="Script">
                <div class="log">
                  <el-fixed-size-list
                    :data="scriptViewLogs"
                    :total="scriptViewLogs.length"
                    :height="240"
                    :item-size="18"
                  >
                    <template #default="{ data, index, style }">
                      <div class="log-line" :style="style">{{ data[index] }}</div>
                    </template>
                  </el-fixed-size-list>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>

        <div v-else-if="currentView === 'scripts'" class="stack">
          <div class="split-horizontal">
            <div class="panel">
              <div class="section-title">Script Editor</div>
              <el-input v-model="yamlText" type="textarea" :rows="14" />
            </div>
            <div class="panel">
              <div class="section-title">Script Controls</div>
              <div class="row">
                <el-button @click="loadYaml">Load YAML</el-button>
                <el-button @click="saveYaml">Save YAML</el-button>
                <el-button type="primary" @click="runScript">Run Script</el-button>
                <el-button plain @click="stopScript">Stop Script</el-button>
              </div>
              <div class="field">
                <label>Status</label>
                <el-tag type="info">{{ scriptState }}</el-tag>
              </div>
              <div class="field">
                <label>Progress</label>
                <el-progress :percentage="scriptProgress" :stroke-width="8" />
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="section-title">Script Log</div>
            <div class="log">
              <el-fixed-size-list
                :data="scriptLogs"
                :total="scriptLogs.length"
                :height="240"
                :item-size="18"
              >
                <template #default="{ data, index, style }">
                  <div class="log-line" :style="style">{{ data[index] }}</div>
                </template>
              </el-fixed-size-list>
            </div>
          </div>
        </div>

        <div v-else class="stack">
          <div class="panel">
            <div class="section-title">
              {{ currentView === 'channels' ? 'Channels' : currentView === 'protocols' ? 'Protocols' : 'Settings' }}
            </div>
            <div class="placeholder">
              This section is a placeholder in the Web UI scaffold.
            </div>
          </div>
        </div>
      </section>
    </div>
    <div v-if="snapPreview" class="snap-overlay" :class="`snap-${snapPreview}`"></div>
  </div>
</template>
