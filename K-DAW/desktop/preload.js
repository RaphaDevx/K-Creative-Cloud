const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kdawElectron', {
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
  installUpdate:  () => ipcRenderer.invoke('install-update'),
});
