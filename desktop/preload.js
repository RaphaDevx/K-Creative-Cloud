/**
 * Electron preload — exposes safe IPC bridges to the renderer (live.html).
 * contextIsolation: true  →  no direct Node access from renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronBridge', {
  // Hot-reload: fired when a file in live_engine/ changes
  onHotReload: (cb) =>
    ipcRenderer.on('hot-reload', (_e, data) => cb(data)),

  // Auto-updater events
  onUpdateAvailable: (cb) =>
    ipcRenderer.on('update-available', (_e, info) => cb(info)),
  onUpdateDownloaded: (cb) =>
    ipcRenderer.on('update-downloaded', (_e, info) => cb(info)),
  installUpdate: () =>
    ipcRenderer.send('install-update'),

  // Feature flags (resolved in main process, cached)
  getFeatureFlags: () =>
    ipcRenderer.invoke('get-feature-flags'),

  // App metadata
  getVersion: () =>
    ipcRenderer.invoke('get-version'),
});
