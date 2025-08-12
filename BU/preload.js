const { contextBridge, ipcRenderer } = require("electron");

console.log("waos 1 waos 2 waos 3 waos 4 waos5")

contextBridge.exposeInMainWorld("detection", {
    onUpdatePointer: (callback) => ipcRenderer.on("update-pointer", (_event, value) => callback(value))
})