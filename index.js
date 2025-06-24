const { fileURLToPath } = require("url");
const { app, BrowserWindow } = require("electron/main");
const { spawn } = require("child_process");
const path = require("path");

let python;
let mainWindow;

function createWindow() {
	mainWindow = new BrowserWindow({
		webPreferences: {
			preload: path.join(__dirname, "preload.js"),
			contextIsolation: true
		},
		width: 800,
		height: 800
	});
	mainWindow.loadFile("./index.html");
}

app.whenReady().then(() => {
	app.on("activate", () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow();
			if (python) return;
			python = spawn("python", ["backend/detection.py"]);
			python.stdout.on('data', (data) => {
				const lines = data.toString().split('\n');
				for (let line of lines) {
					if (!line.trim()) continue;
					try {
						console.log("sending wea wea");
						mainWindow.webContents.send("update-pointer", line);
					} catch (e) {
						console.error('Bad data from Python:', line);
					}
				}
			});
		}
	})
});

app.on("window-all-closed", () => {
	if (python) python.kill();
	if (process.platform !== "darwin") {
		app.quit();
	}
})
